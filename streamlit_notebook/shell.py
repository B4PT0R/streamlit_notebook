"""Shell
=================

A lightweight execution engine that brings IPython-style ergonomics to embedded
Python environments while staying dependency-light.

Highlights
----------
- Node-by-node execution powered by ASTTokens so hooks can inspect, transform
  or log each AST node before and after it runs.
- Streaming IO capture via `Collector`, custom `Stream` wrappers and a
  prompt_toolkit-aware `StdinProxy`, all pluggable through hooks.
- Token-aware support for single-line (`%`) and cell (`%%`) magics plus system
  commands (`!`, `!!`) that respect indentation and ignore occurrences inside
  strings or comments.
- Comprehensive hook matrix (pre/post run, code blocks, namespace diffing,
  display, exception, stdin/stdout/stderr) enabling fine-grained customization
  for agents, REPLs or UIs.
- Rich execution results encapsulated in `ShellResponse`, exposing captured
  stdout/stderr, last expression value, namespaces before/after, and any
  exception information.

Hook Matrix
-----------
The `Shell` class exposes hooks to customize every stage of execution. Each hook
receives rich context so embedders can log, transform or short-circuit behaviour:

- `input_hook(code)` runs before parsing the source string (logging, metrics).
- `pre_run_hook(code)` lets you rewrite code before it is tokenized/executed.
- `code_block_hook(code_block)` fires for every AST block (useful for tracing).
- `pre_execute_hook(node, source)` can mutate AST nodes prior to compilation.
- `post_execute_hook(node, result)` observes results or exceptions per node.
- `display_hook(result)` overrides how expression values are rendered.
- `stdout_hook(data, buffer)` / `stderr_hook(data, buffer)` redirect output streams to custom handlers.
- `stdin_hook()` redirect stdin reads to a custom handler (web, CLI, agents).
- `exception_hook(exc)` is invoked once a run finishes with an error.
- `namespace_change_hook(old, new, locals)` inspects or vetoes namespace diffs.
- `post_run_hook(response)` sees the aggregate `ShellResponse` for logging or
  telemetry.

Hooks can be combined; each is optional and falls back to a sensible default when
not provided.


Quick Start
-----------
    shell = Shell()
    shell.register_magic(lambda text: text.upper(), name="caps")
    shell.run('''%caps hello
!pwd
value = 41 + 1''')

    response = shell.run("value")
    print(response.result)  # 42

This module is designed to be embedded in CLI tools, notebooks, web consoles or
agents that need controllable Python execution without the dependency weight of
IPython.
"""

from __future__ import annotations

import sys
import traceback
import io
import builtins
import ast
from collections import deque, OrderedDict
from asttokens import ASTTokens
import asyncio
import tokenize
import subprocess
import hashlib
import random
import string
from contextlib import contextmanager
from typing import Any, Callable, Optional, Union, Literal

def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def short_id(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_letters, k=length))

def debug_print(*args: Any, sep: str = " ", end: str = "\n", flush: bool = False) -> None:
    sys.__stdout__.write(sep.join(map(str, args)) + end)
    if flush:
        sys.__stdout__.flush()


def stdout_write(data: str, buffer: str) -> None:
    if isinstance(sys.stdout, Stream):
        sys.__stdout__.write(data)
        sys.__stdout__.flush()
    else:
        sys.stdout.write(data)
        sys.stdout.flush()

def stderr_write(data: str, buffer: str) -> None:
    if isinstance(sys.stderr, Stream):
        sys.__stderr__.write(data)
        sys.__stderr__.flush()
    else:
        sys.stderr.write(data)
        sys.stderr.flush()

def stdin_readline() -> str:
    if isinstance(sys.stdin, StdinProxy):
        return prompt("", multiline=False)
    else:
        return sys.stdin.readline()
    
PTK_SESSION: Any = None

def ensure_ptk_session() -> Any:
    global PTK_SESSION
    if PTK_SESSION is None:
        try:
            from prompt_toolkit import PromptSession
        except ImportError as exc:
            raise RuntimeError("prompt_toolkit is required for interactive shell mode. Install it via 'pip install prompt-toolkit'.") from exc
        PTK_SESSION = PromptSession()
    return PTK_SESSION

def prompt(prompt: str, multiline: bool = True, prompt_continuation: str = "", wrap_lines: bool = False) -> str:
    session = ensure_ptk_session()
    try:
        from prompt_toolkit.patch_stdout import patch_stdout
    except ImportError as exc:
        raise RuntimeError("prompt_toolkit is required for interactive shell mode. Install it via 'pip install prompt-toolkit'.") from exc
    with patch_stdout():
        answer = session.prompt(message=prompt, multiline=multiline, prompt_continuation=prompt_continuation, wrap_lines=wrap_lines, refresh_interval=1)
    return answer

class Stream(io.IOBase):
    """
    Custom io stream that intercepts stdout and stderr streams.

    This class manages text data by buffering it and optionally passing it through a hook
    for real-time processing and display. It ensures efficient data handling by
    maintaining a maximum buffer size and flushing data when this size is exceeded or on newlines.

    Args:
        hook (callable, optional): Function to process written data in real-time.
        buffer_size (int, optional): Maximum size of the internal buffer before forcing a flush. Defaults to 2048.


    Attributes:
        hook (callable): Optional function to process written data in real-time.
        buffer_size (int): Maximum size of the internal buffer before forcing a flush.
        buffer (str): Internal buffer for storing written data.
        cache_buffer (str): Buffer for storing all written data.

    Methods:
        write(data): Writes data to the stream, managing buffering and flushing.
        flush(data_to_flush=None): Flushes the given data to the hook and caches it.
        get_value(): Returns all text that has been written to this stream.
    """
    def __init__(self, hook: Optional[Callable[[str, str], None]] = None, buffer_size: int = 2048) -> None:
        super().__init__()
        self.hook = hook
        self.buffer_size = buffer_size
        self.buffer = ""
        self.cache_buffer = ""

    def write(self, data: str) -> int:
        """
        Writes data to the stream, managing buffering and flushing.

        Args:
            data (str): The data to be written to the stream.

        Raises:
            TypeError: If the input data is not a string.

        This method handles writing data to the stream, managing the internal buffer,
        and flushing complete lines or when the buffer size is exceeded.
        """
        if not isinstance(data, str):
            raise TypeError("write argument must be str, not {}".format(type(data).__name__))
        
        self.buffer += data

        # Process complete lines
        lines = self.buffer.split('\n')
        self.buffer = lines.pop()  # Keep incomplete line in the buffer

        # Flush complete lines
        for line in lines:
            self.flush(line + '\n')

        # Handle buffer overflow
        while len(self.buffer) > self.buffer_size:
            self.flush(self.buffer[:self.buffer_size])
            self.buffer = self.buffer[self.buffer_size:]

        return len(data)

    def flush(self, data_to_flush: Optional[str] = None) -> None:
        """
        Flushes the given data to the hook and caches it.

        Args:
            data_to_flush (str, optional): The data to flush. If None, flushes the current buffer.

        This method processes the data through the hook (if set) and adds it to the cache buffer.
        """
        if data_to_flush is None:
            data_to_flush = self.buffer
            self.buffer = ""

        self.cache_buffer += data_to_flush

        if self.hook:
            self.hook(data_to_flush,self.cache_buffer)
        

    def get_value(self) -> str:
        """
        Returns all text that has been written to this stream.

        Returns:
            str: The entire content that has been written to the stream.
        """
        return self.cache_buffer


class StdinProxy(io.TextIOBase):
    """Proxy that feeds stdin through a provider callable.

    The hook is invoked whenever a new line is required and should return a
    string or ``None`` to signal EOF. Returned chunks are split into
    newline-terminated lines so consumers that read line-by-line keep working.
    """

    def __init__(self, hook: Callable[[], str], *, encoding: str = "utf-8") -> None:
        super().__init__()
        if not callable(hook):
            raise TypeError("provider must be callable")
        self._hook = hook
        self._encoding = encoding
        self._buffer: deque[str] = deque()
        self._eof = False

    @property
    def encoding(self) -> str:
        return self._encoding

    def readable(self) -> bool:
        return True

    def isatty(self) -> bool:
        return True

    def fileno(self) -> int:
        raise io.UnsupportedOperation("StdinProxy does not expose a file descriptor")

    def close(self):
        try:
            self._buffer.clear()
            self._eof = True
        finally:
            super().close()

    def _ensure_line(self):
        if self._buffer or self._eof:
            return

        chunk = self._hook()

        if chunk is None:
            self._eof = True
            return

        if not isinstance(chunk, str):
            raise TypeError("stdin provider must return str or None")

        if chunk == "":
            lines = ["\n"]
        else:
            lines = chunk.splitlines(True)
            if not lines:
                lines = ["\n"]
            if not lines[-1].endswith("\n"):
                lines[-1] += "\n"

        self._buffer.extend(lines)

    def readline(self, size=-1):
        self._checkClosed()

        if size == 0:
            return ""

        self._ensure_line()
        if not self._buffer:
            return ""

        line = self._buffer.popleft()
        if size > 0 and len(line) > size:
            remainder = line[size:]
            line = line[:size]
            self._buffer.appendleft(remainder)
        return line

    def read(self, size=-1):
        self._checkClosed()

        if size == 0:
            return ""

        if size < 0:
            return "".join(iter(self.readline, ""))

        parts = []
        remaining = size
        while remaining > 0:
            chunk = self.readline(remaining)
            if chunk == "":
                break
            parts.append(chunk)
            remaining -= len(chunk)
        return "".join(parts)

class Collector:
    """
    Manages stdout and stderr redirection within a context manager.

    This class captures all output and exceptions, allowing fine control over their handling and display.

    Attributes:
        stdout_hook (callable): Optional function to process stdout in real-time.
        stderr_hook (callable): Optional function to process stderr in real-time.
        exception_hook (callable): Optional function to process exceptions.
        stdin_hook (callable): Optional callable providing text for stdin reads.
        stdout_stream (Stream): Custom stream for capturing stdout.
        stderr_stream (Stream): Custom stream for capturing stderr.
        exception (Exception): Stores any exception raised during execution.

    Methods:
        get_stdout(): Returns all that was written to the stdout stream.
        get_stderr(): Returns all that was written to the stderr stream.
    """
    def __init__(self, stdout_hook=None, stderr_hook=None, exception_hook=None, stdin_hook=None, shell=None):
        self.stdout_hook = stdout_hook or stdout_write
        self.stderr_hook = stderr_hook or stderr_write
        self.stdin_hook = stdin_hook or stdin_readline
        self.exception_hook = exception_hook
        self.shell = shell
        self.stdin_proxy = StdinProxy(hook=self.stdin_hook)
        self.stdout_stream = Stream(hook=self.stdout_hook)
        self.stderr_stream = Stream(hook=self.stderr_hook)
        self.exception = None

    def get_stdout(self):
        """
        Returns all that was written to the stdout stream.

        Returns:
            str: The entire content written to stdout.
        """
        return self.stdout_stream.get_value()
    
    def get_stderr(self):
        """
        Returns all that was written to the stderr stream.

        Returns:
            str: The entire content written to stderr.
        """
        return self.stderr_stream.get_value()

    def __enter__(self):
        """
        Implements using the collector as a context manager.

        This method redirects sys.stdout and sys.stderr to stdout and stderr Streams
        and, when ``stdin_hook`` is provided, installs a ``StdinProxy`` as sys.stdin.

        Returns:
            Collector: The Collector instance.
        """
        self.saved_stdout = sys.stdout
        self.saved_stderr = sys.stderr
        self.saved_stdin = sys.stdin
        sys.stdout = self.stdout_stream
        sys.stderr = self.stderr_stream
        sys.stdin = self.stdin_proxy
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """
        Flushes the streams, restores the standard streams and gracefully processes any pending exception.

        Args:
            exc_type: The type of the exception.
            exc_value: The exception instance.
            exc_traceback: The traceback object.

        Returns:
            bool: True if the exception was handled, False otherwise.
        """
        # Flush streams
        self.stdout_stream.flush()
        self.stderr_stream.flush()
        # Restore standard streams
        sys.stdout = self.saved_stdout
        sys.stderr = self.saved_stderr
        sys.stdin = self.saved_stdin
        # Deal with any unhandled exception
        if exc_type is not None:
            # Save the exception
            self.exception = exc_value
            message, enriched = self.shell._build_enriched_traceback(exc_type, exc_value, exc_traceback)
            exc_value.enriched_traceback = enriched
            exc_value.enriched_traceback_string = message

            # Send the traceback to stderr_stream and flush
            self.stderr_stream.write(message)
            self.stderr_stream.flush()
            # Send the exception to the exception hook
            if self.exception_hook:
                self.exception_hook(exc_value)
            return True  # Suppress exception propagation

class ShellResponse:
    """
    Represents the results of code execution, encapsulating various aspects of the execution.

    Attributes:
        input (str): The original input code.
        processed_input (str): The code after preprocessing.
        stdout (str): Captured standard output.
        stderr (str): Captured standard error.
        result (Any): The result of the last executed expression.
        exception (Exception): Any exception that occurred during execution.
    """
    def __init__(
        self,
        input: Optional[str] = None,
        processed_input: Optional[str] = None,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        result: Any = None,
        exception: Optional[Exception] = None
    ) -> None:
        self.input = input
        self.processed_input = processed_input
        self.stdout = stdout
        self.stderr = stderr
        self.result = result
        self.exception = exception

    @staticmethod
    def _short_repr(value: Any, *, limit: int = 100) -> str:
        text = repr(value)
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    def __repr__(self) -> str:
        parts = [self.__class__.__name__ + "("]
        fields = []
        if self.result is not None:
            fields.append(f"result={self._short_repr(self.result)}")
        if self.exception is not None:
            fields.append(f"exception={self._short_repr(self.exception)}")
        if self.stdout:
            fields.append(f"stdout_len={len(self.stdout)}")
        if self.stderr:
            fields.append(f"stderr_len={len(self.stderr)}")
        if self.processed_input:
            fields.append(f"processed_input_len={len(self.processed_input)}")
        if not fields:
            fields.append("empty")
        parts.append(", ".join(fields))
        parts.append(")")
        return "".join(parts)

    def __str__(self) -> str:
        return self.__repr__()

class Shell:
    """
    Executes Python code within a managed environment and captures output and exceptions.

    This class provides a flexible and extensible Python code execution environment.
    It allows for fine-grained control over code execution, input/output handling,
    and namespace management through various hooks and customization options.

    Parameters:
        namespace (dict): The global namespace for code execution.
        display_mode (str): Controls when results are displayed ('all', 'last', or 'none').
        history_size (int): Maximum number of past executions to cache.

        Options for customization via hooks:
        display_hook (callable): Optional function to customize result display.
        input_hook (callable): Optional function called before processing input code.
        pre_run_hook (callable): Optional function to preprocess input code.
        post_run_hook (callable): Optional function called after execution to post-process or monitor the ShellResponse.
        pre_execute_hook (callable): Optional function to modify AST nodes before execution.
        post_execute_hook (callable): Optional function called after each node execution with the node and its result.
        stdout_hook (callable): Optional function to process stdout in real-time.
        stderr_hook (callable): Optional function to process stderr in real-time.
        stdin_hook (callable): Optional callable used to feed stdin reads during execution.
        exception_hook (callable): Optional function called when an exception occurs during execution.
        namespace_change_hook (callable): Optional function called after execution to process namespace changes.
        code_block_hook (callable): Optional function called for each code block before execution.

    Public Attributes:
        namespace (dict): The global namespace for code execution.
        display_mode (str): Controls when results are displayed ('all', 'last', or 'none').
        magics (dict): Registered magic commands.
        last_result (Any): The result of the last executed expression.
        history (OrderedDict): Cache of past executions.
        history_size (int): Maximum number of past executions to cache.
        current_code (str): The current code being executed.
        + all hooks as attributes

    Public Methods:
        run(code, globals, locals): Execute the given code in the shell environment.
        interact(): Starts an interactive shell session with multiline input support.
        ensure_builtins(): Ensures built-in functions and classes are available in the namespace.
        set_namespace(namespace): Dynamically sets the namespace reference to a chosen dict.
        reset_namespace(): Clears the namespace, retaining only built-in functions and classes.
        update_namespace(*args, **kwargs): Dynamically updates the namespace with provided variables or functions.
        display(obj): Default method to display an object.

    Expected hooks signatures:
        input_hook(code)
        pre_run_hook(code) -> processed_code
        code_block_hook(code_block)
        pre_execute_hook(node, source) -> node
        post_execute_hook(node, result)
        display_hook(result)
        stdout_hook(data, buffer)
        stderr_hook(data, buffer)
        stdin_hook() -> str or None
        exception_hook(exc)
        namespace_change_hook(old_globals, new_globals, locals)
        post_run_hook(response) -> response
        
    """

    def __init__(
        self,
        # Configuration
        namespace: Optional[dict[str, Any]] = None,
        display_mode: Literal['all', 'last', 'none'] = 'last',
        history_size: int = 200,
        # Hooks
        stdout_hook: Optional[Callable[[str, str], None]] = None,
        stderr_hook: Optional[Callable[[str, str], None]] = None,
        stdin_hook: Optional[Callable[[], str]] = None,
        display_hook: Optional[Callable[[Any], None]] = None,
        exception_hook: Optional[Callable[[Exception], None]] = None,
        input_hook: Optional[Callable[[str], None]] = None,
        pre_run_hook: Optional[Callable[[str], str]] = None,
        code_block_hook: Optional[Callable[[str], None]] = None,
        pre_execute_hook: Optional[Callable[[ast.AST, str], ast.AST]] = None,
        post_execute_hook: Optional[Callable[[ast.AST, Any], None]] = None,
        namespace_change_hook: Optional[Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], None]] = None,
        post_run_hook: Optional[Callable[[ShellResponse], ShellResponse]] = None,
        add_script_run_ctx_hook: Optional[Callable[..., Any]] = None,
        get_script_run_ctx_hook: Optional[Callable[..., Any]] = None,
    ) -> None:
        
        self.namespace = namespace or {}
        self.display_mode = display_mode        
        self.input_hook = input_hook
        self.code_block_hook = code_block_hook
        self.stdout_hook = stdout_hook
        self.stderr_hook = stderr_hook
        self.stdin_hook = stdin_hook
        self.display_hook = display_hook
        self.exception_hook = exception_hook
        self.pre_run_hook = pre_run_hook
        self.post_run_hook = post_run_hook
        self.pre_execute_hook = pre_execute_hook
        self.post_execute_hook = post_execute_hook
        self.namespace_change_hook = namespace_change_hook
        self.add_script_run_ctx_hook = add_script_run_ctx_hook
        self.get_script_run_ctx_hook=get_script_run_ctx_hook
        self.magics= {}
        self._placeholders={}
        self._placeholder_stack=[]
        self.last_result = None
        self._current_code=None
        self._current_filename="<shell-input-0>"
        self.history_size=max(history_size,1)
        self.history=OrderedDict()
        self._input_counter=0
        self.session=None
        self.ensure_builtins()

    @property
    def current_code(self):
        """Returns the current code being executed (readonly)."""
        return self._current_code
    
    def _render_snippet(self, filename, lineno):
        """Renders a code snippet for a given filename and line number.
        Args:
            filename (str): The name of the file.
            lineno (int): The line number to center the snippet around. (1-based)
        Returns:
            str: A formatted code snippet with line numbers and an indicator for the target line.
        """
        if filename==self._current_filename:
            source = self._current_code
        elif filename in self.history:
            response = self.history.get(filename)
            if response and isinstance(response, ShellResponse):
                source = response.processed_input
            else:
                source = ""
        else:
            try:
                with open(filename, 'r') as f:
                    source = f.read()
            except Exception:
                source =""
        if not source:
            return ""
        lines = source.splitlines()
        target_index = lineno - 1
        if not (0 <= target_index < len(lines)):
            return ""
        start_index = max(target_index - 2, 0)
        end_index = min(target_index + 1, len(lines) - 1)
        snippet_lines = []
        width=len(str(end_index+1))
        for idx in range(start_index, end_index + 1):
            marker = "=> " if idx == target_index else "   "
            snippet_lines.append(f"{marker}{str(idx + 1).rjust(width)} | {lines[idx]}")
        return "\n".join(snippet_lines) + "\n"

    def _build_enriched_traceback(self, exc_type, exc_value, exc_traceback):
        """Builds an enriched traceback with code snippets for each frame.
        Args:
            exc_type: The type of the exception.
            exc_value: The exception instance.
            exc_traceback: The traceback object.
        Returns:
            tuple: A tuple containing the formatted traceback string and a dictionary with enriched frame information.
        """
        te = traceback.TracebackException(exc_type, exc_value, exc_traceback)
        output = ['Traceback (most recent call last):\n']
        enriched_frames = []
        for i,frame in enumerate(te.stack):
            if i<2:
                # Skip the first two frames (inside the shell machinery)
                continue
            output.append(f"  File \"{frame.filename}\", line {frame.lineno}, in {frame.name}\n")
            snippet = self._render_snippet(frame.filename,frame.lineno)
            output.append(snippet)
            enriched_frames.append({
                "filename": frame.filename,
                "lineno": frame.lineno,
                "name": frame.name,
                "line": frame.line,
                "snippet": snippet,
            })
        exception_lines = list(te.format_exception_only())
        output.extend(exception_lines)
        enriched = {
            "frames": enriched_frames,
            "exception_lines": exception_lines,
        }
        return "".join(output), enriched

    def _parse_system_cmd(self, code):
        """Parses and transforms system commands in the code.
        Args:
            code (str): The input code containing potential system commands.
        Returns:
            str: The transformed code with system commands replaced by function calls.
        """
        stripped_code=code.lstrip('\n')
        if stripped_code.startswith('!!'):
            command = stripped_code[2:].lstrip('\n')
            id= short_id()
            self._placeholders[id]=command
            return f"__shell__.run_system_cmd(__shell__._placeholders.get('{id}'))"

        lines = code.split('\n')
        ignore_map = self._build_ignore_map(code, lines)
        for i, line in enumerate(lines):
            stripped_line = line.lstrip()
            if stripped_line.startswith('!') and not stripped_line.startswith('!!'):
                column = len(line) - len(stripped_line)
                if self._position_ignored(ignore_map, i + 1, column):
                    continue
                indent = line[:column]
                command = stripped_line[1:].lstrip()
                id= short_id()
                self._placeholders[id]=command
                
                lines[i] = f"{indent}__shell__.run_system_cmd(__shell__._placeholders.get('{id}'))"
        return '\n'.join(lines)

    def _parse_magics(self,code):
        """Parses and transforms magic commands in the code.
        Args:
            code (str): The input code containing potential magic commands.
        Returns:
            str: The transformed code with magic commands replaced by function calls.
        """
        stripped_code=code.lstrip('\n')
        if stripped_code.startswith('%%'):
            lines=stripped_code.split('\n')
            magic=lines[0][2:].strip()
            content='\n'.join(lines[1:])
            id= short_id()
            self._placeholders[id]=content
            code=f"__magics__['{magic}'](__shell__._placeholders.get('{id}'))"
        else:
            lines=code.split('\n')
            ignore_map = self._build_ignore_map(code, lines)
            for i,line in enumerate(lines):
                stripped=line.lstrip()
                if stripped.startswith("%"):
                    column=len(line)-len(stripped)
                    if self._position_ignored(ignore_map, i + 1, column):
                        continue
                    indent=line[:column]
                    parts=stripped.split(" ",1)
                    magic=parts[0][1:]
                    content=parts[1].strip() if len(parts)>1 else ""
                    id= short_id()
                    self._placeholders[id]=content
                    lines[i]=f"{indent}__magics__['{magic}'](__shell__._placeholders.get('{id}'))"
            code='\n'.join(lines)
        return code
    
    def register_magic(self,func=None,*,name=None):
        """Registers a magic function.
        Args:
            func (callable): The function to register as a magic.
            name (str, optional): The name of the magic. If None, uses func.__name__.
        Returns:
            callable: The registered magic function.
        """
        if func is None:
            return lambda f: self.register_magic(f, name=name)
        name= name or func.__name__
        self.magics[name]=func
        return func

    def run_system_cmd(self, command):
        """Runs a system command using subprocess.
        Args:
            command (str): The system command to run.
        Returns:
            int: The return code of the command.
        """
        def _stream_output(stream, out_stream):
            for line in iter(stream.readline, ''):
                out_stream.write(line)
                out_stream.flush()
            stream.close()

        import threading

        process = subprocess.Popen(
            command, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1
        )

        t_out = threading.Thread(target=_stream_output, args=(process.stdout, sys.stdout))
        t_err = threading.Thread(target=_stream_output, args=(process.stderr, sys.stderr))
        if self.add_script_run_ctx_hook:
            self.add_script_run_ctx_hook(t_out,self.get_script_run_ctx_hook())
            self.add_script_run_ctx_hook(t_err,self.get_script_run_ctx_hook())
        t_out.start()
        t_err.start()
        t_out.join()
        t_err.join()

        return process.wait()

    def _build_ignore_map(self, code, lines):
        """Builds a map of positions to ignore (inside strings or comments).
        Used to avoid parsing magics or system commands inside strings or comments.
        Args:
            code (str): The input code.
            lines (list): List of lines in the code.
        Returns:
            dict: A mapping of line numbers to lists of (start_col, end_col) tuples to ignore.
        """
        ignore = {}
        try:
            tokens = tokenize.generate_tokens(io.StringIO(code).readline)
        except (tokenize.TokenError, IndentationError):
            return ignore

        for tok in tokens:
            if tok.type in (tokenize.STRING, tokenize.COMMENT):
                (start_line, start_col) = tok.start
                (end_line, end_col) = tok.end

                if start_line == end_line:
                    ignore.setdefault(start_line, []).append((start_col, end_col))
                else:
                    line_text = lines[start_line - 1] if start_line - 1 < len(lines) else ''
                    ignore.setdefault(start_line, []).append((start_col, len(line_text)))
                    for line in range(start_line + 1, end_line):
                        line_text = lines[line - 1] if line - 1 < len(lines) else ''
                        ignore.setdefault(line, []).append((0, len(line_text)))
                    ignore.setdefault(end_line, []).append((0, end_col))

        return ignore

    @staticmethod
    def _position_ignored(ignore_map, line_no, column):
        """Checks if a given position is within an ignored range.
        Args:
            ignore_map (dict): The ignore map.
            line_no (int): The line number (1-based).
            column (int): The column number (0-based).
        Returns:
            bool: True if the position is ignored, False otherwise.
        """
        for start, end in ignore_map.get(line_no, ()):
            if start <= column < end:
                return True
        return False
    
    def _execute(self, node, source, globals, locals, suppress_result=False, is_last_node=False):
        """
        Execute a single AST node in the given namespace.

        Args:
            node (ast.AST): The AST node to execute.
            source (ASTTokens): The source tokens.
            globals (dict): The global namespace.
            locals (dict): The local namespace.
            suppress_result (bool): Whether to suppress the result display.
            is_last_node (bool): Whether this is the last node in the current execution.

        Returns:
            tuple: Updated (globals, locals) after execution.

        This method is responsible for the actual execution of individual AST nodes.
        It handles both expression and statement nodes, and manages result capturing and display.
        """

        if self.pre_execute_hook:
            node = self.pre_execute_hook(node,source)
            if not isinstance(node, ast.AST):
                raise TypeError("pre_execute_hook must return an AST node")
        
        if isinstance(node, ast.Expr):
            compiled_code = compile(ast.Expression(node.value), filename=self._current_filename, mode='eval')
            self.last_result = eval(compiled_code, globals,locals)
            if not suppress_result:
                if self.display_mode == 'all' or (self.display_mode == 'last' and is_last_node):
                    self.display(self.last_result)
        else:
            self.last_result = None
            compiled_code = compile(ast.Module([node], type_ignores=[]), filename=self._current_filename, mode='exec')
            exec(compiled_code, globals,locals)

        if self.post_execute_hook:
            self.post_execute_hook(node, self.last_result)

        return globals,locals

    @contextmanager
    def _placeholder_scope(self):
        """
        Provides an isolated placeholder store for a single shell run.

        A stack is used so nested shell runs (e.g. magics invoking __shell__.run)
        keep their placeholders separate.
        """
        previous = getattr(self, "_placeholders", {})
        self._placeholder_stack.append(previous)
        self._placeholders = {}
        try:
            yield self._placeholders
        finally:
            prior = self._placeholder_stack.pop() if self._placeholder_stack else {}
            self._placeholders = prior if prior is not None else {}

    def run(self, code, globals=None, locals=None,silent=False,filename=None):
        """
        Execute the given code in the shell environment.

        Args:
            code (str): The Python code to execute.
            globals (dict, optional): Global namespace to use. If None, uses self.namespace.
            locals (dict, optional): Local namespace to use. If None, globals will be used.

        Returns:
            ShellResponse: An object containing the results of the execution.

        This method is the main entry point for code execution in the Shell.
        It handles the entire execution process, including calling various hooks,
        managing the execution environment, and capturing outputs and exceptions.
        """

        if self.input_hook:
            self.input_hook(code)

        with self._placeholder_scope():
            code=self._parse_system_cmd(code)
            code=self._parse_magics(code)

            if self.pre_run_hook:
                processed_code = self.pre_run_hook(code)
            else:
                processed_code=code

            # Increment input counter and set current filename
            self._input_counter+=1
            if filename is not None:
                self._current_filename=filename
            else:
                self._current_filename=f"<shell-input-{self._input_counter}>"
            filename=self._current_filename

            self._current_code=processed_code
            
            if globals is None:
                globals=self.namespace

            if locals is None:
                locals=globals

            old_globals = dict(globals)

            self.last_result = None

            if silent:
                stdout_hook=lambda token,content:None
                stderr_hook=lambda token,content:None
            else:
                stdout_hook=self.stdout_hook 
                stderr_hook=self.stderr_hook

            collector = Collector(stdout_hook=stdout_hook, stderr_hook=stderr_hook, exception_hook=self.exception_hook, stdin_hook=self.stdin_hook, shell=self)
            with collector:
                try:
                    source = ASTTokens(processed_code, parse=True)
                    nodes = source.tree.body
                    for i, node in enumerate(nodes):
                        # Check for semicolon
                        next_token = source.next_token(node.last_token)
                        suppress_result = (next_token and next_token.string == ';')

                        # Check for last node
                        is_last_node = (i == len(nodes) - 1)
                        
                        # Extract the block of code associated with the current node.
                        startpos = node.first_token.startpos
                        endpos = next_token.endpos if suppress_result else node.last_token.endpos
                        code_block = source.text[startpos:endpos]

                        # send to code_block_hook for monitoring and execute the block
                        if self.code_block_hook:
                            self.code_block_hook(code_block)
                        line_no, column = node.first_token.start
                        globals,locals=self._execute(node, source, globals,locals, suppress_result, is_last_node)
                except:
                    # Raise any uncaught exception so that the collector may catch it
                    raise

            if self.namespace_change_hook:
                self.namespace_change_hook(old_globals, globals, locals)

            if '__' in globals:
                globals.update(___=globals['__'])
            if '_' in globals:
                globals.update(__=globals['_'])
                
            globals.update(_=self.last_result)

            response = ShellResponse(
                input=code,
                processed_input=processed_code,
                stdout=collector.get_stdout(), 
                stderr=collector.get_stderr(), 
                result=self.last_result, 
                exception=collector.exception,
            )
        
            if self.post_run_hook:
                response=self.post_run_hook(response)

            # Add to history
            self.add_to_history(filename,response)

            return response
    
    def add_to_history(self, filename, response):
        """Adds a response to the history, maintaining the history size limit.
        Args:
            rank (int): The rank or identifier for the response.
            response (ShellResponse): The response object to add to history.
        """
        self.history[filename]=response
        while len(self.history)>self.history_size:
            self.history.popitem(last=False)
    
    def display(self,obj):
        """
        Default method to display an object.

        Args:
            obj: The object to be displayed.

        This method attempts to use self.display_hook if provided,
        or falls back to printing the repr of the object.
        """
        if obj is not None:
            if self.display_hook:
                self.display_hook(obj)
            else:
                print(repr(obj))


    def interact(self):
        """
        Starts an interactive shell session with multiline input support.
        """

        print("Welcome to the interactive Python shell.") 
        print("Use Alt+Enter to submit your input.")
        print("Type 'exit()' to exit the shell.")

        loop=True

        def custom_exit():
            nonlocal loop
            loop=False

        self.update_namespace(exit=custom_exit)
        
        while loop:
            try:
                code = prompt(">>> ",prompt_continuation="... ")
                self.run(code)
            except KeyboardInterrupt:
                print("\nKeyboardInterrupt")
            except EOFError:
                break
            except Exception as e:
                print(f"An error occurred: {e}")

        print("Exiting interactive shell.")

    def ensure_builtins(self):
        """Ensures built-in functions and classes are available in the namespace."""
        self.update_namespace(
            __builtins__=builtins,
            display=self.display,
            __magics__=self.magics,
            __shell__=self,
            magic=self.register_magic
        )

    def reset_namespace(self):
        """
        Clears the namespace, retaining only built-in functions and classes.

        This method is useful for resetting the shell to its initial state,
        clearing all user-defined variables and functions while keeping builtins.
        """
        self.namespace.clear()
        self.magics={}
        self.ensure_builtins()

    def update_namespace(self, *args, **kwargs):
        """
        Dynamically updates the namespace with provided variables or functions.

        Args:
            *args: Dictionaries of items to add to the namespace.
            **kwargs: Key-value pairs to add to the namespace.

        This method allows for real-time modifications to the execution environment,
        adding new variables or functions that will be available in subsequent code executions.
        """
        self.namespace.update(*args, **kwargs)

    def set_namespace(self, namespace):
        """
        Dynamically sets the namespace reference to a chosen dict.

        Args:
            namespace (dict): The namespace the console will use 
        """
        if isinstance(namespace,dict):
            self.namespace=namespace
            self.ensure_builtins()
        else:
            raise TypeError("The Shell's namespace should always be a dict.")
        
if __name__=='__main__':
    Shell().interact()

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
import tokenize
import subprocess

from contextlib import contextmanager
from typing import Any, Callable, Optional, Union, Literal
from .utils import Thread, short_id, prompt
from .collector import Collector
from .magics import MagicParser


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

class _MISSING:
    """
    A sentinel class to represent missing values in the Shell
    """
    pass

MISSING=_MISSING()

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
        history (OrderedDict): Cache of past executions.
        history_size (int): Maximum number of past executions to cache.
        current_code (str): The current code being executed.
        last_result (Any): The result of the last execution.
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
        self._magic_parser=MagicParser()
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

        process = subprocess.Popen(
            command, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1
        )

        t_out = Thread(target=_stream_output, args=(process.stdout, sys.stdout))
        t_err = Thread(target=_stream_output, args=(process.stderr, sys.stderr))
        if self.add_script_run_ctx_hook:
            self.add_script_run_ctx_hook(t_out,self.get_script_run_ctx_hook())
            self.add_script_run_ctx_hook(t_err,self.get_script_run_ctx_hook())
        t_out.start()
        t_err.start()
        t_out.join()
        t_err.join()

        return process.wait()


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
            result = eval(compiled_code, globals,locals)
            self.last_result=result
            if not suppress_result:
                if self.display_mode == 'all' or (self.display_mode == 'last' and is_last_node):
                    self.display(result)
        else:
            self.last_result=None
            compiled_code = compile(ast.Module([node], type_ignores=[]), filename=self._current_filename, mode='exec')
            exec(compiled_code, globals,locals)

        if self.post_execute_hook:
            self.post_execute_hook(node, self.last_result)

        return globals,locals

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

        with self._magic_parser._placeholder_scope():
            code=self._magic_parser._parse_system_cmd(code)
            code=self._magic_parser._parse_magics(code)

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
        """Add a ``ShellResponse`` to the cache, enforcing the size limit.

        Args:
            filename: Synthetic filename (e.g. ``<shell-input-1>``) used as the
                history key.
            response: The response object to add to history.
        """
        self.history[filename]=response
        while len(self.history)>self.history_size:
            self.history.popitem(last=False)
    
    def display(self,obj,**kwargs):
        """
        Default method to display an object.

        Args:
            obj: The object to be displayed.
            **kwargs: Optional arguments to pass to the display hook
                (e.g., backend='json' for custom display backends).

        This method attempts to use self.display_hook if provided,
        passing any additional kwargs to it. Falls back to printing
        the repr of the object if no hook is configured.
        """
        if obj is not None:
            if self.display_hook:
                self.display_hook(obj,**kwargs)
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

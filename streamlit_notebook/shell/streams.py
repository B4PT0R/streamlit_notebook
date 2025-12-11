import io
from typing import Optional, Callable
from collections import deque
import sys
from .utils import prompt

def stdout_write(data: str, buffer: str) -> None:
    """Default stdout hook that mirrors captured output to the real stdout."""
    if isinstance(sys.stdout, Stream):
        sys.__stdout__.write(data)
        sys.__stdout__.flush()
    else:
        sys.stdout.write(data)
        sys.stdout.flush()

def stderr_write(data: str, buffer: str) -> None:
    """Default stderr hook that mirrors captured output to the real stderr."""
    if isinstance(sys.stderr, Stream):
        sys.__stderr__.write(data)
        sys.__stderr__.flush()
    else:
        sys.stderr.write(data)
        sys.stderr.flush()

def stdin_readline() -> str:
    """Fallback stdin hook that reads from the console."""
    if isinstance(sys.stdin, StdinProxy):
        return prompt("", multiline=False)
    else:
        return sys.stdin.readline()

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
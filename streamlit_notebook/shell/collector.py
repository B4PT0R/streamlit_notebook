import sys
from .streams import Stream, StdinProxy, stdout_write, stderr_write, stdin_readline

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
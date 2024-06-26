import sys
import traceback
import io
import builtins
import ast
from asttokens import ASTTokens
from asttokens.util import walk,visit_tree

def debug_print(content):
    sys.__stdout__.write(repr(content)+'\n')

class Stream(io.IOBase):
    """
    Custom io stream that intercepts stdout and stderr streams.
    This class manages text data by buffering it and optionally passing it through a hook
    for real-time processing and display. It ensures efficient data handling by
    maintaining a maximum buffer size and flushing data when this size is exceeded or on newlines.
    """
    def __init__(self, hook=None, buffer_size=2048):
        super().__init__()
        self.hook = hook
        self.buffer_size = buffer_size
        self.buffer = ""
        self.cache_buffer = ""

    def write(self, data):
        """
        Writes data to the buffer, flushing complete lines or when buffer exceeds max size.
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

    def flush(self, data_to_flush=None):
        """
        Flushes the given data to the hook and caches it. 
        If no data is given, flushes the current buffer.
        """
        if data_to_flush is None:
            data_to_flush = self.buffer
            self.buffer = ""

        if self.hook:
            self.hook(data_to_flush,self.cache_buffer)
        self.cache_buffer += data_to_flush

    def get_value(self):
        """
        Returns all text that has been written to this stream.
        """
        return self.cache_buffer

class Collector:
    """
    Manages stdout and stderr redirection within a context manager.
    It captures all output and exceptions, allowing fine control over their handling and display.
    """
    def __init__(self, stdout_hook=None, stderr_hook=None,exception_hook=None):
        self.stdout_hook = stdout_hook
        self.stderr_hook = stderr_hook
        self.exception_hook=exception_hook
        self.stdout_stream = Stream(hook=self.stdout_hook)
        self.stderr_stream = Stream(hook=self.stderr_hook)
        self.exception = None

    def get_stdout(self):
        return self.stdout_stream.get_value()
    
    def get_stderr(self):
        return self.stderr_stream.get_value()

    def __enter__(self):
        self.saved_stdout = sys.stdout
        self.saved_stderr = sys.stderr
        sys.stdout = self.stdout_stream
        sys.stderr = self.stderr_stream
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.stdout_stream.flush()
        self.stderr_stream.flush()
        sys.stdout = self.saved_stdout
        sys.stderr = self.saved_stderr
        if exc_type is not None:
            self.exception = exc_value
            error_message = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            self.stderr_stream.write(error_message)
            self.stderr_stream.flush()
            if self.exception_hook:
                self.exception_hook(exc_value)
            return True  # Suppress exception propagation

class ShellResponse:
    """
    Represents the results of code execution, encapsulating stdout, stderr, results, and exceptions.
    """
    def __init__(self, input=None, stdout=None, stderr=None, result=None, exception=None):
        self.input = input
        self.stdout = stdout
        self.stderr = stderr
        self.result = result
        self.exception = exception

class Shell:
    """
    Executes Python code within a managed environment and captures the output and exceptions.
    This class is designed to be extensible through various hooks that allow custom handling 
    of input, output, results, and exceptions, providing flexibility to tailor its functionality 
    to specific needs.
    """
    def __init__(self, namespace=None, stdout_hook=None, stderr_hook=None, input_hook=None, result_hook=None, exception_hook=None, preprocess_hook=None, code_hook=None):
        # Initialize the shell with optional namespace and hooks for various stages of code execution.
        self.namespace = namespace or {"__builtins__": builtins}
        self.stdout_hook = stdout_hook
        self.stderr_hook = stderr_hook
        self.input_hook = input_hook
        self.result_hook = result_hook
        self.exception_hook = exception_hook
        self.preprocess_hook = preprocess_hook
        self.code_hook = code_hook

    def preprocess(self, code):
        # Apply preprocessing to the code if a preprocess hook is provided; otherwise, return the code unchanged.
        return self.preprocess_hook(code) if self.preprocess_hook else code

    def execute(self, node, suppress_result=False):
        """
        Execute a single AST node. This method determines how to compile and execute the node
        and whether to suppress the output based on a trailing semicolon.
        """
        if isinstance(node, ast.Expr):
            # Compile and evaluate expression nodes.
            compiled_code = compile(ast.Expression(node.value), filename="<ast>", mode='eval')
            self.last_result = eval(compiled_code, self.namespace)
            # Only invoke the result hook if output is not suppressed.
            if self.result_hook and not suppress_result:
                self.result_hook(self.last_result)
        else:
            # Compile and execute all other types of statements.
            compiled_code = compile(ast.Module([node], []), filename="<ast>", mode='exec')
            exec(compiled_code, self.namespace)

    def run(self, code):
        # This method processes the input code, handling tokenization and execution of each node.
        if self.input_hook:
            self.input_hook(code)
        processed_code = self.preprocess(code)

        self.last_result = None
        collector = Collector(stdout_hook=self.stdout_hook, stderr_hook=self.stderr_hook, exception_hook=self.exception_hook)
        with collector:
            try:
                source = ASTTokens(processed_code, parse=True)
                for node in source.tree.body:
                    # Check the next token after the current node to see if it's a semicolon.
                    next_token = source.next_token(node.last_token)
                    startpos = node.first_token.startpos
                    if next_token.string == ";":
                        endpos = node.last_token.endpos + 1
                        suppress_result = True
                    else:
                        endpos = node.last_token.endpos
                        suppress_result = False
                    # Extract the block of code associated with the current node.
                    code_block = source.text[startpos:endpos]
                    if self.code_hook:
                        self.code_hook(code_block)
                    self.execute(node, suppress_result)
            except:
                # Raise any uncaught exception so that the collector may catch it
                raise

        return ShellResponse(
            input=code, 
            stdout=collector.get_stdout(), 
            stderr=collector.get_stderr(), 
            result=self.last_result, 
            exception=collector.exception
        )

    def reset_namespace(self):
        """
        Clears the namespace, retaining only built-in functions and classes.
        This method is useful for resetting the state between executions to avoid cross-contamination of run contexts.
        """
        self.namespace.clear()
        self.namespace["__builtins__"] = builtins

    def update_namespace(self, *args, **kwargs):
        """
        Dynamically updates the namespace with provided variables or functions,
        allowing for modifications to the execution environment in real-time.
        """
        self.namespace.update(*args, **kwargs)
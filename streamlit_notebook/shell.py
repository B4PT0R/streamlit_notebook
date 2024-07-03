"""
Shell Module

This module provides a flexible and extensible Python code execution environment.
It allows for fine-grained control over code execution, input/output handling,
and namespace management through various hooks and customization options.

Key Components:
- Shell: The main class for executing Python code in a controlled environment.
- ShellResponse: A class representing the result of code execution.
- Collector: A context manager for capturing stdout, stderr and exceptions.
- Stream: A custom IO stream for efficient text handling and optional routing of outputs to a hook.

Example Usage:

    def custom_input_hook(code):
        print(f"Executing code: {code}")

    def custom_pre_run_hook(code):
        return f"print('Pre-run hook executed')\n{code}"

    def custom_code_hook(code_block):
        print(f"Executing block: {code_block.strip()}")

    def custom_pre_execute_hook(node, source):
        # Demonstrate the power of ASTTokens for source tracking
        start, end = source.get_text_range(node)
        node_source = source.text[start:end]
        print(f"Executing node of type {type(node).__name__}:")
        print(f"  Source: {node_source.strip()}")
        print(f"  Line number: {source.get_line_numbers(node)[0]}")
        return node

    def custom_display_hook(result):
        print(f"Result: {result}")

    def custom_namespace_change_hook(old_globals, new_globals, locals):
        print("Namespace changes:")
        for key in set(new_globals) - set(old_globals):
            print(f"  Added: {key} = {new_globals[key]}")
        return new_globals

    shell = Shell(
        namespace={"custom_var": 42},
        input_hook=custom_input_hook,
        pre_run_hook=custom_pre_run_hook,
        code_hook=custom_code_hook,
        pre_execute_hook=custom_pre_execute_hook,
        display_hook=custom_display_hook,
        namespace_change_hook=custom_namespace_change_hook,
        display_mode='all'
    )

    code = '''
    print(f"Custom variable: {custom_var}")
    new_variable = "I'm a new variable"
    for i in range(3):
        print(f"Loop iteration {i}")
    1+1
    '''

    response = shell.run(code)

    print("\nExecution complete. Results:")
    print(f"Stdout: {response.stdout}")
    print(f"Last result: {response.result}")
    print(f"New variables: {set(response.new_globals) - set(response.old_globals)}")

This example demonstrates:
1. Custom input and pre-run hooks for logging and code modification
2. A code hook that logs each code block before execution
3. A pre-execute hook that uses ASTTokens to provide detailed source information for each node
4. A custom display hook for formatting results
5. A namespace change hook that tracks new variables
6. The use of a custom initial namespace
7. Handling of multi-line code input
8. Accessing various attributes of the ShellResponse

"""

import sys
import traceback
import io
import builtins
import ast
from asttokens import ASTTokens

def debug_print(content):
    sys.__stdout__.write(repr(content)+'\n')

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
    def __init__(self, hook=None, buffer_size=2048):
        super().__init__()
        self.hook = hook
        self.buffer_size = buffer_size
        self.buffer = ""
        self.cache_buffer = ""

    def write(self, data):
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

    def flush(self, data_to_flush=None):
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
        

    def get_value(self):
        """
        Returns all text that has been written to this stream.

        Returns:
            str: The entire content that has been written to the stream.
        """
        return self.cache_buffer

class Collector:
    """
    Manages stdout and stderr redirection within a context manager.

    This class captures all output and exceptions, allowing fine control over their handling and display.

    Attributes:
        stdout_hook (callable): Optional function to process stdout in real-time.
        stderr_hook (callable): Optional function to process stderr in real-time.
        exception_hook (callable): Optional function to process exceptions.
        stdout_stream (Stream): Custom stream for capturing stdout.
        stderr_stream (Stream): Custom stream for capturing stderr.
        exception (Exception): Stores any exception raised during execution.

    Methods:
        get_stdout(): Returns all that was written to the stdout stream.
        get_stderr(): Returns all that was written to the stderr stream.
    """
    def __init__(self, stdout_hook=None, stderr_hook=None,exception_hook=None):
        self.stdout_hook = stdout_hook
        self.stderr_hook = stderr_hook
        self.exception_hook=exception_hook
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

        This method redirects sys.stdout and sys.stderr to stdout and stderr Streams.

        Returns:
            Collector: The Collector instance.
        """
        self.saved_stdout = sys.stdout
        self.saved_stderr = sys.stderr
        sys.stdout = self.stdout_stream
        sys.stderr = self.stderr_stream
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
        # Deal with any unhandled exception
        if exc_type is not None:
            # Save the exception
            self.exception = exc_value
            # Send the traceback to stderr_stream and flush
            error_message = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            self.stderr_stream.write(error_message)
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
        old_globals (dict): The global namespace before execution.
        new_globals (dict): The global namespace after execution.
        locals (dict): The local namespace after execution.
    """
    def __init__(self, input=None, processed_input=None, stdout=None, stderr=None, result=None, exception=None, old_globals=None, new_globals=None, locals=None):
        self.input = input
        self.processed_input=processed_input
        self.stdout = stdout
        self.stderr = stderr
        self.result = result
        self.exception = exception
        self.old_globals=old_globals
        self.new_globals=new_globals
        self.locals=locals

class Shell:
    """
    Executes Python code within a managed environment and captures output and exceptions.

    This class provides a flexible and extensible Python code execution environment.
    It allows for fine-grained control over code execution, input/output handling,
    and namespace management through various hooks and customization options.

    Attributes:
        namespace (dict): The global namespace for code execution.
        display_mode (str): Controls when results are displayed ('all', 'last', or 'none').

    Methods:
        run(code, globals, locals): Execute the given code in the shell environment.
        execute(node, source, globals, locals, suppress_result, is_last_node):
            Execute a single AST node in the given namespace.
        reset_namespace(): Clears the namespace, retaining only built-in functions and classes.
        update_namespace(*args, **kwargs): Dynamically updates the namespace with provided variables or functions.
        display(obj): Default method to display an object.

    The class supports various hooks that can be set to customize behavior:
        input_hook(code): Called before processing the input code.
        pre_run_hook(code): Preprocesses the input code.
        code_hook(code_block): Called for each code block before execution.
        pre_execute_hook(node, source): Allows modification of AST nodes before execution.
        post_execute_hook(node, result): Called after each node execution with the node and its result.
        display_hook(result): Called to display the result of an expression evaluation.
        stdout_hook(data, full_buffer): Called when data is written to stdout.
        stderr_hook(data, full_buffer): Called when data is written to stderr.
        exception_hook(exception): Called when an exception occurs during execution.
        namespace_change_hook(old_globals, new_globals, locals): Called after execution to process namespace changes.
        post_run_hook(response): Called after execution with the ShellResponse.
    """

    def __init__(self, namespace=None, stdout_hook=None, stderr_hook=None, input_hook=None, 
                 display_hook=None, exception_hook=None, preprocess_hook=None, code_hook=None, 
                 display_mode='last', pre_run_hook=None, post_run_hook=None, 
                 pre_execute_hook=None, post_execute_hook=None, 
                 namespace_change_hook=None):
        
        self.namespace = namespace or {"__builtins__": builtins}
        self.display_mode = display_mode
        self.update_namespace(
            display=self.display # default display function
        )
        
        self.input_hook = input_hook
        self.code_hook = code_hook
        self.stdout_hook = stdout_hook
        self.stderr_hook = stderr_hook
        self.display_hook = display_hook
        self.exception_hook = exception_hook
        self.pre_run_hook = pre_run_hook
        self.post_run_hook = post_run_hook
        self.pre_execute_hook = pre_execute_hook
        self.post_execute_hook = post_execute_hook
        self.namespace_change_hook = namespace_change_hook

    def execute(self, node, source, globals, locals, suppress_result=False, is_last_node=False):
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
            compiled_code = compile(ast.Expression(node.value), filename="<ast>", mode='eval')
            self.last_result = eval(compiled_code, globals,locals)
            if self.display_hook and not suppress_result:
                if self.display_mode == 'all' or (self.display_mode == 'last' and is_last_node):
                    self.display_hook(self.last_result)
        else:
            compiled_code = compile(ast.Module([node], type_ignores=[]), filename="<ast>", mode='exec')
            exec(compiled_code, globals,locals)

        if self.post_execute_hook:
            self.post_execute_hook(node, self.last_result)

        return globals,locals

    def run(self, code, globals=None, locals=None):
        """
        Execute the given code in the shell environment.

        Args:
            code (str): The Python code to execute.
            globals (dict, optional): Global namespace to use. If None, uses self.namespace.
            locals (dict, optional): Local namespace to use. If None, an empty dict is created.

        Returns:
            ShellResponse: An object containing the results of the execution.

        This method is the main entry point for code execution in the Shell.
        It handles the entire execution process, including calling various hooks,
        managing the execution environment, and capturing outputs and exceptions.
        """

        if self.input_hook:
            self.input_hook(code)

        if self.pre_run_hook:
            processed_code = self.pre_run_hook(code)
        else:
            processed_code=code

        if globals is None:
            globals=self.namespace

        if locals is None:
            locals=dict()

        old_globals = dict(globals)

        self.last_result = None
        collector = Collector(stdout_hook=self.stdout_hook, stderr_hook=self.stderr_hook, exception_hook=self.exception_hook)
        with collector:
            try:
                source = ASTTokens(processed_code, parse=True)
                nodes = source.tree.body
                for i, node in enumerate(nodes):
                    # Check for semicolon
                    next_token = source.next_token(node.last_token)
                    suppress_result = (next_token and next_token.string == ';')
                    
                    # Extract the code block
                    startpos = node.first_token.startpos
                    endpos = next_token.endpos if suppress_result else node.last_token.endpos
                    code_block = source.text[startpos:endpos]

                    # Extract the block of code associated with the current node.
                    code_block = source.text[startpos:endpos]
                    if self.code_hook:
                        self.code_hook(code_block)
                    is_last_node = (i == len(nodes) - 1)
                    globals,locals=self.execute(node, source, globals,locals, suppress_result, is_last_node)
            except:
                # Raise any uncaught exception so that the collector may catch it
                raise

        if self.namespace_change_hook:
            globals=self.namespace_change_hook(old_globals, globals, locals)
        else:
            globals.update(locals)

        response = ShellResponse(
            input=code,
            processed_input=processed_code,
            stdout=collector.get_stdout(), 
            stderr=collector.get_stderr(), 
            result=self.last_result, 
            exception=collector.exception,
            old_globals=old_globals,
            new_globals=globals,
            locals=locals
        )
    
        if self.post_run_hook:
            response=self.post_run_hook(response)

        return response
    
    def display(self,obj):
        """
        Default method to display an object.

        Args:
            obj: The object to be displayed.

        This method attempts to use self.display_hook if provided,
        or falls back to printing the repr of the object.
        """

        if self.display_hook:
            self.display_hook(obj)
        else:
            print(repr(obj))

    def reset_namespace(self):
        """
        Clears the namespace, retaining only built-in functions and classes.

        This method is useful for resetting the shell to its initial state,
        clearing all user-defined variables and functions while keeping Python builtins.
        """
        self.namespace.clear()
        self.namespace["__builtins__"] = builtins
        self.update_namespace(
            display=self.display
        )

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

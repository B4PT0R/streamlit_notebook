"""Echo code execution context manager for Streamlit notebooks.

This module provides an adaptation of Streamlit's echo functionality
customized for the notebook interactive environment.

The :class:`echo` context manager displays the code being executed
alongside its output, making it perfect for tutorials and demonstrations.

Examples:
    Basic usage::

        with st.echo():
            st.write("This code will be shown above the output")
            x = 42
            st.write(f"The answer is {x}")

Note:
    This is an adapted version of Streamlit's echo module.
    All credits to the Streamlit developers.
"""

from __future__ import annotations

import ast
import contextlib
import textwrap
import traceback
from typing import Callable, Optional, Iterator, Literal
import streamlit as st

class echo:
    """Context manager for displaying code alongside its execution.

    This class provides functionality to display the code being executed
    along with its output in a Streamlit app, perfect for tutorials and demonstrations.

    Attributes:
        current_code_hook: Optional function to retrieve the current code.
            If provided, this function will be called to get the source code
            instead of reading from the file system.

    Examples:
        Basic usage (code shown above output)::

            with st.echo():
                st.write('This code will be printed')
                x = 1 + 1

        Show code below output::

            with st.echo(code_location="below"):
                st.write('Output appears first')

    Note:
        The echo instance must be callable. When used as ``st.echo()``,
        it calls the :meth:`__call__` method which returns the context manager.
    """

    def __init__(self, current_code_hook: Optional[Callable[[], str]] = None) -> None:
        """Initialize the echo context manager.

        Args:
            current_code_hook: Optional function that returns the current code
                as a string. If None, code is read from the file system.
        """
        self.current_code_hook = current_code_hook

    @contextlib.contextmanager
    def __call__(self, code_location: Literal["above", "below"] = "above") -> Iterator[None]:
        """Create a context manager that displays and executes code.

        Use in a ``with`` block to draw code on the app, then execute it.

        Args:
            code_location: Whether to show the echoed code before (``"above"``)
                or after (``"below"``) the execution results. Defaults to ``"above"``.

        Yields:
            None - This is a context manager, code is executed in its context.

        Examples:
            Show code above output (default)::

                with st.echo():
                    st.write('This text appears below the code')

            Show code below output::

                with st.echo(code_location="below"):
                    st.write('This text appears above the code')

        Note:
            If the code cannot be retrieved (e.g., file not found), a warning
            will be displayed instead of the code.
        """

        from streamlit import source_util

        if code_location == "above":
            placeholder = st.empty()

        try:
            # Get stack frame *before* running the echoed code. The frame's
            # line number will point to the `st.echo` statement we're running.
            frame = traceback.extract_stack()[-3]
            filename, start_line = frame.filename, frame.lineno

            if self.current_code_hook is None:
                # Read the file containing the source code of the echoed statement.
                with source_util.open_python_file(filename) as source_file:
                    source_lines = source_file.readlines()
            else:
                # Read the passed source code directly
                source_lines=self.current_code_hook().splitlines(True)

            # Use ast to parse the Python file and find the code block to display
            root_node = ast.parse("".join(source_lines))
            line_to_node_map = {}

            def collect_body_statements(node: ast.AST) -> None:
                if not hasattr(node, "body"):
                    return
                for child in node.body:  # type: ignore
                    line_to_node_map[child.lineno] = child
                    collect_body_statements(child)

            collect_body_statements(root_node)

            # In AST module the lineno (line numbers) are 1-indexed,
            # so we decrease it by 1 to lookup in source lines list
            echo_block_start_line = line_to_node_map[start_line].body[0].lineno - 1
            echo_block_end_line = line_to_node_map[start_line].end_lineno
            lines_to_display = source_lines[echo_block_start_line:echo_block_end_line]

            code_string = textwrap.dedent("".join(lines_to_display))

            # draw the code string to the app.
            if code_location=="above":
                with placeholder:
                    st.code(code_string)

            # Run the echoed code...
            yield

            
            if not code_location=="above":
                st.code(code_string)

        except Exception as err:
            if code_location=="above":
                with placeholder:
                    st.warning("Unable to display code. %s" % err)
            else:
                st.warning("Unable to display code. %s" % err)

    



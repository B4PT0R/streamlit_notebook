"""Cell type definitions for streamlit-notebook.

This module provides the cell type classes that define how different
types of cells (code, markdown, HTML) are executed and displayed.

Cell Types:
    - :class:`CellType`: Base interface for all cell types
    - :class:`PyType`: Python code execution type
    - :class:`MDType`: Markdown rendering type
    - :class:`HTMLType`: HTML rendering type

See Also:
    :class:`~streamlit_notebook.cell.Cell`: Main cell class
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import streamlit as st
from .utils import format

if TYPE_CHECKING:
    from .cell import Cell

class CellType:

    """
    Class acting as an interface for cell types.

    A cell type is a class that defines how a cell is executed and displayed.
    It is used by the Cell class to define the behavior of a cell based on its type.
    Subclasses need to expose:
    - self.language: the language of the cell
    - self.type: the type of the cell
    - self.has_fragment_toggle: whether the cell has a fragment toggle
    - self.has_reactive_toggle: whether the cell has a reactive toggle
    - self.exec(): the method to execute the cell
    - self.get_exec_code(): the method to get the code to execute
    - self.is_reactive(): the method to check if the cell is reactive
    - self.is_fragment(): the method to check if the cell is a fragment
    or inherit the defaults
    """

    def __init__(self,cell):
        self.cell:Cell=cell
        self.has_fragment_toggle=True
        self.has_reactive_toggle=True
        self.language='python'
        self.type=None

    def is_reactive(self):
        return self.cell._reactive

    def is_fragment(self):
        return self.cell._fragment

    def exec(self):
        """
        Executes the code returned by self.get_exec_code()
        """
        with self.cell:
            response=self.cell.notebook.shell.run(self.cell._get_exec_code(),filename=f"<{self.cell.id}>")
        self.cell._set_output(response)


    def get_exec_code(self):
        return self.cell.code

class PyType(CellType):

    def __init__(self,cell):
        super().__init__(cell)
        self.language='python'
        self.type="code"

    def get_exec_code(self):
        return self.cell.code

    def exec(self):
        """
        Executes the cell code.

        This method chooses between normal execution and fragment execution
        based on the cell's fragment attribute.
        """
        if self.cell.fragment:
            self._exec_as_fragment()
        else:
            self._exec_normally()


    @st.fragment
    def _exec_as_fragment(self):
        """
        Executes the cell as a Streamlit fragment.

        This method is decorated with @st.fragment and executes
        the cell's code within a Streamlit fragment context.
        """
        with self.cell:
            response=self.cell.notebook.shell.run(self.cell._get_exec_code(),filename=f"<{self.cell.id}>")
        self.cell._set_output(response)

    def _exec_normally(self):
        """
        Executes the cell normally.

        This method runs the cell's code in the normal execution context.
        """
        with self.cell:
            response=self.cell.notebook.shell.run(self.cell._get_exec_code(),filename=f"<{self.cell.id}>")
        self.cell._set_output(response)

class MDType(CellType):

    def __init__(self,cell):
        super().__init__(cell)
        self.language='markdown'
        self.type="markdown"
        self.has_fragment_toggle=False
        self.has_reactive_toggle=False

    def is_reactive(self):
        return True

    def is_fragment(self):
        return False

    def get_exec_code(self):
        """
        Formats the Markdown code and converts it to a st.markdown call.

        Returns:
            str: A string containing a st.markdown() call with the formatted Markdown content.

        This method processes the cell's content, formats any variables,
        and wraps it in a Streamlit markdown function call.
        """
        formatted_code=format(self.cell.code,**self.cell.notebook.shell.namespace).replace("'''","\'\'\'")
        code=f"st.markdown(r'''{formatted_code}''');"
        return code

class HTMLType(CellType):

    def __init__(self,cell):
        super().__init__(cell)
        self.language='markdown'
        self.type="html"
        self.has_fragment_toggle=False
        self.has_reactive_toggle=False

    def is_reactive(self):
        return True

    def is_fragment(self):
        return False

    def get_exec_code(self):
        """
        Formats the HTML code and converts it to a st.html call.

        Returns:
            str: A string containing a st.html() call with the formatted HTML content.

        This method processes the cell's content, formats any variables,
        and wraps it in a Streamlit html function call.
        """
        formatted_code=format(self.cell.code,**self.cell.notebook.shell.namespace).replace("'''","\'\'\'")
        code=f"st.html(r'''{formatted_code}''');"
        return code

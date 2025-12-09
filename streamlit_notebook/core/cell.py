"""Cell classes for streamlit-notebook.

This module provides the main Cell abstraction for streamlit-notebook,

It implements the wrapping :class:`Cell` class.

Cell delegates its functionning to the :class:`BaseCellType` class and its subclasses, via its _cell_type attribute.
This architecture allows for full flexibility of custom cell behaviour under the same Cell interface.
It also enables changing a cell's type dynamically without having to recreate the instance of the Cell object

Supported Cell Types:
    - 'code' (:class:`PyType`): Python code execution with output capture
    - 'markdonw' (:class:`MDType`): Formatted text with variable interpolation
    - 'html' (:class:`HTMLType`): Raw HTML rendering with variable interpolation
    This list can be easily extended with new cell types by subclassing BaseCellType
    and adding the corresponding type entry in Cell._supported_types class dictionary

Cells support:
    - Selective reactivity (auto-rerun on changes if reactive=True)
    - Fragment execution (Streamlit fragments for performance)
    - One-shot execution (run once, then skip)
    - Output capture (stdout, stderr, results, exceptions)

Examples:
    Cells are typically created via notebook decorators::

        @nb.cell(type='code')
        def analyze():
            import pandas as pd
            df = pd.DataFrame({'x': [1, 2, 3]})
            st.dataframe(df)

        @nb.cell(type='markdown')
        def explanation():
            '''
            # Results
            The data has <<len(df)>> rows.
            '''

See Also:
    :class:`~streamlit_notebook.notebook.Notebook`: Notebook orchestrator
    :class:`~streamlit_notebook.cell.Cell`: Main Cell wrapper
    :class:`~streamlit_notebook.cell_ui.CellUI`: Cell UI components
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Literal
from types import NoneType
import streamlit as st
from streamlit_notebook.core.shell import short_id
from .cell_types import BaseCellType, PyType, MDType, HTMLType

if TYPE_CHECKING:
    from .notebook import Notebook

state = st.session_state

class Cell:

    """
    Main Cell class for streamlit-notebook.
    Acts as a wrapper for specialized cell types.
    Refer to BaseCellType for the full implementation of Cell functionality.
    """

    _supported_types=dict(
        code=PyType,
        markdown=MDType,
        html=HTMLType
    )

    @classmethod
    def _to_type_class(cls,type:str) -> BaseCellType:
        """Returns the cell type class for a given type string."""
        if type in cls._supported_types:
            return cls._supported_types[type]
        else:
            raise NotImplementedError(f"Cell type {type} not implemented")
        
    @classmethod
    def from_dict(cls, d:dict)-> Cell:
        """
        Creates a cell from a dictionary representation.

        Args:
           d (dict): A dictionary containing the cell's attributes.

        Returns:
           Cell: A new Cell object created from the dictionary.
        """        
        # Create a new cell with the dictionary values
        cell = cls(
            d.get("key", short_id()), 
            d.get("type", "code"),
            d.get("code", ""),
            d.get("reactive", False),
            d.get("fragment", False)
        )
        return cell

    def __init__(self,key,type="code",code="",reactive=False,fragment=False):
        """
        Initializes a new cell instance.

        Args:
            key (str): A unique identifier for the cell.
            type (str, optional): The type of cell. Defaults to "code".
            code (str, optional): The code content of the cell. Defaults to ""
            reactive (bool, optional): Whether the cell is reactive. Defaults to False.
            fragment (bool, optional): Whether the cell is a fragment. Defaults to False.
        """

        self._cell_type: BaseCellType = self._to_type_class(type)(self,key,type,code,reactive,fragment)
        self._notebook : Notebook = None

    @property
    def notebook(self) -> Notebook:
        from .notebook import Notebook
        if not isinstance(self._notebook, Notebook):
            raise RuntimeError(f"This cell (key={self.key}) must be linked to a notebook to be fully functional. Call `notebook.add_cell(cell)` before calling any of its notebook-bound methods or proteries.")
        return self._notebook

    @notebook.setter
    def notebook(self, value: Optional[Notebook]) -> None:
        from .notebook import Notebook
        if not isinstance(value,(Notebook, NoneType)):
            raise TypeError(f"Expected None or a Notebook instance, got {type(value)}")
        self._notebook=value

    @notebook.deleter
    def notebook(self) -> None:
        self._notebook=None

    # Context manager methods

    def __enter__(self) -> Cell:
        """
        Allows using the cell as a context manager.

        This method enables running code in the shell and directing its outputs to the cell
        by switching the notebook.current_cell property.

        Returns:
            Cell: The current cell instance.

        Example:
            with cell:
                notebook.shell.run(code)  # all shell outputs will be directed to the cell
        """
        self.saved_cell = self._cell_type.notebook.current_cell
        self._cell_type.notebook.current_cell = self
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, exc_tb: Any) -> None:
        """
        Restores the notebook.current_cell property to its initial value.

        Args:
            exc_type: The type of the exception that was raised, if any.
            exc_value: The exception instance that was raised, if any.
            exc_tb: The traceback object encapsulating the call stack at the point where the exception occurred.
        """
        self._cell_type.notebook.current_cell = self.saved_cell

    # Attribute delegation to _cell_type

    def __getattr__(self, name: str)-> Any:
        return getattr(self._cell_type, name)
    
    def __setattr__(self, name: str, value: Any)-> None:
        if name in ("_cell_type","_notebook","notebook"):
            super().__setattr__(name, value)
        else:
            setattr(self._cell_type, name, value)

    def __delattr__(self, name: str)-> None:
        if name in ("_cell_type","_notebook","notebook"):
            super().__delattr__(name)
        else:
            delattr(self._cell_type, name)

"""Cell classes for streamlit-notebook.

This module provides the cell abstraction for streamlit-notebook,
including base :class:`Cell` class and specialized subclasses for
different content types.

Cell Types:
    - :class:`CodeCell`: Python code execution with output capture
    - :class:`MarkdownCell`: Formatted text with variable interpolation
    - :class:`HTMLCell`: Raw HTML rendering with variable interpolation

Cells support:
    - Selective reactivity (auto-rerun on changes)
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
    :class:`~streamlit_notebook.cell_ui.CellUI`: Cell UI components
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Literal
import streamlit as st
from streamlit.errors import DuplicateWidgetID, StreamlitDuplicateElementKey
from .utils import format, short_id, rerun, display
from .cell_ui import CellUI, Code
from .cell_types import CellType, PyType, MDType, HTMLType

if TYPE_CHECKING:
    from .notebook import Notebook

state = st.session_state

class Cell:

    """
    Class implementing a notebook's cell.

    This class provides the core functionality for cells, including
    type management, code storage, execution, and UI management.

    Attributes:
        notebook (Notebook): The parent Notebook object.
        key (str): A unique identifier for the cell.
        code (str): The content of the cell (code, markdown, or HTML).
        reactive (bool): If True, the cell automatically reruns when its content changes.
        fragment (bool): If True, the cell runs as a Streamlit fragment.
        type (str): The type of the cell ("code", "markdown", or "html").
        ui (CellUI): The UI object managing the cell's interface.
        results (list): A list of results from the last execution.
        exception (Exception): Any exception raised during the last execution.

    Methods:
        show(): Renders the cell's layout and content.
        run(): Executes the cell's code.
        get_exec_code(): Returns the code to be executed.
        set_output(response): Sets the output of the cell after execution.
        show_output(): Displays the execution results (if any).
        move_up(): Moves the cell up in the notebook.
        move_down(): Moves the cell down in the notebook.
        delete(): Removes the cell from the notebook.
        to_dict(): Returns a dictionary representation of the cell.
    """

    _supported_types=dict(
        code=PyType,
        markdown=MDType,
        html=HTMLType
    )

    @classmethod
    def _type_to_class(cls,type:str)-> CellType:
        if type in cls._supported_types:
            return cls._supported_types[type]
        else:
            raise ValueError(f"Unknown cell type: {type}")

    def __init__(
        self,
        notebook: Notebook,
        key: str,
        type: str = "code",  # code, markdown, html
        code: str = "",
        reactive: bool = False,
        fragment: bool = False
    ) -> None:
        self.notebook = notebook
        self.container: Any = None
        self.output: Any = None
        self.output_area: Any = None
        self.stdout_area: Any = None
        self.stderr_area: Any = None
        self.visible:bool = True
        self.stdout: Optional[str] = None
        self.stderr: Optional[str] = None
        self.results: list[Any] = []
        self.displays: list[dict[str, Any]] = []  # Display metadata for each result
        self.exception: Optional[Exception] = None
        self.ready = False
        self.has_run = False
        self.run_requested = False
        self._code = Code(value=code)
        self.last_code: Optional[str] = None
        self.key = key
        self.ui_key = short_id()
        self._reactive = reactive
        self._type: Optional[Literal['code', 'markdown', 'html']] = type
        self._fragment = fragment
        self.__type_object: Optional[CellType] = None
        self.prepare_ui()

    #Properties

    @property
    def _type_object(self) -> CellType:
        if self.__type_object is None or self.__type_object.type != self.type:
           self.__type_object = self._type_to_class(self.type)(self)
        return self.__type_object
    
    @_type_object.setter
    def _type_object(self, value: Any) -> None:
        raise AttributeError("Cannot set _type_object directly. Updating type is probably what you want to do.")

    @property
    def language(self) -> str:
        return self._type_object.language
    
    @language.setter
    def language(self, value: str) -> None:
        raise AttributeError(f"Cannot set language directly. Use type instead.")

    @property
    def index(self):
        """
        Gets the current index of the cell in the cells list.

        Returns:
            int: The index of the cell in the notebook's cell list.
        """
        return self.notebook.cells.index(self)
    
    @index.setter
    def index(self,value:int):
        self._reindex(index=value)

    @property
    def id(self) -> str:
        return f"Cell[{self.index}]({self.key})"
    
    @id.setter
    def id(self, value: str) -> None:
        raise AttributeError("Cannot set id directly.")

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        self._set_type(value)

    @property
    def code(self) -> str:
        """
        The code written in the cell.

        Returns:
            str: The current code content of the cell.
        """
        return self._code.get_value()

    @code.setter
    def code(self, value: str) -> None:
        """
        Setter for the code property.

        Args:
            value (str): The new code content to set for the cell.
        """
        current_value = self._code.get_value()
        if current_value == value:
            return
        self._code.from_backend(value)
        self.ui_key = short_id() # Force rerender of the ui
        self.reset()
        rerun()

    @property
    def has_run_once(self) -> bool:
        """
        Checks if the cell has been run at least once with the current code.

        Returns:
            bool: True if the cell has been run once with the current code, False otherwise.
        """
        return self.last_code is not None and self.last_code == self.code
    
    @has_run_once.setter
    def has_run_once(self, value: Any) -> None:
        raise AttributeError("has_run_once is a read-only property")

    @property
    def should_run(self) -> bool:
        """
        Checks if the cell should run (has run once OR run was requested).

        This property extends has_run_once to also consider deferred run requests,
        allowing reactive cells to execute on next turn when they couldn't run
        during current turn due to widget duplication concerns.

        Returns:
            bool: True if the cell has run once with current code OR a run was requested
        """
        return self.has_run_once or self.run_requested

    @should_run.setter
    def should_run(self, value: Any) -> None:
        raise AttributeError("should_run is a read-only property")

    @property
    def has_reactive_toggle(self):
        return self._type_object.has_reactive_toggle

    @has_reactive_toggle.setter
    def has_reactive_toggle(self, value: Any) -> None:
        raise AttributeError("has_reactive_toggle is a read-only property")

    @property
    def reactive(self) -> bool:
        """Whether the cell automatically reruns on changes."""
        return self._type_object.is_reactive()

    @reactive.setter
    def reactive(self, value: bool) -> None:
        """Set the reactive state of the cell."""
        if self._reactive != value:
            self._reactive = value
            # Trigger UI update if needed
            if hasattr(self, 'ui') and hasattr(self.ui, 'buttons') and 'Reactive' in self.ui.buttons:
                self.ui.buttons['Reactive'].toggled = value
                rerun()

    @property
    def has_fragment_toggle(self):
        return self._type_object.has_fragment_toggle
    
    @has_fragment_toggle.setter
    def has_fragment_toggle(self, value: Any) -> None:
        raise AttributeError("has_fragment_toggle is a read-only property")

    @property
    def fragment(self) -> bool:
        """Whether the cell runs as a Streamlit fragment."""
        return self._type_object.is_fragment()

    @fragment.setter
    def fragment(self, value: bool) -> None:
        """Set the fragment state of the cell."""
        if self._fragment != value:
            self._fragment = value
            # Trigger UI update if needed
            if hasattr(self, 'ui') and hasattr(self.ui, 'buttons') and 'Fragment' in self.ui.buttons:
                self.ui.buttons['Fragment'].toggled = value
                rerun()

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
        self.saved_cell = self.notebook.current_cell
        self.notebook.current_cell = self
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, exc_tb: Any) -> None:
        """
        Restores the notebook.current_cell property to its initial value.

        Args:
            exc_type: The type of the exception that was raised, if any.
            exc_value: The exception instance that was raised, if any.
            exc_tb: The traceback object encapsulating the call stack at the point where the exception occurred.
        """
        self.notebook.current_cell = self.saved_cell

    # UI methods

    def prepare_ui(self):
        """
        Initializes the CellUI object and sets up the cell's user interface components.
        """
        self.ui=CellUI(code=self._code,lang=self.language,key=f"cell_ui_{self.ui_key}",response_mode="blur")
        self.ui.submit_callback=self._submit_callback
        self.ui.buttons["Reactive"].callback=self._toggle_reactive
        self.ui.buttons["Reactive"].toggled=self.reactive
        self.ui.buttons["Fragment"].callback=self._toggle_fragment
        self.ui.buttons["Fragment"].toggled=self.fragment
        self.ui.buttons["Up"].callback=self.move_up
        self.ui.buttons["Down"].callback=self.move_down
        self.ui.buttons["Close"].callback=self.delete
        self.ui.buttons["Run"].callback=self._run_callback
        self.ui.buttons["InsertAbove"].callback=self.insert_above
        self.ui.buttons["InsertBelow"].callback=self.insert_below
        self.ui.buttons["TypeCode"].callback=lambda: self._set_type("code")
        self.ui.buttons["TypeMarkdown"].callback=lambda: self._set_type("markdown")
        self.ui.buttons["TypeHTML"].callback=lambda: self._set_type("html")
        
    def update_ui(self):
        """
        Updates the cell's UI components based on the current cell state.
        """
        self.ui.lang=self.language
        self.ui.key=f"cell_ui_{self.ui_key}"
        self.ui.buttons['Fragment'].visible=self.has_fragment_toggle
        self.ui.buttons['Reactive'].visible=self.has_reactive_toggle

        self.ui.info_bar.set_info(dict(name=f"{self.id}:",style=dict(fontSize="14px",width="100%")))

        # Update type buttons to highlight current type with bold font
        for type_name, button_name in [("code", "TypeCode"), ("markdown", "TypeMarkdown"), ("html", "TypeHTML")]:
            if self.type == type_name:
                self.ui.buttons[button_name].style.update(fontWeight = 'bold',opacity='1')
            else:
                self.ui.buttons[button_name].style.update(fontWeight = 'normal',opacity='0.5')

    def initialize_output_area(self):
        """
        Prepares or clears the various containers used to display cell outputs.
        """
        self.output=self.output_area.container()
        with self.output:
            self.exception_area=st.empty()
            self.stdout_area=st.empty()
            self.stderr_area=st.empty()
            self.display_area=st.container()
        
    def prepare_skeleton(self):
        """
        Prepares the various containers used to display the cell UI and its outputs.
        """
        self.container=st.container()
        self.output_area=st.empty()
        self.initialize_output_area()
        self.ready=True # flag used by self.run() and shell hooks to signal that the cell has prepared the adequate containers to receive outputs

    def show(self):
        """
        Renders the cell's layout.

        This method is responsible for displaying the cell's UI components
        and managing its visibility based on notebook settings.
        """
        self.prepare_skeleton()

        if not self.notebook.app_view and self.visible:
            with self.container.container():
                self.update_ui()
                self.ui.show()

        # Rerun only if the cell has been run at least once with the current code OR a run was requested
        # This prevents premature execution when toggling "reactive" on a cell that hasn't run yet
        if self.reactive and self.should_run:
            self.run()

        self.show_outputs()

    def show_displays(self):
        if self.displays:
            with self.display_area:
                # Display each result using info from displays
                for display_info in self.displays:
                    result = display_info.get("result")
                    backend = display_info.get("backend")
                    # Extract all kwargs except 'result' and 'backend'
                    display_kwargs = {k: v for k, v in display_info.items()
                                     if k not in ("result", "backend")}
                    display(result, backend=backend, **display_kwargs)

    def show_outputs(self):
        """
        Displays the cell's current execution outputs.
        """
        self.initialize_output_area()
        if self.exception:
            with self.exception_area:
                formatted_traceback=f"**{type(self.exception).__name__}**: {str(self.exception)}\n```\n{self.exception.enriched_traceback_string}\n```"
                st.error(formatted_traceback)
        if self.stdout and self.notebook.show_stdout:
            with self.stdout_area:
                st.code(self.stdout,language="text")
        if self.stderr and self.notebook.show_stderr:
            with self.stderr_area:
                st.code(self.stderr,language="text")


        if not self.has_run:
            # We don't show displays if the cell has already run this turn
            # because display shows them already when the cell runs 
            self.show_displays()

    # Excution workflow 

    def run(self):
        """
        Runs the cell's code.

        This method executes the cell's content, captures the output,
        and updates the cell's state accordingly.

        If the cell has already run this turn, it defers execution to next turn
        to avoid widget duplication errors.
        """
        # Check if already ran this turn - defer to next turn
        if self.has_run:
            self.run_requested = True
            return

        if self.code:
            self.last_code=self.code
            self.results=[]
            self.displays=[]
            self.has_run=True
            self.run_requested = False  # Clear request flag once we actually run
            if self.ready:
                # The cell skeleton is on screen and can receive outputs
                self.initialize_output_area()
                with self.display_area:
                    self._exec()
            else:
                # The cell skeleton isn't on screen yet
                # The code runs anyway, but the outputs will be shown after a refresh
                self._exec()
                rerun()   

    def _exec(self):
        """
        Execute the cell's code in the shell and handle the response.

        This method delegates the execution workflow to the underlying type object.
        """
        return self._type_object.exec()

    def _get_exec_code(self):
        """
        Get the code to execute.

        Returns:
            str: The code to be executed.

        Note:
            This method delegates to the type object to provide
            type-specific code preparation.
        """
        return self._type_object.get_exec_code()  

    def _set_output(self,response):
        """
        Assigns relevant fields of the shell response to the cell.

        Args:
            response (ShellResponse): The response object from code execution.

        This method updates the cell's stdout, stderr, and exception attributes.
        """
        self.stdout=response.stdout
        self.stderr=response.stderr
        self.exception=response.exception

    # Private Callbacks 
        
    def _submit_callback(self):
        """
        Callback used to deal with the "submit" event from the UI.

        Runs the cell only if notebook.run_on_submit is true.
        """
        if self.notebook.run_on_submit:
            self.has_run=False
            self.run()
            self.notebook.notify(f"Executed `{self.id}`", icon="▶️")

    def _run_callback(self):
        """
        Callback used to deal with the "run" event from the ui.

        Resets run_state to None and runs the cell.
        """
        self.has_run=False
        self.run()
        self.notebook.notify(f"Executed `{self.id}`", icon="▶️")

    def _toggle_reactive(self):
        """Toggles the 'Auto-Rerun' feature for the cell (internal)."""
        self._reactive = self.ui.buttons["Reactive"].toggled

    def _toggle_fragment(self):
        """Toggles the 'Fragment' feature for the cell (internal)."""
        self._fragment = self.ui.buttons["Fragment"].toggled

    def _set_type(self, new_type):
        """
        Changes the type of the cell (code, markdown, or html).

        Args:
            new_type (str): The new type for the cell ("code", "markdown", or "html")
        """
        if new_type == self.type:
            return  # Already this type, nothing to do
        
        if new_type in Cell._supported_types:
            self._type = new_type
        else:
            raise ValueError(f"Invalid cell type: {new_type}. Must be 'code', 'markdown', or 'html'")
        rerun()

    def _reindex(self,index:int):
        """
        Moves the cell to a new index.

        Args:
            index (int): The new index (position) for the cell in the notebook.
        """
        if 0<=index<len(self.notebook.cells) and not index==self.index:
            # Remove from current position
            self.notebook.cells.remove(self)
            # Insert at new position
            self.notebook.cells.insert(index, self)
            rerun()

    # Public methods

    def move_up(self):
        """
        Moves the cell up in the notebook.

        This method changes the cell's position, moving it one place earlier in the execution order.
        """
        self._reindex(self.index-1)
        
    def move_down(self):
        """
        Moves the cell down in the notebook.

        This method changes the cell's position, moving it one place later in the execution order.
        """
        self._reindex(self.index+1)

    def insert_above(self, type: str = "code", code: str = "", reactive: bool = False, fragment: bool = False):
        """
        Inserts a new cell above this cell in the notebook.

        Args:
            type (str): The type of cell to create ("code", "markdown", or "html"). Defaults to "code".
            code (str): Initial code or content for the cell. Defaults to "".
            reactive (bool): Whether the cell should automatically re-run when UI refreshes. Defaults to False.
            fragment (bool): Whether the cell should run as a Streamlit fragment. Defaults to False.
        """
        new_key = self.notebook._gen_cell_key()
        cell = new_cell(self.notebook, new_key, type=type, code=code, reactive=reactive, fragment=fragment)
        # Insert at current position (pushing this cell down)
        self.notebook.cells.insert(self.index, cell)
        rerun()
        return cell

    def insert_below(self, type: str = "code", code: str = "", reactive: bool = False, fragment: bool = False):
        """
        Inserts a new cell below this cell in the notebook.

        Args:
            type (str): The type of cell to create ("code", "markdown", or "html"). Defaults to "code".
            code (str): Initial code or content for the cell. Defaults to "".
            reactive (bool): Whether the cell should automatically re-run when UI refreshes. Defaults to False.
            fragment (bool): Whether the cell should run as a Streamlit fragment. Defaults to False.
        """
        new_key = self.notebook._gen_cell_key()
        cell = new_cell(self.notebook, new_key, type=type, code=code, reactive=reactive, fragment=fragment)
        # Insert after current position
        self.notebook.cells.insert(self.index + 1, cell)
        rerun()
        return cell

    def delete(self):
        """
        Deletes the cell from the notebook.
        """
        if self in self.notebook.cells:
            self.notebook.cells.remove(self)
            rerun()

    def reset(self):
        """
        Resets the cell's state, clearing outputs and execution history.
        This method is called when we need to clear all previous results and run states like we start with a fresh cell.
        """
        self.initialize_output_area()
        self.has_run=False
        self.last_code=None
        self.results=[]
        self.displays=[]
        self.stdout=None
        self.stderr=None
        self.exception=None

    # Serialization methods

    def to_dict(self, minimal: bool = True):
        """
        Returns a dictionary representation of the cell.

        Args:
            minimal: If True (default), returns only the minimal data needed
                to recreate the cell (for saving notebooks). If False, includes
                all execution outputs, metadata, and runtime state useful for
                AI agents or state inspection.

        Returns:
            dict: A dictionary containing the cell's attributes. When
                ``minimal=False``, includes complete execution state, outputs,
                and runtime metadata.

        Examples:
            Minimal serialization (for saving notebooks)::

                cell_data = cell.to_dict()  # minimal=True by default
                # {'key': 'abc123', 'type': 'code', 'code': '...',
                #  'reactive': False, 'fragment': False}

            Full serialization (for AI agent context)::

                cell_state = cell.to_dict(minimal=False)
                # Includes: id, index, language, has_run_once, visible, stdout,
                # stderr, results (as repr strings), exception info

        Note:
            Results are converted to their string representations (via ``repr()``)
            to ensure JSON serializability. Exception tracebacks are included
            as formatted strings when ``minimal=False``.
        """
        # Basic cell definition (always included)
        d = dict(
            key=self.key,
            type=self.type,
            code=self.code,
            reactive=self.reactive,
            fragment=self.fragment
        )

        # Add execution outputs and metadata if full state requested
        if not minimal:
            d.update(
                id=self.id,
                index=self.index,
                language=self.language,
                has_run_once=self.has_run_once,
                visible=self.visible,
                stdout=self.stdout,
                stderr=self.stderr,
                # Convert results to string representations for serializability
                results=[repr(r) for r in self.results] if self.results else [],
                # Include exception details if present
                exception=dict(
                    type=type(self.exception).__name__,
                    message=str(self.exception),
                    traceback=getattr(self.exception, 'enriched_traceback_string', str(self.exception))
                ) if self.exception else None
            )

        return d
    
    @classmethod
    def from_dict(cls, d):
        """
        Creates a cell from a dictionary representation.

        Args:
           d (dict): A dictionary containing the cell's attributes.

        Returns:
           Cell: A new Cell object created from the dictionary.
        """
        # Get the current notebook instance from state
        notebook: Notebook = st.session_state.get("notebook", None)
        if notebook is None:
            raise ValueError("No notebook instance found in session state.")
        
        # Create a new cell with the dictionary values
        cell = cls(
            notebook, 
            d.get("key",notebook._gen_cell_key()), 
            d.get("type", "code"),
            d.get("code", ""),
            d.get("reactive", False),
            d.get("fragment", False)
        )
        return cell

def new_cell(notebook,key,type="code",code="",reactive=False,fragment=False):
    """
    Returns a new cell, given a notebook object, a key, and optional kwargs.

    This function is used in the notebook.new_cell method to create cells of different types.

    Args:
        notebook (Notebook): The parent Notebook object.
        key: Unique identifier for the cell.
        type (str): The type of cell to create ("code", "markdown", or "html").
        code (str): Initial code or content for the cell.
        reactive (bool): Whether the cell should automatically re-run when UI refreshes.
        fragment (bool): Whether the cell should run as a Streamlit fragment.

    Returns:
        Cell: A new Cell object of the specified type.

    Raises:
        NotImplementedError: If an unsupported cell type is specified.
    """
    if not type in Cell._supported_types:
        raise NotImplementedError(f"Cell type {type} not implemented")
    return Cell(notebook,key,type=type,code=code,reactive=reactive,fragment=fragment)
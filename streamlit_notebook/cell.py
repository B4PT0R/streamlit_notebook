import streamlit as st
from streamlit.errors import DuplicateWidgetID
from .utils import format, short_id, rerun
from .cell_ui import CellUI, Code

state=st.session_state

def display(obj):
    """
    Display an object using st.write as a default backend.

    This function attempts to display the object using Streamlit's st.write function.
    If that fails, it falls back to displaying the object's string representation.

    Args:
        obj: The object to be displayed.

    This function is used internally to handle the display of various types of objects
    within the notebook cells.
    """
    if obj is not None:
        try: 
            st.write(obj)
        except:
            st.text(repr(obj))

class Cell:

    """
    The base class for all types of cells in the notebook.

    This class provides the core functionality for cells, including
    code storage, execution, and UI management.

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
    def __init__(self,notebook,key,code="",reactive=False,fragment=False):
        self.notebook=notebook
        self.container=None
        self.output=None
        self.output_area=None
        self.stdout_area=None
        self.stderr_area=None
        self.visible=True
        self.stdout=None
        self.stderr=None
        self.results=[]
        self.exception=None
        self.ready=False
        self.has_run=False
        self.has_fragment_toggle=True
        self._code=Code(value=code)
        self.last_code=None
        self.key=key
        self.reactive=reactive
        self.language=None
        self.type=None
        self.fragment=fragment
        self.prepare_ui()

    @property
    def code(self):
        """
        The code written in the cell.

        Returns:
            str: The current code content of the cell.
        """
        return self._code.get_value()
    
    @code.setter
    def code(self,value):
        """
        Setter for the code property.

        Args:
            value (str): The new code content to set for the cell.
        """
        self._code.from_backend(value)
        rerun()

    @property
    def has_run_once(self):
        """
        Checks if the cell has been run at least once with the current code.

        Returns:
            bool: True if the cell has been run once with the current code, False otherwise.
        """
        return self.last_code is not None and self.last_code==self.code

    def __enter__(self):
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
        self.saved_cell=self.notebook.current_cell
        self.notebook.current_cell=self
        return self
    
    def __exit__(self,exc_type,exc_value,exc_tb):
        """
        Restores the notebook.current_cell property to its initial value.

        Args:
            exc_type: The type of the exception that was raised, if any.
            exc_value: The exception instance that was raised, if any.
            exc_tb: The traceback object encapsulating the call stack at the point where the exception occurred.
        """
        self.notebook.current_cell=self.saved_cell


    def prepare_ui(self):
        """
        Initializes the CellUI object and sets up the cell's user interface components.
        """
        self.ui=CellUI(code=self._code,lang=self.language,key=f"cell_ui_{short_id()}",response_mode="blur")
        self.ui.submit_callback=self.submit_callback
        self.ui.buttons["Reactive"].callback=self.toggle_reactive
        self.ui.buttons["Reactive"].toggled=self.reactive
        self.ui.buttons["Fragment"].callback=self.toggle_fragment
        self.ui.buttons["Fragment"].toggled=self.fragment
        self.ui.buttons["Up"].callback=self.move_up
        self.ui.buttons["Down"].callback=self.move_down
        self.ui.buttons["Close"].callback=self.delete
        self.ui.buttons["Run"].callback=self.run_callback
        

    def update_ui(self):
        """
        Updates the cell's UI components based on the current cell state.
        """
        self.ui.lang=self.language
        self.ui.buttons['Fragment'].visible=self.has_fragment_toggle
        #self.ui.buttons['Has_run'].visible=self.has_run_once
        self.ui.info_bar.set_info(dict(name=f"Cell[{self.key}]: {self.type}",style=dict(fontSize="14px",width="100%")))

    def initialize_output_area(self):
        """
        Prepares or clears the various containers used to display cell outputs.
        """
        self.output=self.output_area.container()
        with self.output:
            self.stdout_area=st.empty()
            self.stderr_area=st.empty()
        
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

        if not self.notebook.app_mode and self.visible:
            with self.container.container():
                self.update_ui()
                self.ui.show()

        # Rerun only if the cell has been run at least once with the current code
        # This prevents premature execution when toggling auto-rerun on a cell that hasn't run yet
        if self.reactive and self.has_run_once:
            self.run()

        self.show_output()
        
    def submit_callback(self):
        """
        Callback used to deal with the "submit" event from the UI.

        Runs the cell only if notebook.run_on_submit is true.
        """
        if self.notebook.run_on_submit:
            self.has_run=False
            self.run()

    def run_callback(self):
        """
        Callback used to deal with the "run" event from the ui.

        Resets run_state to None and runs the cell.
        """
        self.has_run=False
        self.run()

    def run(self):
        """
        Runs the cell's code.

        This method executes the cell's content, captures the output,
        and updates the cell's state accordingly.
        """
        if not self.has_run and self.code:
            self.last_code=self.code
            self.results=[]
            self.has_run=True
            if self.ready:
                # The cell skeleton is on screen and can receive outputs
                self.initialize_output_area()
                with self.output:
                    self.exec()
            else:
                # The cell skeleton isn't on screen yet
                # The code runs anyway, but the outputs will be shown after a refresh
                self.exec()
                rerun()
            

    def get_exec_code(self):
        """
        Get the code to execute.

        Returns:
            str: The code to be executed.

        Note:
            This method is overridden in subclasses to provide
            type-specific code preparation.
        """
        return self.code

    def exec(self):
        """
        Executes the code returned by self.get_exec_code()
        """
        with self:
            response=self.notebook.shell.run(self.get_exec_code(),filename=f"<Cell[{self.key}]>")
        self.set_output(response)       

    def set_output(self,response):
        """
        Assigns relevant fields of the shell response to the cell.

        Args:
            response (ShellResponse): The response object from code execution.

        This method updates the cell's stdout, stderr, and exception attributes.
        """
        self.stdout=response.stdout
        self.stderr=response.stderr
        self.exception=response.exception

    def show_output(self):
        """
        Displays the previous execution results.

        This method is called when a cell hasn't run in the current Streamlit run,
        displaying previous results without re-executing the code.
        """
        self.initialize_output_area()
        if self.stdout:
            with self.stdout_area:
                st.code(self.stdout,language="text")
        if self.stderr and self.notebook.show_stderr:
            with self.stderr_area:     
                st.code(self.stderr,language="text")
        if self.results:
            with self.output:
                for result in self.results:
                    display(result)
        if self.exception:
            with self.output:
                formatted_traceback=f"**{type(self.exception).__name__}**: {str(self.exception)}\n```\n{self.exception.enriched_traceback_string}\n```"
                st.error(formatted_traceback)

    @property
    def rank(self):
        """
        Gets the current rank of the cell in the cells dict.

        Returns:
            int: The index of the cell in the notebook's cell list.
        """
        return list(self.notebook.cells.keys()).index(self.key)
    
    def rerank(self,rank):
        """
        Moves the cell to a new rank.

        Args:
            rank (int): The new rank (position) for the cell in the notebook.
        """
        if 0<=rank<len(self.notebook.cells) and not rank==self.rank:
            keys=list(self.notebook.cells.keys())
            del keys[self.rank]
            keys.insert(rank,self.key)
            self.notebook.cells={k:self.notebook.cells[k] for k in keys}
            rerun()

    def move_up(self):
        """
        Moves the cell up in the notebook.

        This method changes the cell's position, moving it one place earlier in the execution order.
        """
        self.rerank(self.rank-1)
        

    def move_down(self):
        """
        Moves the cell down in the notebook.

        This method changes the cell's position, moving it one place later in the execution order.
        """
        self.rerank(self.rank+1)


    def toggle_reactive(self):
        """
        Toggles the 'Auto-Rerun' feature for the cell.
        """
        self.reactive=self.ui.buttons["Reactive"].toggled

    def toggle_fragment(self):
        """
        Toggles the 'Run as fragment' feature for the cell.
        """
        self.fragment=self.ui.buttons["Fragment"].toggled

    def delete(self):
        """
        Deletes the cell from the notebook.
        """
        if self.key in self.notebook.cells:
            del self.notebook.cells[self.key]
            rerun()

    def reset(self):
        self.initialize_output_area()
        self.has_run=False
        self.last_code=None
        self.results=[]
        self.stdout=None
        self.stderr=None
        self.exception=None
    
    def to_dict(self):
        """
        Returns a minimal dict representation of the cell.

        Returns:
            dict: A dictionary containing the essential attributes of the cell.

        This method is used for serialization of the cell, containing only
        what is necessary to recreate it.
        """
        d=dict(
            key=self.key,
            type=self.type,
            code=self.code,
            reactive=self.reactive,
            fragment=self.fragment
        )
        return d
            
class CodeCell(Cell):

    """
    A subclass of Cell implementing a code cell.

    This class represents a cell containing Python code that can be executed
    within the notebook environment.

    Attributes:
        language (str): Always set to "python" for code cells.
        type (str): Always set to "code" for code cells.

    Methods:
        exec(): Executes the cell code, either as a fragment or normally.
        exec_code_as_fragment(): Executes the cell as a Streamlit fragment.
        exec_code(): Executes the cell normally.
    """

    def __init__(self,notebook,key,code="",reactive=True,fragment=False):
        super().__init__(notebook,key,code=code,reactive=reactive,fragment=fragment)
        self.has_fragment_toggle=True
        self.language="python"
        self.type="code"

    def exec(self):
        """
        Executes the cell code.

        This method chooses between normal execution and fragment execution
        based on the cell's fragment attribute.
        """
        if self.fragment:
            self.exec_code_as_fragment()
        else:
            self.exec_code()


    @st.fragment
    def exec_code_as_fragment(self):
        """
        Executes the cell as a Streamlit fragment.

        This method is decorated with @st.fragment and executes
        the cell's code within a Streamlit fragment context.
        """
        with self:
            response=self.notebook.shell.run(self.get_exec_code(),filename=f"<Cell[{self.key}]>")
        self.set_output(response)

    def exec_code(self):
        """
        Executes the cell normally.

        This method runs the cell's code in the normal execution context.
        """
        with self:
            response=self.notebook.shell.run(self.get_exec_code(),filename=f"<Cell[{self.key}]>")
        self.set_output(response)

class MarkdownCell(Cell):

    """
    A subclass of Cell implementing a Markdown cell.

    This class represents a cell containing Markdown content that is
    rendered as formatted text in the notebook.

    Attributes:
        language (str): Always set to "markdown" for Markdown cells.
        type (str): Always set to "markdown" for Markdown cells.

    Methods:
        get_exec_code(): Formats the Markdown code and converts it to a st.markdown call.
    """

    def __init__(self,notebook,key,code="",reactive=True,fragment=False):
        super().__init__(notebook,key,code=code,reactive=reactive,fragment=False)
        self.has_fragment_toggle=False
        self.language="markdown"
        self.type="markdown"

    def get_exec_code(self):
        """
        Formats the Markdown code and converts it to a st.markdown call.

        Returns:
            str: A string containing a st.markdown() call with the formatted Markdown content.

        This method processes the cell's content, formats any variables,
        and wraps it in a Streamlit markdown function call.
        """
        formatted_code=format(self.code,**self.notebook.shell.namespace).replace("'''","\'\'\'")
        code=f"st.markdown(r'''{formatted_code}''');"
        return code

class HTMLCell(Cell):

    """
    A subclass of Cell implementing an HTML cell.

    This class represents a cell containing HTML content that is
    rendered directly in the notebook.

    Attributes:
        language (str): Always set to "html" for HTML cells.
        type (str): Always set to "html" for HTML cells.

    Methods:
        get_exec_code(): Formats the HTML code and converts it to a st.html call.
    """

    def __init__(self,notebook,key,code="",reactive=True,fragment=False):
        super().__init__(notebook,key,code=code,reactive=reactive,fragment=False)
        self.has_fragment_toggle=False
        self.language="html"
        self.type="html"

    def get_exec_code(self):
        """
        Formats the HTML code and converts it to a st.html call.

        Returns:
            str: A string containing a st.html() call with the formatted HTML content.

        This method processes the cell's content, formats any variables,
        and wraps it in a Streamlit HTML function call.
        """
        formatted_code=format(self.code,**self.notebook.shell.namespace).replace("'''","\'\'\'")
        code=f"st.html(r'''{formatted_code}''');"
        return code

def type_to_class(cell_type):
    """
    Routes a cell type to the appropriate class.

    This function maps cell type strings to their corresponding Cell subclasses.

    Args:
        cell_type (str): The type of cell ("code", "markdown", or "html").

    Returns:
        type: The Cell subclass corresponding to the given type.

    Raises:
        NotImplementedError: If an unsupported cell type is specified.
    """
    if cell_type=="code":
        return CodeCell
    elif cell_type=="markdown":
        return MarkdownCell
    elif cell_type=="html":
        return HTMLCell
    else:
        raise NotImplementedError(f"Unsupported cell type: {cell_type}")

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
    return type_to_class(type)(notebook,key,code=code,reactive=reactive,fragment=fragment)
import streamlit as st
from streamlit.errors import DuplicateWidgetID
from .utils import format, short_id, rerun
from .cell_ui import CellUI, Code

state=st.session_state

def display(obj):
    """
    Display an object using st.write as a default backend
    falls back to displaying the object's repr() in case st.write fails
    """
    if obj is not None:
        try: 
            st.write(obj)
        except:
            st.text(repr(obj))

class Cell:

    "Implements the main notebook Cell class from which other cell types inherit"

    def __init__(self,notebook,key,code="",auto_rerun=False,fragment=False):
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
        self.has_fragment_toggle=True
        self._code=Code(value=code)
        self.last_code=None
        self.key=key
        self.auto_rerun=auto_rerun
        self.has_run=False
        self.language=None
        self.type=None
        self.fragment=fragment
        self.needs_to_run=False
        self.prepare_ui()

    @property
    def code(self):
        """
        This property returns the code written in the cell
        """
        return self._code.get_value()
    
    @code.setter
    def code(self,value):
        """
        Setter of the code property
        """
        self._code.from_backend(value)
        rerun()

    @property
    def has_run_once(self):
        return self.last_code is not None and self.last_code==self.code

    def __enter__(self):
        """
        Allows to use the cell as a context manager.
        Enables to run code in the shell and direct its outputs to the cell by switching the notebook.current_cell porperty
        example:
        with cell:
            notebook.shell.run(code) # all shell outputs will be directed to the cell
        """
        self.saved_cell=self.notebook.current_cell
        self.notebook.current_cell=self
        return self
    
    def __exit__(self,exc_type,exc_value,exc_tb):
        """
        Restore the notebook.current_cell property to initial value
        """
        self.notebook.current_cell=self.saved_cell


    def prepare_ui(self):
        """
        Initializes the CellUI object
        """
        self.ui=CellUI(code=self._code,lang=self.language,key=f"cell_ui_{short_id()}",response_mode="blur")
        self.ui.submit_callback=self.submit_callback
        self.ui.buttons["Auto_rerun"].callback=self.toggle_auto_rerun
        self.ui.buttons["Auto_rerun"].toggled=self.auto_rerun
        self.ui.buttons["Fragment"].callback=self.toggle_fragment
        self.ui.buttons["Fragment"].toggled=self.fragment
        self.ui.buttons["Up"].callback=self.move_up
        self.ui.buttons["Down"].callback=self.move_down
        self.ui.buttons["Close"].callback=self.delete
        self.ui.buttons["Run"].callback=self.run_callback
        

    def update_ui(self):
        """
        Updates the cell's ui
        """
        self.ui.lang=self.language
        self.ui.buttons['Fragment'].visible=self.has_fragment_toggle
        #self.ui.buttons['Has_run'].visible=self.has_run_once
        self.ui.info_bar.set_info(dict(name=f"Cell[{self.key}]: {self.type}",style=dict(fontSize="14px",width="100%")))

    def prepare_output_area(self):
        """
        Prepares the various containers used to display cell outputs
        """
        self.output=self.output_area.container()
        with self.output:
            self.stdout_area=st.empty()
            self.stderr_area=st.empty()
        
    def prepare_skeleton(self):
        """
        Prepares the various containers used to display the cell ui and its outputs
        """
        self.container=st.container()
        self.output_area=st.empty()
        self.prepare_output_area()
        self.ready=True # flag used by self.run() and shell hooks to signal that the cell has prepared the adequate containers to receive outputs

    def show(self):
        """
        Renders the cell's layout
        """

        self.prepare_skeleton()

        self.has_run=False

        if not self.notebook.hide_code_cells and self.visible:
            with self.container.container():
                self.update_ui()
                self.ui.show()

        if self.auto_rerun or self.needs_to_run:
            self.run()
                
        if not self.has_run:
            self.show_previous_output()
        
    def submit_callback(self):
        """
        Callback used to deal with the "submit" event from the ui
        run it only if notebook.run_on_submit is true
        """
        if self.notebook.run_on_submit:
            self.has_run=False
            self.run()

    def run_callback(self):
        """
        Callback used to deal with the "run" event from the ui
        submits the code and run it
        """
        self.has_run=False
        self.run()

    def run(self):
        """
        Runs the cell's code
        """
        if not self.has_run and self.code:
            self.needs_to_run=False
            self.last_code=self.code
            self.results=[]
            if self.ready:
                # The cell skeleton is on screen and can receive outputs
                self.prepare_output_area()
                with self.output:
                    self.exec()
            else:
                # The cell skeleton isn't on screen yet
                # The code runs anyway, but the outputs will be shown after a refresh
                self.exec()
                rerun()
            self.has_run=True

    def get_exec_code(self):
        """
        Get the code to execute. Defaults to the submitted code.
        Overriden by Markdown and HTML cells.
        """
        return self.code

    def exec(self):
        """
        Executes the code returned by self.get_exec_code()
        """
        with self:
            response=self.notebook.shell.run(self.get_exec_code())
        self.set_output(response)       

    def set_output(self,response):
        """
        Assigns relevant fields of the shell response to the cell
        """
        self.stdout=response.stdout
        self.stderr=response.stderr
        self.exception=response.exception

    def show_previous_output(self):
        """
        Called whenever a cell hasn't run in the current streamlit run
        In which case it only displays previous results without reruning the code
        """
        if self.stdout:
            with self.stdout_area:
                st.code(self.stdout,language="text")
        #if self.stderr:
        #    with self.stderr_area:     
        #        st.code(self.stderr,language="text")
        if self.results:
            with self.output:
                for result in self.results:
                    display(result)
        if self.exception:
            with self.output:
                st.exception(self.exception)

    @property
    def rank(self):
        """
        Gets the current rank of the cell in the cells dict
        """
        return list(self.notebook.cells.keys()).index(self.key)
    
    def rerank(self,rank):
        """
        Moves the cell to a new rank
        """
        if 0<=rank<len(self.notebook.cells) and not rank==self.rank:
            keys=list(self.notebook.cells.keys())
            del keys[self.rank]
            keys.insert(rank,self.key)
            self.notebook.cells={k:self.notebook.cells[k] for k in keys}
            rerun()

    def move_up(self):
        """
        Moves the cell up
        """
        self.rerank(self.rank-1)
        

    def move_down(self):
        """
        Moves the cell down
        """
        self.rerank(self.rank+1)


    def toggle_auto_rerun(self):
        """
        Toggle 'Auto-Rerun'
        """
        self.auto_rerun=self.ui.buttons["Auto_rerun"].toggled

    def toggle_fragment(self):
        """
        Toggle 'Run as fragment' 
        """
        self.fragment=self.ui.buttons["Fragment"].toggled

    def delete(self):
        """
        Deletes the cell
        """
        if self.key in self.notebook.cells:
            del self.notebook.cells[self.key]
            rerun()
    
    def to_dict(self):
        """
        Returns a minimal dict representation of the cell
        Only what is necessary to recreate it 
        """
        d=dict(
            key=self.key,
            type=self.type,
            code=self.code,
            auto_rerun=self.auto_rerun,
            fragment=self.fragment
        )
        return d
            
class CodeCell(Cell):

    """
    Subclass of Cell implementing the Code cell
    """

    def __init__(self,notebook,key,code="",auto_rerun=True,fragment=False):
        super().__init__(notebook,key,code=code,auto_rerun=auto_rerun,fragment=fragment)
        self.has_fragment_toggle=True
        self.language="python"
        self.type="code"

    def exec(self):
        """
        Executes the cell code, either as a fragment or normally depending on its setting
        """
        if self.fragment:
            self.exec_code_as_fragment()
        else:
            self.exec_code()


    @st.experimental_fragment
    def exec_code_as_fragment(self):
        """
        Executes the cell as a fragment 
        """
        with self:
            response=self.notebook.shell.run(self.get_exec_code())
        self.set_output(response)

    def exec_code(self):
        """
        Executes the cell normally
        """
        with self:
            response=self.notebook.shell.run(self.get_exec_code())
        self.set_output(response)

class MarkdownCell(Cell):

    """
    Subclass of Cell implementing the Markdown cell 
    """

    def __init__(self,notebook,key,code="",auto_rerun=True,fragment=False):
        super().__init__(notebook,key,code=code,auto_rerun=auto_rerun,fragment=False)
        self.has_fragment_toggle=False
        self.language="markdown"
        self.type="markdown"

    def get_exec_code(self):
        """
        Formats the markdown code and converts it to a st.markdown call
        """
        formatted_code=format(self.code,**state,**globals()).replace("'''","\'\'\'")
        code=f"st.markdown(r'''{formatted_code}''');"
        return code

class HTMLCell(Cell):

    """
    Subclass of Cell implementing the HTML cell
    """

    def __init__(self,notebook,key,code="",auto_rerun=True,fragment=False):
        super().__init__(notebook,key,code=code,auto_rerun=auto_rerun,fragment=False)
        self.has_fragment_toggle=False
        self.language="html"
        self.type="html"

    def get_exec_code(self):
        """
        Formats the html code and converts it to a st.html call
        """
        formatted_code=format(self.code,**state,**globals()).replace("'''","\'\'\'")
        code=f"st.html(r'''{formatted_code}''');"
        return code

def type_to_class(cell_type):
    """
    Routes a cell type to the adequate class
    """
    if cell_type=="code":
        return CodeCell
    elif cell_type=="markdown":
        return MarkdownCell
    elif cell_type=="html":
        return HTMLCell
    else:
        raise NotImplementedError(f"Unsupported cell type: {cell_type}")

def new_cell(notebook,key,type="code",code="",auto_rerun=False,fragment=False):
    """
    Returns a new cell, given a notebook object, a key, and optional kwargs
    Used in the notebook.new_cell function
    """
    return type_to_class(type)(notebook,key,code=code,auto_rerun=auto_rerun,fragment=fragment)
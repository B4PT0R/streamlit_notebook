import streamlit as st
from streamlit.errors import DuplicateWidgetID
from .utils import format
from .cell_ui import CellUI

state=st.session_state

def display(obj):
    if obj is not None:
        try: 
            st.write(obj)
        except:
            st.text(repr(obj))

class Cell:

    "Implements the main notebook cell from which other cell types inherit"

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
        self.has_fragment_toggle=True
        self.code=code
        self.submitted_code=""
        self.key=key
        self.auto_rerun=auto_rerun
        self.has_run=False
        self.language=None
        self.type=None
        self.fragment=fragment
        self.needs_to_run=False
        self.prepare_ui()

    def __enter__(self):
        self.saved_cell=self.notebook.current_cell
        self.notebook.current_cell=self
        return self
    
    def __exit__(self,exc_type,exc_value,exc_tb):
        self.notebook.current_cell=self.saved_cell


    def prepare_ui(self):
        self.ui=CellUI(code=self.code,lang=self.language,key=f"cell_ui_{self.key}",response_mode="blur")
        self.ui.submit_callback=self.submit_callback
        self.ui.buttons["Auto_rerun"]._callback=self.toggle_auto_rerun
        self.ui.buttons["Auto_rerun"].toggled=self.auto_rerun
        self.ui.buttons["Fragment"]._callback=self.toggle_fragment
        self.ui.buttons["Fragment"].toggled=self.fragment
        self.ui.buttons["Up"]._callback=self.move_up
        self.ui.buttons["Down"]._callback=self.move_down
        self.ui.buttons["Close"]._callback=self.delete
        self.ui.buttons["Run"]._callback=self.run_button_callback
        

    def update_ui(self):
        self.ui.lang=self.language
        self.ui.buttons['Fragment'].visible=self.has_fragment_toggle
        self.ui.info_bar.set_info(dict(name=f"Cell[{self.key}]: {self.type}",style=dict(fontSize="12px",width="100%")))

    def prepare_output_area(self):
        self.output=self.output_area.container()
        with self.output:
            self.stdout_area=st.empty()
            self.stderr_area=st.empty()
        
    def prepare_skeleton(self):
        self.container=st.container()
        self.output_area=st.empty()
        self.prepare_output_area()

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

    def submit(self):
        if self.ui.code:
            self.code=self.ui.code
        self.submitted_code=self.code
        
    def submit_callback(self):
        """
        Submits the content of the cell
        """
        self.submit()
        if self.notebook.run_on_submit:
            self.has_run=False
            self.run()

    def run_button_callback(self):
        self.has_run=False
        self.submit()
        self.run()

    def run(self):
        """
        Runs the cell's code
        """
        self.needs_to_run=False
        if not self.has_run and self.submitted_code:
            self.results=[]
            try:
                self.prepare_output_area()
                with self.output:
                    self.exec()
                self.has_run=True
            except:
                self.needs_to_run=True

    def get_exec_code(self):
        """
        Get the code to execute. Defaults to the submitted code.
        Overriden by Markdown and HTML cells.
        """
        return self.submitted_code

    def exec(self):
        """
        Executes the code returned by self.get_exec_code()
        """
        with self:
            response=self.notebook.shell.run(self.get_exec_code())
        self.set_output(response)       

    def set_output(self,response):
        self.stdout=response.stdout
        self.stderr=response.stderr
        self.exception=response.exception

    def show_previous_output(self):
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
            state.rerun=True

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
            state.rerun=True
    
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
    The Streamlit notebook code cell object
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

    def __init__(self,notebook,key,code="",auto_rerun=True,fragment=False):
        super().__init__(notebook,key,code=code,auto_rerun=auto_rerun,fragment=False)
        self.has_fragment_toggle=False
        self.language="markdown"
        self.type="markdown"

    def get_exec_code(self):
        formatted_code=format(self.submitted_code,**state,**globals()).replace("'''","\'\'\'")
        code=f"st.markdown(r'''{formatted_code}''');"
        return code

class HTMLCell(Cell):

    def __init__(self,notebook,key,code="",auto_rerun=True,fragment=False):
        super().__init__(notebook,key,code=code,auto_rerun=auto_rerun,fragment=False)
        self.has_fragment_toggle=False
        self.language="html"
        self.type="html"

    def get_exec_code(self):
        formatted_code=format(self.submitted_code,**state,**globals()).replace("'''","\'\'\'")
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
    return type_to_class(type)(notebook,key,code=code,auto_rerun=auto_rerun,fragment=fragment)
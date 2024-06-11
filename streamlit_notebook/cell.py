import streamlit as st
from .state import state
from .editor import editor, editor_output_parser
from .utils import format

class Cell:

    "Implements the main notebook cell from which other cell types inherit"

    def __init__(self,key,code="",auto_rerun=True,fragment=False):
        self.code=code
        self.submitted_code=""
        self.key=key
        self.visible=True
        self.auto_rerun=auto_rerun
        self.output=None
        self.output_area=None
        self.has_run=False
        self.parser=editor_output_parser()
        self.language=None
        self.type=None
        self.fragment=fragment
        self.has_fragment_toggle=True

    def show(self):
        """
        Renders the cell's layout
        """
        self.has_run=False
        self.container=st.container()
        self.output_area=st.empty()
        self.output=self.output_area.container()
        if self.auto_rerun:
            self.run()
        if not state.hide_code_cells and self.visible:
            with self.container.container(border=True):
                self.menu_bar()
                event,new_code=self.parser(editor(self.code,lang=self.language,key=f"cell_editor_{self.key}"))
                if event=="submit" or event=="run":
                    self.has_run=False
                    self.code=new_code
                    self.submitted_code=self.code
                    if state.run_on_submit or event=="run":
                        self.run()
                self.status_bar()

    @property
    def rank(self):
        """
        Gets the current rank of the cell in the cells dict
        """
        return list(state.cells.keys()).index(self.key)


    def rerank(self,rank):
        """
        Moves the cell to a new rank
        """
        if 0<=rank<len(state.cells) and not rank==self.rank:
            keys=list(state.cells.keys())
            del keys[self.rank]
            keys.insert(rank,self.key)
            state.cells={k:state.cells[k] for k in keys}

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


    def menu_bar(self):
        """
        Renders the cell's menu bar
        """
        c1,c2,c3,_,c4,c5,c6=st.columns([7,30,30,20,5,5,5])
        c1.text(f"[{self.key}]")
        c2.toggle("Auto-Rerun",value=self.auto_rerun,on_change=self.toggle_auto_rerun,key=f"cell_auto_rerun_{self.key}")
        if self.has_fragment_toggle:
            c3.toggle("Run as fragment",value=self.fragment,on_change=self.toggle_fragment,key=f"cell_fragment_{self.key}")
        c4.button("🔺",on_click=self.move_up,key=f"cell_move_up_{self.key}",use_container_width=True)
        c5.button("🔻",on_click=self.move_down,key=f"cell_move_down_{self.key}",use_container_width=True)
        c6.button("❌",on_click=self.delete,key=f"cell_close_{self.key}",use_container_width=True)

    def status_bar(self):
        """
        Renders the cell's status bar
        """
        c1,_,c2=st.columns([15,85,5])
        c1.caption(self.type)
        if self.has_run:
            c2.write("✅")

    def toggle_auto_rerun(self):
        """
        Toggle auto_rerun attribute 
        """
        self.auto_rerun=not self.auto_rerun

    def toggle_fragment(self):
        """
        Toggle 'Run as fragment' 
        """
        self.fragment=not self.fragment

    def delete(self):
        """
        Deletes the cell
        """
        if self.key in state.cells:
            del state.cells[self.key]

    def run(self):
        """
        Runs the cell (renders it)
        """
        if not self.has_run and self.submitted_code:
            self.output=self.output_area.container()
            with self.output:
                self.exec()
            self.has_run=True

    def exec(self):
        raise NotImplementedError("Subclasses of cells must implement a custom exec method")
    

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

    def __init__(self,key,code="",auto_rerun=True,fragment=False):
        super().__init__(key,code=code,auto_rerun=auto_rerun,fragment=fragment)
        self.has_fragment_toggle=True
        self.language="python"
        self.type="code"

    def exec(self):
        if self.fragment:
            self.exec_code_as_fragment()
        else:
            self.exec_code()


    @st.experimental_fragment
    def exec_code_as_fragment(self):
        """
        Executes the cell as a fragment 
        """
        try:
            exec(self.submitted_code,globals())
        except Exception as e:
            st.exception(e)

    def exec_code(self):
        """
        Executes the cell normally
        """
        try:
            exec(self.submitted_code,globals())
        except Exception as e:
            st.exception(e)

class MarkdownCell(Cell):

    def __init__(self,key,code="",auto_rerun=True,fragment=False):
        super().__init__(key,code=code,auto_rerun=auto_rerun,fragment=False)
        self.has_fragment_toggle=False
        self.language="markdown"
        self.type="markdown"

    def exec(self):
        """
        Executes the markdown cell by running a st.markdown command with the content
        The content is preformatted with evaluated expressions enclosed in <<expr>> tags.
        """
        try:
            formatted_code=format(self.submitted_code,**state,**globals())
            code=f'st.markdown(r"""{formatted_code}""")'
            exec(code,globals())
        except Exception as e:
            st.exception(e)

class HTMLCell(Cell):

    def __init__(self,key,code="",auto_rerun=True,fragment=False):
        super().__init__(key,code=code,auto_rerun=auto_rerun,fragment=False)
        self.has_fragment_toggle=False
        self.language="html"
        self.type="html"

    def exec(self):
        """
        Executes the html cell by running a st.html command with the content
        The content is preformatted with evaluated expressions enclosed in <<expr>> tags.
        """
        try:
            formatted_code=format(self.submitted_code,**state,**globals())
            code=f'st.html(r"""{formatted_code}""")'
            exec(code,globals())
        except Exception as e:
            st.exception(e)

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

def new_cell(key,type="code",code="",auto_rerun=True,fragment=False):
    return type_to_class(type)(key,code=code,auto_rerun=auto_rerun,fragment=fragment)
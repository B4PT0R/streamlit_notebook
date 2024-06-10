import streamlit as st
from state import state
from editor import editor, editor_output_parser
from utils import format

class Cell:

    "Implements the main notebook cell from which other cell types inherit"

    def __init__(self,code,key,auto_rerun=True):
        self.code=code
        self.submitted_code=""
        self.key=key
        self.visible=True
        self.auto_rerun=auto_rerun
        self.output=None
        self.output_area=None
        self.has_run=False
        self.parser=editor_output_parser()
        self.language="python"
        self.type="code"

    def show(self):
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
                if event=="submit":
                    self.has_run=False
                    self.code=new_code
                    self.submitted_code=self.code
                    if state.run_on_submit:
                        self.run()
                if event=="run":
                    self.has_run=False
                    self.code=new_code
                    self.submitted_code=self.code
                    self.run()
                self.status_bar()

    @property
    def rank(self):
        return list(state.cells.keys()).index(self.key)


    def rerank(self,rank):
        if 0<=rank<len(state.cells) and not rank==self.rank:
            keys=list(state.cells.keys())
            del keys[self.rank]
            keys.insert(rank,self.key)
            state.cells={k:state.cells[k] for k in keys}

    def move_up(self):
        self.rerank(self.rank-1)

    def move_down(self):
        self.rerank(self.rank+1)


    def menu_bar(self):
        c1,c2,c3,_,c4,c5,c6=st.columns([7,30,30,20,5,5,5])
        c1.text(f"[{self.key}]")
        c2.toggle("Auto-Rerun",value=self.auto_rerun,on_change=self.switch_auto_rerun,key=f"cell_auto_rerun_{self.key}")
        #c3.toggle("Run as fragment",value=self.fragment,on_change=self.switch_fragment,key=f"cell_fragment_{self.key}")
        c4.button("🔺",on_click=self.move_up,key=f"cell_move_up_{self.key}",use_container_width=True)
        c5.button("🔻",on_click=self.move_down,key=f"cell_move_down_{self.key}",use_container_width=True)
        c6.button("❌",on_click=self.delete,key=f"cell_close_{self.key}",use_container_width=True)

    def status_bar(self):
        c1,_,c2=st.columns([15,85,5])
        c1.caption(self.type)
        if self.has_run:
            c2.write("✅")

    def switch_auto_run(self):
        self.auto_run=not self.auto_run

    def switch_auto_rerun(self):
        self.auto_rerun=not self.auto_rerun

    def delete(self):
        if self.key in state.cells:
            del state.cells[self.key]

    def run(self):
        raise NotImplementedError("Subclasses of Cell should implement a run method.")
            
class CodeCell(Cell):

    """
    The Streamlit notebook code cell object
    """

    def __init__(self,code,key,fragment=False,auto_rerun=True):
        super().__init__(code,key,auto_rerun=auto_rerun)
        self.fragment=fragment

    def menu_bar(self):
        """
        Renders the menu bar of the code cell.
        """
        c1,c2,c3,_,c4,c5,c6=st.columns([7,30,30,20,5,5,5])
        c1.text(f"[{self.key}]")
        c2.toggle("Auto-Rerun",value=self.auto_rerun,on_change=self.switch_auto_rerun,key=f"cell_auto_rerun_{self.key}")
        c3.toggle("Run as fragment",value=self.fragment,on_change=self.switch_fragment,key=f"cell_fragment_{self.key}")
        c4.button("🔺",on_click=self.move_up,key=f"cell_move_up_{self.key}",use_container_width=True)
        c5.button("🔻",on_click=self.move_down,key=f"cell_move_down_{self.key}",use_container_width=True)
        c6.button("❌",on_click=self.delete,key=f"cell_close_{self.key}",use_container_width=True)

    def run(self):
        """
        Runs the code written in the cell.
        """
        if not self.has_run and self.submitted_code:
            self.output=self.output_area.container()
            with self.output:
                if self.fragment:
                    self.exec_as_fragment()
                else:
                    self.exec()
            self.has_run=True
    
    def switch_fragment(self):
        self.fragment=not self.fragment

    @st.experimental_fragment
    def exec_as_fragment(self):
        try:
            exec(self.submitted_code,globals())
        except Exception as e:
            st.exception(e)

    def exec(self):
        try:
            exec(self.submitted_code,globals())
        except Exception as e:
            st.exception(e)

class MarkdownCell(Cell):

    def __init__(self,code,key,auto_rerun=True):
        super().__init__(code,key,auto_rerun=auto_rerun)
        self.language="markdown"
        self.type="markdown"

    def run(self):
        if not self.has_run and self.submitted_code:
            self.output=self.output_area.container()
            with self.output:
                self.exec()
            self.has_run=True

    def exec(self):
        try:
            formatted_code=format(self.submitted_code,**state,**globals())
            code=f'st.markdown(r"""{formatted_code}""")'
            exec(code,globals())
        except Exception as e:
            st.exception(e)

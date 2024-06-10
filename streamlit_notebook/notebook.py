from .state import state, init_state
from .cell import CodeCell,MarkdownCell
import streamlit as st 
import os

os.environ['APP_ROOT_PATH']=os.path.dirname(os.path.abspath(__file__))

def root_join(*args):
    return os.path.join(os.getenv('APP_ROOT_PATH'),*args)

class Notebook:

    """
    A Streamlit notebook object.
    """

    def __init__(self):
        init_state(
            cells={},
            current_cell_key=0,
            hide_code_cells=False,
            run_on_submit=True,
            show_logo=True,
            rerun=False
        )
        st.notebook=self

    def __getattr__(self,name):
        if name in state:
            return state[name]
        else:
            return super().__getattribute__(name)

    def show(self):

        """
        Renders the notebook's UI 
        """

        self.logo()        

        self.sidebar()

        for cell in list(state.cells.values()):
            cell.show()

        self.control_bar()

        if state.rerun:
            state.rerun=False
            st.rerun()
    
    def sidebar(self):
        with st.sidebar:
            st.image(root_join("app_images","st_notebook.png"),use_column_width=True)
            st.divider()
            def on_change():
                state.hide_code_cells=not state.hide_code_cells
            st.toggle("App mode",value=state.hide_code_cells,on_change=on_change, key="toggle_hide_cells")
            def on_change():
                state.run_on_submit=not state.run_on_submit
            st.toggle("Run cell on submit",value=state.run_on_submit,on_change=on_change,key="toggle_run_on_submit")
            def on_change():
                state.show_logo=not state.show_logo
            st.toggle("Show logo",value=state.show_logo,on_change=on_change,key="toggle_show_logo")
            st.divider()
            def on_click():
                self.clear_cells()
            st.button("Clear all cells",on_click=on_click,use_container_width=True,key="button_clear_cells")
            def on_click():
                self.run_all_cells()
            st.button("Run all cells",on_click=on_click,use_container_width=True,key="button_run_all_cells")



    def logo(self):
        if state.show_logo:
            _,c,_=st.columns([40,40,40])
            c.image(root_join("app_images","st_notebook.png"),use_column_width=True)


    def control_bar(self):
        if not state.hide_code_cells:
            c1,c2=st.columns(2)

            code_button=c1.button("New code cell",use_container_width=True,key="new_code_cell_button")
            mkdwn_button=c2.button("New Markdown cell",use_container_width=True,key="new_mkdwn_cell_button")
            
            if code_button:
                self.add_code_cell()
            if mkdwn_button:
                self.add_mkdwn_cell()

    def clear_cells(self):
        state.cells={}
        state.current_cell_key=0
        state.rerun=True

    def run_all_cells(self):
        for cell in state.cells.values():
            cell.has_run=False
            cell.run()


    def add_code_cell(self,code=""):
        """
        Adds a new code cell at the bottom of the notebook.
        """
        state.cells[state.current_cell_key]=CodeCell(code,state.current_cell_key)
        state.current_cell_key+=1
        state.rerun=True

    def add_mkdwn_cell(self,code=""):
        """
        Adds a new  Markdown cell at the bottom of the notebook.
        """
        state.cells[state.current_cell_key]=MarkdownCell(code,state.current_cell_key)
        state.current_cell_key+=1
        state.rerun=True


def st_notebook():
    if not 'notebook' in state:
        state.notebook=Notebook()
    state.notebook.show()


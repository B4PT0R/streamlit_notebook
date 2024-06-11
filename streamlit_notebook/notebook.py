from .state import state, init_state
from .cell import new_cell
from .attrdict import AttrDict
import streamlit as st 
import os
import json
from io import StringIO

os.environ['ROOT_PACKAGE_FOLDER']=os.path.dirname(os.path.abspath(__file__))

def root_join(*args):
    return os.path.join(os.getenv('ROOT_PACKAGE_FOLDER'),*args)

class Notebook:

    """
    The Streamlit notebook object.
    """

    def __init__(self):
        init_state(
            name="new_notebook",
            cells={},
            hide_code_cells=False,
            run_on_submit=True,
            show_logo=True,
            rerun=False
        )
        st.notebook=self

    def __getattr__(self,name):
        """
        Delegate attribute access to state
        """
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
        """
        Renders the notebook's sidebar
        """
        with st.sidebar:
            st.image(root_join("app_images","st_notebook.png"),use_column_width=True)
            st.divider()
            state.name=st.text_input("Notebook title:",value=state.name)
            if st.button("Upload notebook",use_container_width=True,key="button_upload_notebook"):
                self.upload_notebook()
            self.download_notebook()
            if st.button("Demo notebooks",use_container_width=True,key="button_load_demo"):
                self.load_demo()
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
        """
        Renders the app's logo
        """
        if state.show_logo:
            _,c,_=st.columns([40,40,40])
            c.image(root_join("app_images","st_notebook.png"),use_column_width=True)

    def control_bar(self):
        """
        Renders the notebooks "new code cell" and "new markdown cell" buttons
        """
        if not state.hide_code_cells:
            c1,c2,c3=st.columns(3)

            code_button=c1.button("New code cell",use_container_width=True,key="new_code_cell_button")
            mkdwn_button=c2.button("New Markdown cell",use_container_width=True,key="new_mkdwn_cell_button")
            html_button=c3.button("New HTML cell",use_container_width=True,key="new_html_cell_button")
            
            if code_button:
                self.add_new_cell(type="code")
            if mkdwn_button:
                self.add_new_cell(type="markdown")
            if html_button:
                self.add_new_cell(type="html")

    def clear_cells(self):
        """
        Deletes all cells
        """
        state.cells={}
        state.rerun=True

    def submit_all_cells(self):
        """
        Submit all cells
        """
        for cell in state.cells.values():
            cell.submit()

    def run_all_cells(self):
        """
        (Re)Run all the cells
        """
        for cell in state.cells.values():
            cell.run()

    def gen_cell_key(self):
        """
        Generates a unique key for the cell 
        """
        i=0
        while i in state.cells:
            i+=1
        return i

    def add_new_cell(self,type="code",code="",auto_rerun=True,fragment=False):
        """
        Adds a new cell of the chosen type at the bottom of the notebook
        """
        key=self.gen_cell_key()
        state.cells[key]=new_cell(key,type=type,code=code,auto_rerun=auto_rerun,fragment=fragment)
        state.rerun=True

    def delete_cell(self,key):
        """
        Deletes a cell given its key
        """
        if key in state.cells:
            state.cells[key].delete()

    def load_demo(self):
        """
        Loads a demo notebook found in the package folder at 'streamlit_notebook/demo_notebooks'
        """
        demo_folder=root_join("demo_notebooks")
        demos=list(os.listdir(demo_folder))
        def on_change():
            if state.demo_choice:
                with open(os.path.join(demo_folder,state.demo_choice)) as f:
                    self.from_json(f.read())
        st.selectbox("Choose a demo notebook.",options=demos,index=None,on_change=on_change,key="demo_choice")

    def to_json(self):
        """
        Converts the whole notebook to a json strings
        """
        data=dict(
            name=state.name,
            hide_code_cells=state.hide_code_cells,
            show_logo=state.show_logo,
            run_on_submit=state.run_on_submit,
            cells={k:state.cells[k].to_dict() for k in state.cells}
        )
        return json.dumps(data)
    
    def from_json(self,json_string):
        """
        Loads a new notebook from a json string
        """
        data=AttrDict(**json.loads(json_string))
        state.name=data.name
        state.hide_code_cells=data.hide_code_cells
        state.show_logo=data.show_logo
        state.run_on_submit=data.run_on_submit
        state.cells={}
        for cell in data.cells.values():
            cell=AttrDict(**cell)
            state.cells[cell.key]=new_cell(cell.key,type=cell.type,code=cell.code,auto_rerun=cell.auto_rerun,fragment=cell.fragment)
        self.submit_all_cells()
        state.rerun=True

    def upload_notebook(self):
        """
        Let the user upload a notebook from a json file and loads it.
        """
        def on_change():
            if state.uploaded_file is not None:
                self.from_json(StringIO(state.uploaded_file.getvalue().decode("utf-8")).read())
        st.file_uploader("Upload a notebook file from your local drive.",on_change=on_change,key="uploaded_file")

    def download_notebook(self):
        """
        Let the user download the current notebook as a json file
        """
        st.download_button(
            label="Download notebook",
            data=self.to_json(),
            file_name=f"{state.name}.json",
            mime="application/json",
            use_container_width=True
        )

def st_notebook():
    """
    Initializes and renders the notebook
    """
    if not 'notebook' in state:
        state.notebook=Notebook()
    state.notebook.show()


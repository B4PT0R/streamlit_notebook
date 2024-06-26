from .cell import new_cell, display
from .attrdict import AttrDict
from .echo import echo
from .utils import format
from .shell import Shell
import streamlit as st 
import os
import json
from io import StringIO
from textwrap import dedent,indent
import sys

os.environ['ROOT_PACKAGE_FOLDER']=os.path.dirname(os.path.abspath(__file__))

state=st.session_state

def root_join(*args):
    return os.path.join(os.getenv('ROOT_PACKAGE_FOLDER'),*args)

class Notebook:

    """
    The Streamlit notebook object.
    """

    def __init__(self):
        self.notebook_title="new_notebook"
        self.cells={}
        self._current_cell=None
        self.hide_code_cells=False
        self.run_on_submit=True
        self.show_logo=True
        self.rerun=False
        self.current_code=None
        st.notebook=self
        # Override st.echo to fit the notebook environment
        st.echo=echo(self.get_current_code).__call__
        self.init_shell()

    def init_shell(self):
        self.shell=Shell(stdout_hook=self.stdout_hook,result_hook=self.display_hook,exception_hook=self.exception_hook, code_hook=self.code_hook)
        self.shell.update_namespace(
            st=st,
            display=self.display_hook
        )

    @property
    def current_cell(self):
        return self._current_cell
    
    @current_cell.setter
    def current_cell(self,value):
        self._current_cell=value

    def code_hook(self,code):
        self.current_code=code

    def get_current_code(self):
        return self.current_code

    def stdout_hook(self,data,buffer):
        with self.current_cell.stdout_area:
            if buffer:
                st.code(buffer,language="text")

    def stderr_hook(self,data,buffer):
        with self.current_cell.stderr_area:
            if buffer:
                st.code(buffer,language="text")

    def display_hook(self,result):
        with self.current_cell.output:    
            self.current_cell.results.append(result)
            display(result)

    def exception_hook(self,exception):
        with self.current_cell.output: 
            st.exception(exception)

    def __getattr__(self,name):
        """
        Delegate unknown attribute access to state
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

        for cell in list(self.cells.values()):
            cell.show()

        self.control_bar()

        if self.rerun:
            self.rerun=False
            st.rerun()
    
    def sidebar(self):
        """
        Renders the notebook's sidebar
        """
        with st.sidebar:
            st.image(root_join("app_images","st_notebook.png"),use_column_width=True)
            st.divider()
            self.notebook_title=st.text_input("Notebook title:",value=self.notebook_title)
            if st.button("Upload notebook",use_container_width=True,key="button_upload_notebook"):
                self.upload_notebook()
            self.download_notebook()
            #self.download_python()
            if st.button("Demo notebooks",use_container_width=True,key="button_load_demo"):
                self.load_demo()
            st.divider()
            def on_change():
                self.hide_code_cells=not self.hide_code_cells
            st.toggle("App mode",value=self.hide_code_cells,on_change=on_change, key="toggle_hide_cells")
            def on_change():
                self.run_on_submit=not self.run_on_submit
            st.toggle("Run cell on submit",value=self.run_on_submit,on_change=on_change,key="toggle_run_on_submit")
            def on_change():
                self.show_logo=not self.show_logo
            st.toggle("Show logo",value=self.show_logo,on_change=on_change,key="toggle_show_logo")
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
        if self.show_logo:
            _,c,_=st.columns([40,40,40])
            c.image(root_join("app_images","st_notebook.png"),use_column_width=True)

    def control_bar(self):
        """
        Renders the notebooks "New XXX cell" buttons
        """
        if not self.hide_code_cells:
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
            file_name=f"{self.notebook_title}.json",
            mime="application/json",
            use_container_width=True
        )

    def download_python(self):
        """
        Let the user download the current notebook as a streamlit script file
        """
        st.download_button(
            label="Download as Python script",
            data=self.to_python(),
            file_name=f"{self.notebook_title}.py",
            mime="text/x-python",
            use_container_width=True
        )

    def clear_cells(self):
        """
        Deletes all cells
        """
        self.cells={}
        self.rerun=True

    def submit_all_cells(self):
        """
        Submit all cells
        """
        for cell in self.cells.values():
            cell.submit()

    def run_all_cells(self):
        """
        (Re)Run all the cells
        """
        for cell in self.cells.values():
            cell.run()

    def gen_cell_key(self):
        """
        Generates a unique key for the cell 
        """
        i=0
        while i in self.cells:
            i+=1
        return i

    def add_new_cell(self,type="code",code="",auto_rerun=False,fragment=False):
        """
        Adds a new cell of the chosen type at the bottom of the notebook
        """
        key=self.gen_cell_key()
        self.cells[key]=new_cell(self,key,type=type,code=code,auto_rerun=auto_rerun,fragment=fragment)
        self.rerun=True

    def delete_cell(self,key):
        """
        Deletes a cell given its key
        """
        if key in self.cells:
            self.cells[key].delete()

    def to_python(self):
        """
        Exports the notebook as a python script 
        """
        code="import streamlit as st\n\n"
        for cell in self.cells.values():
            code+=f"# cell_[{cell.key}]\n\n"
            if not cell.fragment:
                code+=cell.get_exec_code()+'\n\n'
            else:
                template=dedent("""
                @st.experimental_fragment
                def __():
                <<code>>
                
                __()
                """)
                code+=format(template,code=indent(cell.get_exec_code(),prefix='    '))+'\n\n'
        return code      

    def to_json(self):
        """
        Converts the whole notebook to a json strings
        """
        data=dict(
            name=self.notebook_title,
            hide_code_cells=self.hide_code_cells,
            show_logo=self.show_logo,
            run_on_submit=self.run_on_submit,
            cells={k:self.cells[k].to_dict() for k in self.cells}
        )
        return json.dumps(data)
    
    def from_json(self,json_string):
        """
        Loads a new notebook from a json string
        """
        data=AttrDict(**json.loads(json_string))
        self.notebook_title=data.name
        self.hide_code_cells=data.hide_code_cells
        self.show_logo=data.show_logo
        self.run_on_submit=data.run_on_submit
        self.cells={}
        for cell in data.cells.values():
            cell=AttrDict(**cell)
            self.cells[cell.key]=new_cell(self,cell.key,type=cell.type,code=cell.code,auto_rerun=cell.auto_rerun,fragment=cell.fragment)
        self.submit_all_cells()
        self.rerun=True


def st_notebook():
    """
    Initializes and renders the notebook
    """
    if not 'notebook' in state:
        state.notebook=Notebook()
    state.notebook.show()


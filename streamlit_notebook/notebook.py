from .cell import new_cell, display
from .attrdict import AttrDict
from .echo import echo
from .utils import format, rerun, check_rerun, root_join, state
from .shell import Shell
import streamlit as st 
import os
import json
from io import StringIO
from textwrap import dedent,indent
from typing import Union, Dict

class Notebook:

    """
    The main Streamlit notebook object.

    This class orchestrates the entire notebook, managing cells, execution,
    and overall notebook state.

    Attributes:
        title (str): The title of the notebook.
        cells (dict): A dictionary of Cell objects, keyed by their unique identifiers.
        hide_code_cells (bool): If True, code cells are hidden in the UI.
        run_on_submit (bool): If True, cells are executed immediately upon submission.
        show_logo (bool): If True, the notebook logo is displayed.
        shell (Shell): The Shell object used for code execution.

    Methods:
        show(): Renders the entire notebook UI.
        sidebar(): Renders the notebook's sidebar with controls.
        logo(): Renders the notebook's logo.
        control_bar(): Renders the control bar for adding new cells.
        load_demo(): Loads a demo notebook.
        upload_notebook(): Allows user to upload a notebook file.
        download_notebook(): Allows user to download the current notebook as a file.
        download_python(): Allows user to download the notebook as a Python script.
        clear_cells(): Deletes all cells in the notebook.
        run_all_cells(): Executes all cells in the notebook.
        new_cell(type, code, auto_rerun, fragment): Creates a new cell.
        delete_cell(key): Deletes a specific cell.
        to_python(): Converts the notebook to a Python script.
        to_json(): Converts the notebook to a JSON string.
        from_json(json_string): Loads a notebook from a JSON string.
    """

    def __init__(self,title="new_notebook"):
        self.title="new_notebook"
        self.cells={}
        self._current_cell=None
        self.hide_code_cells=False
        self.run_on_submit=True
        self.show_logo=True
        self.current_code=None
        # Override st.echo to fit the notebook environment
        st.echo=echo(self.get_current_code).__call__
        self.init_shell()

    def init_shell(self):
        """
        (Re)Initializes the shell to startup state.

        This method creates a new Shell instance with the necessary hooks and updates the namespace.
        """
        self.shell=Shell(
            stdout_hook=self.stdout_hook,
            display_hook=self.display_hook,
            exception_hook=self.exception_hook, 
            input_hook=self.input_hook
        )
        self.shell.update_namespace(
            st=st,
            notebook=self
        )

    @property
    def current_cell(self):
        """
        The cell currently executing code.

        This property is used in the shell hooks to know where to direct outputs of execution
        """
        return self._current_cell
    
    @current_cell.setter
    def current_cell(self,value):
        self._current_cell=value

    def input_hook(self,code):
        """
        Shell hook called whenever code is inputted.

        Args:
            code (str): The inputted code.
        """
        self.current_code=code

    def get_current_code(self):
        """
        Returns the code being currently executed.

        Returns:
            str: The current code being executed.
        """
        return self.current_code

    def stdout_hook(self,data,buffer):
        """
        Shell hook called whenever the shell attempts to write to stdout.

        Args:
            data (str): The data being written to stdout.
            buffer (str): The current content of the stdout buffer.
        """
        if self.current_cell.ready:
            with self.current_cell.stdout_area:
                if buffer:
                    st.code(buffer,language="text")

    def stderr_hook(self,data,buffer):
        """
        Shell hook called whenever the shell attempts to write to stderr.

        Args:
            data (str): The data being written to stderr.
            buffer (str): The current content of the stderr buffer.
        """
        if self.current_cell.ready:
            with self.current_cell.stderr_area:
                if buffer:
                    st.code(buffer,language="text")

    def display_hook(self,result):
        """
        Shell hook called whenever the shell attempts to display a result.

        Args:
            result: The result to be displayed.
        """
        self.current_cell.results.append(result)
        if self.current_cell.ready:
            with self.current_cell.output:    
                display(result)

    def exception_hook(self,exception):
        """
        Shell hook called whenever the shell catches an exception.

        Args:
            exception (Exception): The caught exception.
        """
        if self.current_cell.ready:
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
        Renders the notebook's UI.

        This method is responsible for displaying all components of the notebook,
        including the logo, sidebar, cells, and control bar.
        """

        self.logo()        

        self.sidebar()

        for cell in list(self.cells.values()):
            cell.show()

        self.control_bar()

    def sidebar(self):
        """
        Renders the notebook's sidebar.

        The sidebar contains various controls and options for the notebook,
        such as title editing, file operations, and display settings.
        """
        with st.sidebar:
            st.image(root_join("app_images","st_notebook.png"),use_column_width=True)
            st.divider()
            self.title=st.text_input("Notebook title:",value=self.title)
            if st.button("Upload notebook", use_container_width=True,key="button_upload_notebook"):
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
            def on_change():
                self.shell.display_mode=state.select_display_mode
            options=['all','last','none']
            st.selectbox("Display mode", options=options,index=options.index(self.shell.display_mode),on_change=on_change,key="select_display_mode")
            st.divider()
            st.button("Clear all cells",on_click=self.clear_cells,use_container_width=True,key="button_clear_cells")
            st.button("Restart shell",on_click=self.init_shell,use_container_width=True,key="button_restart_shell")
            st.button("Run all cells",on_click=self.run_all_cells,use_container_width=True,key="button_run_all_cells")

    def logo(self):
        """
        Renders the app's logo.

        Displays the notebook logo if show_logo is True.
        """
        if self.show_logo:
            _,c,_=st.columns([40,40,40])
            c.image(root_join("app_images","st_notebook.png"),use_column_width=True)

    def control_bar(self):
        """
        Renders the notebooks "New XXX cell" buttons.

        This bar allows users to add new code, markdown, or HTML cells to the notebook.
        """
        if not self.hide_code_cells:
            c1,c2,c3=st.columns(3)

            code_button=c1.button("New code cell",use_container_width=True,key="new_code_cell_button")
            mkdwn_button=c2.button("New Markdown cell",use_container_width=True,key="new_mkdwn_cell_button")
            html_button=c3.button("New HTML cell",use_container_width=True,key="new_html_cell_button")
            
            if code_button:
                self.new_cell(type="code")
            if mkdwn_button:
                self.new_cell(type="markdown")
            if html_button:
                self.new_cell(type="html")

    def load_demo(self):
        """
        Loads a demo notebook.

        Allows the user to select and load a pre-defined demo notebook from the package's demo folder.
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
        Lets the user upload a notebook from a .stnb file and loads it.

        This method handles file upload and notebook loading from the uploaded file.
        """
        def on_change():
            if state.uploaded_file is not None:
                if state.uploaded_file.name.endswith('.stnb'):
                    self.from_json(StringIO(state.uploaded_file.getvalue().decode("utf-8")).read())
                else:
                    st.error("Invalid file type. Please upload a .stnb file.")
                    state.uploaded_file = None

        st.file_uploader(
            "Upload a notebook file (.stnb) from your local drive.",
            type=['stnb'],
            on_change=on_change,
            key="uploaded_file"
        )

    def download_notebook(self):
        """
        Lets the user download the current notebook as a JSON file.

        This method creates a downloadable .stnb file containing the current notebook state.
        """
        st.download_button(
            label="Download notebook",
            data=self.to_json(),
            file_name=f"{self.title}.stnb",
            mime="application/json",
            use_container_width=True
        )

    def download_python(self):
        """
        Lets the user download the current notebook as a Streamlit script file.

        This method converts the notebook to a .py file that can be run as a standalone Streamlit app.
        """
        st.download_button(
            label="Download as Python script",
            data=self.to_python(),
            file_name=f"{self.title}.py",
            mime="text/x-python",
            use_container_width=True
        )

    def clear_cells(self):
        """
        Deletes all cells in the notebook.

        This method removes all cells from the notebook, resetting it to an empty state.
        """
        self.cells={}
        rerun()

    def run_all_cells(self):
        """
        (Re)Runs all the cells in the notebook.

        This method executes all cells in the notebook in order, updating their outputs.
        """
        for cell in self.cells.values():
            cell.run()

    def gen_cell_key(self):
        """
        Generates a unique key for the cell.

        Returns:
            int: A unique integer used as a cell key in the cells dict
        """
        i=0
        while i in self.cells:
            i+=1
        return i

    def new_cell(self,type="code",code="",auto_rerun=False,fragment=False):
        """
        Adds a new cell of the chosen type at the bottom of the notebook.

        Args:
            type (str): The type of cell to create ("code", "markdown", or "html").
            code (str): Initial code or content for the cell.
            auto_rerun (bool): If True, the cell will automatically re-run when changed.
            fragment (bool): If True, the cell will run as a Streamlit fragment.

        Returns:
            Cell: The newly created cell object.
        """
        key=self.gen_cell_key()
        cell=new_cell(self,key,type=type,code=code,auto_rerun=auto_rerun,fragment=fragment)
        self.cells[key]=cell
        rerun()
        return cell

    def delete_cell(self,key):
        """
        Deletes a cell given its key.

        Args:
            key: The unique identifier of the cell to be deleted.
        """
        if key in self.cells:
            self.cells[key].delete()

    def to_python(self):
        """
        Exports the notebook as a Python script.

        Returns:
            str: A string containing the Python script representation of the notebook.
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
        Converts the whole notebook to a JSON string.

        Returns:
            str: A JSON string representation of the notebook.
        """
        data=dict(
            title=self.title,
            hide_code_cells=self.hide_code_cells,
            display_mode=self.shell.display_mode,
            show_logo=self.show_logo,
            run_on_submit=self.run_on_submit,
            cells={k:self.cells[k].to_dict() for k in self.cells}
        )
        return json.dumps(data)
    
    def from_json(self,json_string):
        """
        Loads a new notebook from a JSON string.

        Args:
            json_string (str): A JSON string representing a notebook.

        This method replaces the current notebook state with the one defined in the JSON string.
        """
        self.shell_enabled=False
        data=AttrDict(**json.loads(json_string))
        self.title=data.get('title',data.get('name',"new_notebook"))
        self.hide_code_cells=data.get('hide_code_cells',False)
        self.shell.display_mode=data.get('display_mode','last')
        self.show_logo=data.get('show_logo',True)
        self.run_on_submit=data.get('run_on_submit',True)
        cells=data.get('cells',{})
        self.cells={}
        for cell in cells.values():
            cell=AttrDict(cell)
            self.cells[cell.key]=new_cell(self,cell.key,type=cell.type,code=cell.code,auto_rerun=cell.auto_rerun,fragment=cell.fragment)
        self.init_shell()
        rerun()

def st_notebook(initial_notebook: Union[str, Dict, None] = None):
    """
    Initializes and renders the notebook interface.

    This function sets up the Streamlit notebook environment, either starting with a blank notebook
    or loading an existing one based on the provided input.

    Args:
        initial_notebook (Union[str, Dict, None]): 
            Either a path to a JSON file, a JSON string, a dictionary representing 
            the notebook, or None to start with a blank notebook. Defaults to None.

    Raises:
        ValueError: If the provided initial_notebook is invalid or cannot be loaded.

    This function modifies the Streamlit session state and renders the notebook UI.
    It's the main entry point for using the Streamlit Notebook in an application.
    """

    if 'notebook' not in state:
        state.notebook = Notebook()
        
        if initial_notebook is not None:
            try:
                if isinstance(initial_notebook, str):
                    # Check if it's a file path
                    if initial_notebook.endswith('.stnb'):
                        with open(initial_notebook, 'r') as f:
                            notebook_data = json.load(f)
                    else:  # Assume it's a JSON string
                        notebook_data = json.loads(initial_notebook)
                elif isinstance(initial_notebook, dict):
                    notebook_data = initial_notebook
                else:
                    raise ValueError("Invalid initial_notebook type. Expected str, dict, or None.")
                
                state.notebook.from_json(json.dumps(notebook_data))
            except Exception as e:
                raise ValueError(f"Failed to load initial notebook: {str(e)}")

    state.notebook.show()
    check_rerun()

    



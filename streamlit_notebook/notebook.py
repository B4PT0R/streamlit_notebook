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
        clear_cells(): Deletes all cells in the notebook.
        run_all_cells(): Executes all cells in the notebook.
        new_cell(type, code, auto_rerun, fragment): Creates a new cell.
        delete_cell(key): Deletes a specific cell.
        to_python(): Converts the notebook to a Python script.
        to_json(): Converts the notebook to a JSON string.
        from_json(json_string): Loads a notebook from a JSON string.
    """

    def __init__(self,title="new_notebook",app_mode=False,locked=False):
        self.title=title
        self.cells={}
        self._current_cell=None
        self.app_mode=app_mode  # Whether to hide code cells (can be toggled in dev)
        self.locked=locked  # Whether app mode is locked (deployment mode, can't toggle back)
        self.run_on_submit=True
        self.show_logo=True
        self.show_stderr=False
        self.current_code=None
        # patch st.echo in streamlit module to fit the notebook environment
        st.echo=echo(self.get_current_code).__call__
        # replace streamlit module in sys.modules to ensure the interactive shell uses the patched version
        import sys
        sys.modules['streamlit']=st

        self.init_shell()

    def init_shell(self):
        """
        (Re)Initializes the shell to startup state.

        This method creates a new Shell instance with the necessary hooks and updates the namespace.
        """
        self.shell=Shell(
            stdout_hook=self.stdout_hook,
            stderr_hook=self.stderr_hook,
            display_hook=self.display_hook,
            exception_hook=self.exception_hook, 
            input_hook=self.input_hook
        )
        self.shell.update_namespace(
            st=st,
            __notebook__=self
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
        if self.show_stderr and self.current_cell.ready:
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
                formatted_traceback=f"**{type(exception).__name__}**: {str(exception)}\n```\n{exception.enriched_traceback_string}\n```"
                st.error(formatted_traceback)

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

        # Though not very intuitive, resetting cells 'has_run' state AT THE END of show()
        # instead of the beginning ensures that a cell isn't executed twice in the same run 
        # Indeed, in Streamlit, callbacks triggered by UI events are fired AT THE VERY BEGINNING of the current run.
        # So if a callback caused a cell to run during this run, resetting 'has_run' before the above
        # loop would cause the cell to run AGAIN in the same run when we reach it in the loop.
        # Causing potential DuplicateWidgetID errors and other issues.
        self.reset_cells()

    def sidebar(self):
        """
        Renders the notebook's sidebar.

        Chooses between app mode sidebar and notebook mode sidebar based on current state.
        """
        if self.app_mode:
            self.sidebar_app_mode()
        else:
            self.sidebar_notebook_mode()

    def sidebar_app_mode(self):
        """
        Renders the app mode sidebar with minimal controls.

        In app mode, users can only interact with the notebook, not edit it.
        Shows execution controls and basic settings.
        """
        with st.sidebar:
            st.image(root_join("app_images","st_notebook.png"),use_container_width=True)
            st.divider()

            # Title (read-only in locked mode, editable in preview mode)
            if self.locked:
                st.markdown(f"### {self.title}")
            else:
                self.title=st.text_input("Notebook title:",value=self.title)

            st.divider()

            # Execution controls
            st.markdown("**Execution**")
            if st.button("▶️ Run All Cells", use_container_width=True, key="app_run_all"):
                self.run_all_cells()
            if st.button("🔄 Reset & Run All", use_container_width=True, key="app_reset_run"):
                self.init_shell()
                self.run_all_cells()

            st.divider()

            # Display settings
            if not self.locked:
                # In preview mode, allow toggling back to notebook mode
                def on_toggle_app_mode():
                    self.app_mode=not self.app_mode
                st.toggle("App mode preview", value=True, on_change=on_toggle_app_mode, key="toggle_app_preview")

            def on_change():
                self.show_logo=not self.show_logo
            st.toggle("Show logo",value=self.show_logo,on_change=on_change,key="toggle_show_logo_app")

            st.divider()

            # Download notebook
            self.download_notebook()

            if self.locked:
                st.caption("🔒 Running in locked app mode")

    def sidebar_notebook_mode(self):
        """
        Renders the full development sidebar with all notebook controls.

        In notebook mode, users have full access to editing, cell management,
        and all configuration options.
        """
        with st.sidebar:
            st.image(root_join("app_images","st_notebook.png"),use_container_width=True)
            st.divider()
            self.title=st.text_input("Notebook title:",value=self.title)

            # Demo notebooks
            if st.button("Demo notebooks", use_container_width=True, key="button_load_demo"):
                self.load_demo()

            # Save button
            self.save_notebook()

            # Open button with expandable section
            if st.button("Open notebook", use_container_width=True, key="button_open_notebook_trigger"):
                state.show_open_dialog = not state.get('show_open_dialog', False)

            if state.get('show_open_dialog', False):
                with st.container():
                    self.open_notebook()
                    st.caption("Or upload from elsewhere:")
                    self.upload_notebook()

            # Download button (tertiary, less prominent)
            self.download_notebook_button()

            st.divider()

            # App mode preview toggle (only if not locked)
            if not self.locked:
                def on_change():
                    self.app_mode=not self.app_mode
                st.toggle("App mode preview",value=self.app_mode,on_change=on_change, key="toggle_app_mode")

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
            def on_change():
                self.show_stderr=state.toggle_show_stderr
            st.toggle("Show stderr output",value=self.show_stderr,on_change=on_change,key="toggle_show_stderr")
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
            c.image(root_join("app_images","st_notebook.png"),use_container_width=True)

    def control_bar(self):
        """
        Renders the notebooks "New XXX cell" buttons.

        This bar allows users to add new code, markdown, or HTML cells to the notebook.
        Only shown in notebook mode (not in app mode).
        """
        if not self.app_mode:
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
                    # Close the open dialog after successful upload
                    state.show_open_dialog = False
                else:
                    st.error("Invalid file type. Please upload a .stnb file.")
                    state.uploaded_file = None

        st.file_uploader(
            "Drag and drop or browse",
            type=['stnb'],
            on_change=on_change,
            key="uploaded_file",
            label_visibility="collapsed"
        )

    def save_notebook(self):
        """
        Saves the current notebook to a .stnb file in the current working directory.
        """
        def on_click():
            filename = f"{self.title}.stnb"
            filepath = os.path.join(os.getcwd(), filename)
            try:
                with open(filepath, 'w') as f:
                    f.write(self.to_json())
                st.toast(f"Saved to {filepath}",icon="💾")
            except Exception as e:
                st.toast(f"Failed to save: {str(e)}",icon="⚠️")

        st.button("Save notebook", use_container_width=True, key="button_save_notebook", on_click=on_click)

    def open_notebook(self):
        """
        Opens a .stnb file from the current working directory.
        """
        cwd = os.getcwd()
        stnb_files = [f for f in os.listdir(cwd) if f.endswith('.stnb')]

        if not stnb_files:
            st.info("No .stnb files found in current directory")
            return

        def on_change():
            if state.open_notebook_choice:
                filepath = os.path.join(cwd, state.open_notebook_choice)
                try:
                    with open(filepath, 'r') as f:
                        self.from_json(f.read())
                except Exception as e:
                    st.error(f"Failed to open: {str(e)}")

        st.selectbox(
            "Open notebook from current directory",
            options=stnb_files,
            index=None,
            on_change=on_change,
            key="open_notebook_choice"
        )

    def download_notebook(self):
        """
        Lets the user download the current notebook as a JSON file.

        This method creates a downloadable .stnb file containing the current notebook state.
        Used in app mode sidebar.
        """
        st.download_button(
            label="Download notebook",
            data=self.to_json(),
            file_name=f"{self.title}.stnb",
            mime="application/json",
            use_container_width=True
        )

    def download_notebook_button(self):
        """
        Tertiary download button for notebook mode sidebar.
        Less prominent than save/open, for exporting to Downloads folder.
        """
        st.download_button(
            label="⬇ Download",
            data=self.to_json(),
            file_name=f"{self.title}.stnb",
            mime="application/json",
            use_container_width=True,
            type="tertiary",
            help="Export notebook to Downloads folder"
        )

    def clear_cells(self):
        """
        Deletes all cells in the notebook.

        This method removes all cells from the notebook, resetting it to an empty state.
        """
        self.cells={}
        rerun()

    def reset_cells(self):
        """
        Resets all cells in the notebook.

        This method clears the outputs and state of all cells without deleting them.
        """
        for cell in self.cells.values():
            cell.has_run=False

    def run_all_cells(self):
        """
        (Re)Runs all the cells in the notebook.

        This method executes all cells in the notebook in order, updating their outputs.
        """
        for cell in list(self.cells.values()):
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

    def to_json(self):
        """
        Converts the whole notebook to a JSON string.

        Returns:
            str: A JSON string representation of the notebook.
        """
        data=dict(
            title=self.title,
            app_mode=self.app_mode,
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
        # Support both old 'hide_code_cells' and new 'app_mode' for backwards compatibility
        self.app_mode=data.get('app_mode',data.get('hide_code_cells',False))
        self.show_logo=data.get('show_logo',True)
        self.run_on_submit=data.get('run_on_submit',True)
        display_mode=data.get('display_mode','last')
        cells=data.get('cells',{})
        self.cells={}
        for cell in cells.values():
            cell=AttrDict(cell)
            self.cells[cell.key]=new_cell(self,cell.key,type=cell.type,code=cell.code,auto_rerun=cell.auto_rerun,fragment=cell.fragment)
        self.init_shell()
        self.shell.display_mode=display_mode
        rerun()

def st_notebook(initial_notebook: Union[str, Dict, None] = None, app_mode: bool = False, locked: bool = False):
    """
    Initializes and renders the notebook interface.

    This function sets up the Streamlit notebook environment, either starting with a blank notebook
    or loading an existing one based on the provided input.

    Args:
        initial_notebook (Union[str, Dict, None]):
            Either a path to a JSON file, a JSON string, a dictionary representing
            the notebook, or None to start with a blank notebook. Defaults to None.
        app_mode (bool):
            If True, starts in app mode (code cells hidden, minimal UI).
            Defaults to False.
        locked (bool):
            If True, locks the notebook in app mode (prevents toggling back to notebook mode).
            Useful for deployment. Defaults to False.

    Raises:
        ValueError: If the provided initial_notebook is invalid or cannot be loaded.

    This function modifies the Streamlit session state and renders the notebook UI.
    It's the main entry point for using the Streamlit Notebook in an application.
    """

    if 'notebook' not in state:
        state.notebook = Notebook(app_mode=app_mode, locked=locked)

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

    

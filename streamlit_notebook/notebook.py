from .cell import new_cell, display
from .echo import echo
from .utils import format, rerun, check_rerun, root_join, state
from .shell import Shell
import streamlit as st
import os
from textwrap import dedent, indent
from typing import Union, Dict
import inspect

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
        render(): Renders the entire notebook (with required pre and post actions).
        show(): Renders the UI (sidebar, logo, cells, controls)
        sidebar(): Renders the notebook's sidebar with controls.
        logo(): Renders the notebook's logo.
        control_bar(): Renders the control bar for adding new cells.
        load_demo(): Loads a demo notebook (UI method).
        save_notebook(): Saves the notebook with UI feedback (UI method).
        open_notebook(): Opens a notebook with file upload and UI feedback (UI method).
        clear_cells(): Deletes all cells in the notebook.
        run_next_cell(): runs the first cell encountered that hasn't run yet.
        run_all_cells(): Executes all cells in the notebook.
        restart_session(): reinitializes the shell and resets the cells to initial state
        save(filepath=None): save the current notebook as a .py file (UI-agnostic).
        open(source): opens a notebook from a .py file or code string (UI-agnostic).
        is_valid_notebook(source): static method to check if a source is a valid notebook.
        new_cell(type, code, reactive, fragment): Creates a new cell.
        delete_cell(key): Deletes a specific cell.
        @cell: decorator used to declare new cells in the .py notebook script
        to_python(): Converts the notebook to a Python script.
    """

    def __init__(self,
            title="new_notebook",
            app_mode=False,
            locked=False,
            run_on_submit=True,
            show_logo=True,
            show_stderr=False
        ):
        self.title=title
        self.cells={}
        self._current_cell=None
        self.app_mode=app_mode  # Whether to hide code cells (can be toggled in dev)
        self.locked=locked  # Whether app mode is locked (deployment mode, can't toggle back)
        self.run_on_submit=run_on_submit
        self.show_logo=show_logo
        self.show_stderr=show_stderr
        self.current_code=None
        self.initialized=False
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

    def render(self):
        """
        main rendering method called in each Streamlit run.
        """

        self.initialized=True

        self.show()

        # Though not very intuitive, resetting cells 'has_run' state AFTER show()
        # instead of before ensures that a cell isn't executed twice in the same run 
        # Indeed, in Streamlit, callbacks triggered by UI events are fired AT THE VERY BEGINNING of the current run.
        # So if a callback caused a cell to run during this run, resetting 'has_run' before cells show in the for
        # loop would cause the cell to run AGAIN in the same run when we reach it in the loop.
        # Causing potential DuplicateWidgetID errors and other issues.
        self.reset_run_states()
        check_rerun()

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

            st.text_input("Notebook title:",value=self.title,key="notebook_title_show",disabled=True)

            # Open button with expandable section
            if st.button("Open notebook", use_container_width=True, key="button_open_notebook_trigger"):
                state.show_open_dialog = not state.get('show_open_dialog', False)

            if state.get('show_open_dialog', False):
                with st.container():
                    self.open_notebook()

            st.divider()

            # Execution controls
            st.markdown("**Execution**")
            if st.button("▶️ Run Next Cell", use_container_width=True, key="app_run_next"):
                self.run_next_cell()
            if st.button("⏩​ Run All Cells", use_container_width=True, key="app_run_all"):
                self.run_all_cells()
            if st.button("🔄 Reset", use_container_width=True, key="app_reset_run"):
                self.restart_session()


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
            def on_title_change_edit():
                self.title = state.notebook_title_edit
            st.text_input("Notebook title:",value=self.title,key="notebook_title_edit",on_change=on_title_change_edit)

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

            st.divider()
    
            st.button("▶️​ Run next cell",on_click=self.run_next_cell,use_container_width=True,key="button_run_next_cell")
            st.button("⏩ Run all cells",on_click=self.run_all_cells,use_container_width=True,key="button_run_all_cells")
            st.button("🔄​ Restart session",on_click=self.restart_session,use_container_width=True,key="button_restart_session")
            st.button("🗑️​ Clear all cells",on_click=self.clear_cells,use_container_width=True,key="button_clear_cells")

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
        UI method: Loads a demo notebook from the package's demo folder.
        Provides user feedback via toast messages.
        """
        demo_folder = root_join("demo_notebooks")
        demos = [f for f in os.listdir(demo_folder) if f.endswith('.py')]

        def on_change():
            if state.demo_choice:
                filepath = os.path.join(demo_folder, state.demo_choice)
                try:
                    self.open(filepath)
                    st.toast(f"Loaded demo: {state.demo_choice}", icon="📚")
                except ValueError as e:
                    st.toast(str(e), icon="⚠️")
                except Exception as e:
                    st.toast(f"Failed to load demo: {str(e)}", icon="⚠️")

        st.selectbox("Choose a demo notebook.", options=demos, index=None, on_change=on_change, key="demo_choice")

    @staticmethod
    def is_valid_notebook(source):
        """
        Checks if a source (file path or code string) is a valid notebook.

        Args:
            source (str): Path to a .py file or notebook code string

        Returns:
            bool: True if the source is a valid notebook, False otherwise
        """
        try:
            # Check if source is a file path or code string
            if os.path.isfile(source):
                if not source.endswith('.py'):
                    return False
                with open(source, 'r') as f:
                    code = f.read()
            else:
                # Treat as code string
                code = source

            # Validate it's a notebook file by checking for the signature
            return all(map(lambda x:x in code,['from streamlit_notebook import ','get_notebook','render_notebook']))

        except Exception:
            return False

    def save_notebook(self):
        """
        UI method: Saves the current notebook to a .py file in the current working directory.
        Provides user feedback via toast messages.
        """
        def on_click():
            filename = f"{self.title}.py"
            filepath = os.path.join(os.getcwd(), filename)
            try:
                self.save(filepath)
                st.toast(f"Saved to {filepath}", icon="💾")
            except Exception as e:
                st.toast(f"Failed to save: {str(e)}", icon="⚠️")

        st.button("Save notebook", use_container_width=True, key="button_save_notebook", on_click=on_click)

    def open(self, source):
        """
        Opens a notebook from a .py file or code string by loading it into session state.

        The source can be either:
        - A filepath to a .py notebook file generated by save()
        - A string containing the notebook Python code directly

        Works by storing the script in session_state, which will be executed
        by the main script on rerun.

        Args:
            source (str): Path to the .py notebook file or notebook code string

        Raises:
            ValueError: If the source is not a valid notebook Python file
            Exception: If there's an error reading the file or loading the notebook
        """
        
        # Validate it's a notebook file using the helper
        if not self.is_valid_notebook(source):
            raise ValueError("This doesn't appear to be a valid notebook Python file.")

        # Check if source is a file path or code string
        if os.path.isfile(source):
            with open(source, 'r') as f:
                code = f.read()
        else:
            # Treat as code string
            code = source

        # Store the notebook script in session state
        state.notebook_script = code

        # Clear current notebook from state so it gets recreated
        if 'notebook' in state:
            del state['notebook']

        # Rerun to execute the new script (with delay to show toast if called from UI)
        rerun(delay=1.5)

    def open_notebook(self):
        """
        UI method: Opens a notebook .py file from the current working directory or via file upload.
        Provides user feedback via toast messages.
        """
        # File uploader for drag and drop
        uploaded_file = st.file_uploader(
            "📎 Drop a notebook file here or browse",
            type=['py'],
            key="notebook_file_uploader",
            help="Upload a .py notebook file"
        )

        if uploaded_file is not None:
            try:
                # Read the uploaded file
                code = uploaded_file.read().decode('utf-8')

                # Open the notebook from the code string
                self.open(code)
                st.toast(f"Opened notebook: {uploaded_file.name}", icon="📂")
                # Close the open dialog
                state.show_open_dialog = False
            except ValueError as e:
                st.toast(str(e), icon="⚠️")
            except Exception as e:
                st.toast(f"Failed to open uploaded file: {str(e)}", icon="⚠️")

        # Existing selectbox for local files
        cwd = os.getcwd()
        all_files = [f for f in os.listdir(cwd) if f.endswith('.py')]

        # Filter .py files to only show those that look like notebooks
        notebook_files = []
        for f in all_files:
            filepath = os.path.join(cwd, f)
            if self.is_valid_notebook(filepath):
                notebook_files.append(f)

        if not notebook_files:
            st.info("No notebook files (.py) found in current directory")
            return

        def on_change():
            if state.open_notebook_choice:
                filepath = os.path.join(cwd, state.open_notebook_choice)
                try:
                    self.open(filepath)
                    st.toast(f"Opened notebook: {state.open_notebook_choice}", icon="📂")
                    # Close the open dialog
                    state.show_open_dialog = False
                except ValueError as e:
                    st.toast(str(e), icon="⚠️")
                except Exception as e:
                    st.toast(f"Failed to open: {str(e)}", icon="⚠️")

        st.selectbox(
            "Or select from current directory",
            options=notebook_files,
            index=None,
            on_change=on_change,
            key="open_notebook_choice"
        )

    def clear_cells(self):
        """
        Deletes all cells in the notebook.

        This method removes all cells from the notebook, resetting it to an empty state.
        Provides user feedback via toast.
        """
        count = len(self.cells)
        self.cells = {}
        st.toast(f"Cleared {count} cell{'s' if count != 1 else ''}", icon="🗑️")
        rerun(delay=1.5)

    def reset_run_states(self):
        """
        Resets all cells in the notebook.

        This method clears the outputs and state of all cells without deleting them.
        """
        for cell in self.cells.values():
            cell.has_run=False

    def reset_cells(self):
        """
        Resets all cells in the notebook.

        This method clears the outputs and state of all cells without deleting them.
        """
        for cell in self.cells.values():
            cell.reset()

    def run_all_cells(self):
        """
        (Re)Runs all the cells in the notebook.

        This method executes all cells in the notebook in order, updating their outputs.
        Provides user feedback via toast.
        """
        count = 0
        for cell in list(self.cells.values()):
            if not cell.has_run_once:
                cell.run()
                count += 1

        if count > 0:
            st.toast(f"Executed {count} cell{'s' if count > 1 else ''}", icon="⏩")
        else:
            st.toast("All cells already executed", icon="✅")

    def run_next_cell(self):
        """
        Runs the first cell that hasn't been run yet.
        Provides user feedback via toast.
        """
        executed = False
        for cell in list(self.cells.values()):
            if not cell.has_run_once:
                cell.run()
                executed = True
                st.toast(f"Executed cell {cell.key}", icon="▶️")
                break

        if not executed:
            st.toast("All cells have been executed", icon="✅")

    def restart_session(self):
        """
        Restarts the Python session and resets all cells.
        Provides user feedback via toast.
        """
        self.reset_cells()
        self.init_shell()
        st.toast("Session restarted", icon="🔄")
        rerun(delay=1.5)

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

    def new_cell(self,type="code",code="",reactive=False,fragment=False):
        """
        Adds a new cell of the chosen type at the bottom of the notebook.

        Args:
            type (str): The type of cell to create ("code", "markdown", or "html").
            code (str): Initial code or content for the cell.
            reactive (bool): If True, the cell will automatically re-run when changed.
            fragment (bool): If True, the cell will run as a Streamlit fragment.

        Returns:
            Cell: The newly created cell object.
        """
        key=self.gen_cell_key()
        cell=new_cell(self,key,type=type,code=code,reactive=reactive,fragment=fragment)
        self.cells[key]=cell
        rerun()
        return cell
    
    def cell(self,type="code",reactive=False,fragment=False):
        """
        returns a decorator that adds a new cell created from a function's source code.
        allows programmatic creation of cells from code defined in functions.
        example:
        @notebook.cell(type="markdown")
        def my_markdown_cell():
            '''
            # This is a markdown cell
            You can write **Markdown** here.
            '''

        Args:
            type (str): The type of cell to create ("code", "markdown", or "html").
            reactive (bool): If True, the cell will automatically re-run when changed.
            fragment (bool): If True, the cell will run as a Streamlit fragment.
        Returns:
            function: A decorator that adds a new cell from the decorated function's code.
            
        """
        import inspect

        # Check if running directly (not via main.py's <notebook_script>)
        frame = inspect.currentframe()
        caller_globals = frame.f_back.f_globals if frame else {}
        caller_file = caller_globals.get('__file__', '<notebook_script>')

        skip=(caller_file != '<notebook_script>')

        def decorator(func):
            if skip or self.initialized:
                return func
            import inspect
            if type in ("markdown","html"):
                # Extract docstring for markdown and html cells
                code=dedent(inspect.getdoc(func) or "")
            else:
                source=self.get_source(func)
                # source includes the function definition line (def my_function():)
                # we need to remove it to get the actual function body
                # skipping first line only
                code=dedent("\n".join(source.split("\n")[1:]))

                # remove any last useless "pass" statement at function module level
                # carefully avoiding to remove indented pass statements inside the function body
                # (might be important to keep in sub-blocks)
                if code.rstrip().endswith("\npass"):
                    lines=code.rstrip().split("\n")
                    if len(lines)>=2 and not lines[-2].startswith(" "):
                        lines=lines[:-1]
                        code="\n".join(lines)

            return self.new_cell(type=type,code=code,reactive=reactive,fragment=fragment)
        return decorator
    
    def get_source(self, func):
        """
        Extracts the source code from a function for @nb.cell() decorator.

        The @nb.cell() decorator is only intended for use in Python script files,
        not for interactive shell usage.

        Args:
            func (function): The function from which to extract the source code.

        Returns:
            str: The source code of the function.

        Raises:
            ValueError: If the function is not defined in a valid context.
        """
        import ast

        # Get the filename where the function was defined
        filename = func.__code__.co_filename

        # Retrieve source code based on filename
        if filename == '<notebook_script>':
            # Function defined in the notebook script executed by main.py
            if 'notebook_script' in state:
                code = state.notebook_script
            else:
                raise ValueError(
                    f"Cannot retrieve source for function '{func.__name__}': "
                    "notebook_script not found in session state"
                )
        elif os.path.exists(filename):
            # Real file - read it
            with open(filename, 'r') as f:
                code = f.read()
        else:
            # Invalid context - this shouldn't happen with @nb.cell()
            raise ValueError(
                f"Cannot retrieve source for function '{func.__name__}': "
                f"@nb.cell() decorator is only for use in Python script files, "
                f"not interactive shell execution. "
                f"For interactive use, create cells with notebook.new_cell() instead."
            )

        # Parse the source code and extract the specific function
        try:
            module = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the function definition in the AST
        for node in module.body:
            if isinstance(node, ast.FunctionDef) and node.name == func.__name__:
                source_lines = code.split("\n")[node.lineno-1:node.end_lineno]
                return dedent("\n".join(source_lines))

        # Function not found in source
        raise ValueError(
            f"Could not find function '{func.__name__}' in source code"
        )
    
    def to_python(self):
        """
        Converts the whole notebook to a Python script.
        the script recreates the notebook structure using the @cell decorator.
        the file can be run as a standard Streamlit app.

        Returns:
            str: A Python script representation of the notebook.
        """
        lines=[]
        lines.append("# Generated by Streamlit Notebook")
        lines.append(f"# Original notebook: {self.title}")
        lines.append("# This file can be run directly with: streamlit run <filename>")
        lines.append("")
        lines.append("from streamlit_notebook import get_notebook, render_notebook")
        lines.append("import streamlit as st")
        lines.append("")
        lines.append("st.set_page_config(page_title=\"st.notebook\", layout=\"centered\", initial_sidebar_state=\"collapsed\")")
        lines.append("")

        # Only include non-default parameters
        defaults = {
            'title': 'new_notebook',
            'app_mode': False,
            'locked': False,
            'run_on_submit': True,
            'show_logo': True,
            'show_stderr': False
        }
        params = dict(
            title=self.title,
            app_mode=self.app_mode,
            locked=self.locked,
            run_on_submit=self.run_on_submit,
            show_logo=self.show_logo,
            show_stderr=self.show_stderr
        )
        params_str = ", ".join([
            f"{k}={repr(v)}"
            for k, v in params.items()
            if v != defaults.get(k)
        ])
        lines.append(f"nb = get_notebook({params_str})")

        # Use @cell decorator to recreate cells from functions
        # Sort by key to ensure consistent ordering
        for key in sorted(self.cells.keys()):
            cell = self.cells[key]
            if cell.type in ("markdown", "html"):
                lines.append("")
                lines.append(f"@nb.cell(type='{cell.type}', reactive={cell.reactive}, fragment={cell.fragment})")
                lines.append("def cell_{}():".format(cell.key))
                if cell.code.strip() == "":
                    lines.append("    pass")
                else:
                    # Handle triple quotes properly
                    content = dedent(cell.code)
                    if "'''" in content and '"""' not in content:
                        # Use double quotes
                        template = 'r"""\n{content}\n"""'
                    elif '"""' in content and "'''" not in content:
                        # Use single quotes
                        template = "r'''\n{content}\n'''"
                    elif "'''" in content and '"""' in content:
                        # Both present - escape double quotes
                        content = content.replace('"""', r'\"\"\"')
                        template = 'r"""\n{content}\n"""'
                    else:
                        # Neither present - use single quotes by default
                        template = "r'''\n{content}\n'''"
                    lines.append(indent(template.format(content=content), "    "))
            else:  # code cell
                lines.append("")
                lines.append(f"@nb.cell(type='code', reactive={cell.reactive}, fragment={cell.fragment})")
                lines.append("def cell_{}():".format(cell.key))
                if cell.code.strip() == "":
                    lines.append("    pass")
                else:
                    lines.append(indent(dedent(cell.code), "    "))

        lines.append("")
        lines.append("# Render the notebook")
        lines.append("# Using render_notebook() instead of nb.render() allows the notebook")
        lines.append("# to be replaced dynamically (e.g., when loading a different file)")
        lines.append("render_notebook()")
        return "\n".join(lines)
    
    def save(self,filepath=None):
        """
        Saves the notebook as a Python script file.

        Args:
            filepath (str): The path where the Python script will be saved.
                            If None, saves to the current working directory with the notebook title.
        """
        if filepath is None:
            filepath=os.path.join(os.getcwd(),f"{self.title}.py")
        with open(filepath,'w') as f:
            f.write(self.to_python())

    def delete_cell(self,key):
        """
        Deletes a cell given its key.

        Args:
            key: The unique identifier of the cell to be deleted.
        """
        if key in self.cells:
            self.cells[key].delete()

def get_notebook(
    title="new_notebook",
    app_mode=False,
    locked=False,
    run_on_submit=True,
    show_logo=True,
    show_stderr=False
) -> Notebook:
    """
    Retrieves the current notebook from state or creates a new one.

    If a notebook exists but its parameters don't match the requested ones,
    it will be recreated. This ensures that when switching notebooks (e.g.,
    in direct run mode), the new notebook's parameters are applied correctly.

    Args:
        title (str): The title of the notebook.
        app_mode (bool): If True, starts in app mode (code cells hidden, minimal UI).
        locked (bool): If True, locks the notebook in app mode (prevents toggling back to notebook mode).
        run_on_submit (bool): If True, cells are executed immediately upon submission.
        show_logo (bool): If True, the notebook logo is displayed.
        show_stderr (bool): If True, stderr output is shown.

    Returns:
        Notebook: The current or newly created Notebook object.
    """
    import sys

    # Check for --app flag in CLI arguments or ST_NOTEBOOK_APP_MODE environment variable
    # Both override the script's parameters to enforce locked app mode
    if '--app' in sys.argv or os.getenv('ST_NOTEBOOK_APP_MODE', '').lower() == 'true':
        app_mode = True
        locked = True

    # Check if we need to create or recreate the notebook
    should_create = False

    if 'notebook' not in state:
        should_create = True
    else:
        # Check if parameters match the existing notebook
        # Only recreate if parameters don't match AND the notebook is not yet initialized
        # (initialized means it went through the exec pass and created cells)
        nb = state.notebook
        if (not nb.initialized and
            (nb.title != title or
             nb.app_mode != app_mode or
             nb.locked != locked or
             nb.run_on_submit != run_on_submit or
             nb.show_logo != show_logo or
             nb.show_stderr != show_stderr)):
            should_create = True

    if should_create:
        state.notebook = Notebook(
            title=title,
            app_mode=app_mode,
            locked=locked,
            run_on_submit=run_on_submit,
            show_logo=show_logo,
            show_stderr=show_stderr
        )

    return state.notebook

_original_set_page_config = st.set_page_config

def set_page_config(*args, **kwargs):
    """
    Patched version of st.set_page_config that only runs during exec context.

    When a notebook is run directly via 'streamlit run notebook.py', this becomes
    a no-op. When render_notebook() re-execs the script with __file__ = '<notebook_script>',
    the actual page config is set. This makes <notebook_script> the canonical execution context.
    """
    # Check if running from exec context (via <notebook_script>)
    frame = inspect.currentframe()
    caller_globals = frame.f_back.f_globals if frame else {}
    caller_file = caller_globals.get('__file__', '<notebook_script>')

    # Only call set_page_config if in exec context
    if caller_file == '<notebook_script>':
        _original_set_page_config(*args, **kwargs)

def render_notebook():
    """
    Renders the notebook currently stored in session state.

    This function should be used instead of calling nb.render() directly
    when you want to support dynamic notebook loading. It ensures that
    even if the notebook object is replaced (e.g., when opening a new file),
    the render call will always work on the current notebook in state.

    This is particularly important when loading notebooks from .py files,
    where exec() creates a new notebook instance that replaces the original.

    Automatically handles direct runs via 'streamlit run notebook.py' by
    bootstrapping the session state when needed.
    """
    # Check if running directly (not via main.py's <notebook_script>)
    frame = inspect.currentframe()
    caller_globals = frame.f_back.f_globals if frame else {}
    caller_file = caller_globals.get('__file__', '<notebook_script>')

    if caller_file != '<notebook_script>':
        # Direct run - need to bootstrap
        if 'notebook_script' not in state:
            # First run - capture the script
            if os.path.exists(caller_file):
                with open(caller_file, 'r') as f:
                    state.notebook_script = f.read()
            # Clear notebook on first bootstrap so exec creates it fresh
            if 'notebook' in state:
                del state['notebook']

        # Execute the notebook script
        exec_globals = globals().copy()
        exec_globals.update({
            '__name__': '__main__',
            '__file__': '<notebook_script>',
            'st': st,
            'get_notebook': get_notebook,
            'render_notebook': render_notebook,
        })
        code_obj = compile(state.notebook_script, '<notebook_script>', 'exec')
        exec(code_obj, exec_globals)
        return  # New script already rendered

    # Normal render
    if 'notebook' not in state:
        st.error("No notebook found in session state. Did you call get_notebook() first?")
        return

    state.notebook.render()



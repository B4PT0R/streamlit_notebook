"""UI components for streamlit-notebook.

This module contains all UI-related methods for the Notebook class,
separated from the core notebook logic for better code organization.

The :class:`NotebookUI` class handles:
    - Sidebar rendering (app mode, notebook mode, and chat mode)
    - Logo display
    - Control bars for adding cells
    - Settings popover
    - Demo notebook loading UI
    - Save/open dialogs
    - AI Assistant chat interface

See Also:
    :class:`~streamlit_notebook.notebook.Notebook`: Core notebook orchestration
    :class:`~streamlit_notebook.core.components.cell_ui.CellUI`: Cell UI components
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import streamlit as st
import os
from .utils import root_join, state, state_key
from .rerun import rerun
from .components.float_container import float_container
from .chat import show_chat

if TYPE_CHECKING:
    from .notebook import Notebook


class NotebookUI:
    """UI component handler for Notebook.

    This class manages all user interface elements for the notebook,
    following the same pattern as :class:`~streamlit_notebook.core.components.cell_ui.CellUI`.

    Attributes:
        notebook: The parent :class:`~streamlit_notebook.notebook.Notebook` instance.

    Examples:
        The UI is automatically created by the Notebook::

            nb = Notebook(title="My Notebook")
            # nb.ui is automatically created
            nb.ui.show()  # Renders the complete UI

    See Also:
        :class:`~streamlit_notebook.notebook.Notebook`: Parent notebook class
    """

    def __init__(self, notebook: Notebook) -> None:
        """Initialize the NotebookUI.

        Args:
            notebook: The parent Notebook instance.
        """
        self.notebook = notebook

    def _prepare_skeleton(self) -> None:
        """Prepare the UI skeleton for the notebook."""

        self.main_container = st.container()
        with self.main_container:
            self.logo_container = st.empty()
            if self.notebook.config.layout.horizontal and not self.notebook.config.app_view:
                split = self.notebook.config.layout.vertical_split
                left_weight = split / 100
                right_weight = 1 - left_weight
                editor_col, output_col = st.columns([left_weight, right_weight])
                self.notebook._layout_columns = (editor_col, output_col)
            else:
                main_col = st.container()
                self.notebook._layout_columns = (main_col, None)
        

    def show(self) -> None:
        """Render the complete notebook UI.

        This method displays all components in the correct order:
            1. Logo (if enabled)
            2. Sidebar (app, notebook, or chat mode)
            3. Cells (delegated to each cell)
            4. Control bar (in notebook mode)
        """

        self._prepare_skeleton()

        with self.main_container:

            if self.notebook.config.show_logo:
                with self.logo_container:
                    self.logo()

            for cell in list(self.notebook.cells):  # list to prevent issues if cells are modified during iteration
                if cell in self.notebook.cells: # may have been removed by the time we get here
                    cell.show()


            self.control_bar()

        # we draw the sidebar after the cells so that any long running operation from the sidebar (eg. chat) does not block the main UI
        # the user may thus look at the cells while the agent explains the code
        self.sidebar()

    def logo(self) -> None:
        """
        Render the notebook logo.
        """
        with st.container(horizontal=True, horizontal_alignment='center'):
            st.space(size='stretch')
            st.image(root_join("app_images", "st_notebook.png"),width=300)
            st.space(size='stretch')

    def _ensure_title_state(self) -> None:
        current_title = self.notebook.config.title
        state[state_key("notebook_title")] = current_title

    def sidebar(self) -> None:
        """Render the appropriate sidebar based on mode.

        Delegates to either :meth:`sidebar_app_mode`, :meth:`sidebar_notebook_mode`,
        or :meth:`sidebar_chat_mode` depending on the current mode settings.
        """
        self._ensure_title_state()
        # Check if chat mode is active
        if state.get(state_key("chat_mode"), False):
            self.sidebar_chat_mode()
        elif self.notebook.config.app_view:
            self.sidebar_app_mode()
        else:
            self.sidebar_notebook_mode()

    def sidebar_app_mode(self) -> None:
        """Render the app mode sidebar.

        App mode provides a minimal interface for deployed notebooks:
            - Notebook title (read-only)
            - Open notebook dialog
            - Execution controls (Run Next, Run All, Reset)
            - Display settings
            - Toggle to exit app view (if not in locked app mode)

        Note:
            In locked app mode, users cannot toggle back to edit mode.
        """
        with st.sidebar:
            self.logo()
            st.divider()

            st.text_input("Notebook title:", key=state_key("notebook_title"), disabled=True)

            # Open button with expandable section
            if st.button("Open notebook", width='stretch', key=state_key("button_open_notebook_trigger")):
                show_open_key = state_key("show_open_dialog")
                state[show_open_key] = not state.get(show_open_key, False)

            if state.get(state_key("show_open_dialog"), False):
                with st.container():
                    self.open_notebook()

            st.divider()

            # Execution controls
            st.markdown("**Execution**")
            if st.button("▶️ Run Next Cell", width='stretch', key=state_key("app_run_next")):
                self.notebook.run_next_cell()
            if st.button("⏩​ Run All Cells", width='stretch', key=state_key("app_run_all")):
                self.notebook.run_all_cells()
            if st.button("🔄 Reset", width='stretch', key=state_key("app_reset_run")):
                self.notebook.restart_session()

            st.divider()

            a,b=st.columns(2,gap='small')
            with a:
                # App view toggle (only if not in locked app mode)
                def on_change():
                    self.notebook.config.app_view = not self.notebook.config.app_view
                st.toggle("App view", value=self.notebook.config.app_view, on_change=on_change, key=state_key("toggle_app_view") ,disabled=self.notebook.config.app_mode)
            with b:
                def on_change():
                    self.notebook.config.show_logo = not self.notebook.config.show_logo
                st.toggle("Show logo", value=self.notebook.config.show_logo, on_change=on_change, key=state_key("toggle_show_logo"))

            def on_change():
                self.notebook.config.layout.width=state[state_key("slider_width")]

            width=self.notebook.config.layout.width
            current_width=68 if width=="centered" else 100 if width=="wide" else width
            st.slider("Layout Width (%)", min_value=60, max_value=100, value=current_width, step=1, key=state_key("slider_width"), on_change=on_change)

            # Vertical split slider (only visible in horizontal layout mode)
            if self.notebook.config.layout.horizontal:
                def on_split_change():
                    self.notebook.config.layout.vertical_split = state[state_key("slider_vertical_split")]
                st.slider(
                    "Code/Output Split (%)",
                    min_value=20,
                    max_value=80,
                    value=int(self.notebook.config.layout.vertical_split),
                    step=5,
                    key=state_key("slider_vertical_split"),
                    on_change=on_split_change,
                    help="Adjust the relative width of code editor vs output area"
                )

            st.divider()

            if self.notebook.config.app_mode:
                st.caption("🔒 Running in locked app mode")

    def sidebar_notebook_mode(self) -> None:
        """Render the full notebook development sidebar.

        Notebook mode provides complete editing capabilities:
            - Notebook title (editable)
            - Demo notebooks button
            - Save/Open buttons
            - Execution controls (Run Next, Run All, Restart, Clear)
            - App mode preview toggle
            - Display settings
            - Technical settings popover
        """
        with st.sidebar:
            self.logo()
            st.divider()

            def on_title_change_edit():
                self.notebook.config.title = state[state_key("notebook_title")]
            st.text_input("Notebook title:", key=state_key("notebook_title"), on_change=on_title_change_edit)

            # Demo notebooks
            if st.button("Demo notebooks", width='stretch', key=state_key("button_load_demo")):
                state[state_key("show_open_demo")] = not state.get(state_key("show_open_demo"), False)

            if state.get(state_key("show_open_demo"), False):    
                self.load_demo()

            # New notebook button
            if st.button("New notebook", width='stretch', key=state_key("button_new_notebook")):
                self.notebook.open()

            # Save button
            self.save_notebook()

            # Open button with expandable section
            if st.button("Open notebook", width='stretch', key=state_key("button_open_notebook_trigger")):
                state[state_key("show_open_dialog")] = not state.get(state_key("show_open_dialog"), False)

            if state.get(state_key("show_open_dialog"), False):
                with st.container():
                    self.open_notebook()

            st.divider()

            # AI Assistant button
            def on_chat_click():
                state[state_key("chat_mode")] = True
            st.button("AI Chat", on_click=on_chat_click, width='stretch', key=state_key("button_open_chat"), type="primary")

            st.divider()

            a,b=st.columns(2,gap='small')
            with a:
                # App view toggle (only if not in locked app mode)
                if not self.notebook.config.app_mode:
                    def on_change():
                        self.notebook.config.app_view = not self.notebook.config.app_view
                    st.toggle("App view", value=self.notebook.config.app_view, on_change=on_change, key=state_key("toggle_app_view"))
            with b:
                def on_change():
                    self.notebook.config.show_logo = not self.notebook.config.show_logo
                st.toggle("Show logo", value=self.notebook.config.show_logo, on_change=on_change, key=state_key("toggle_show_logo"))

            # Minimize/Expand all cells buttons
            c,d=st.columns(2,gap='small')
            with c:
                if st.button("🔽 Minimize All", key=state_key("button_minimize_all_notebook"), type="tertiary"):
                    self.notebook.minimize_all()
            with d:
                if st.button("🔼 Expand All", key=state_key("button_expand_all_notebook"), type="tertiary"):
                    self.notebook.expand_all()

            def on_change():
                self.notebook.config.layout.width=state[state_key("slider_width")]

            width=self.notebook.config.layout.width
            current_width=68 if width=="centered" else 100 if width=="wide" else width
            st.slider("Layout Width (%)", min_value=60, max_value=100, value=current_width, step=1, key=state_key("slider_width"), on_change=on_change)

            # Vertical split slider (only visible in horizontal layout mode)
            if self.notebook.config.layout.horizontal:
                def on_split_change():
                    self.notebook.config.layout.vertical_split = state[state_key("slider_vertical_split")]
                st.slider(
                    "Code/Output Split (%)",
                    min_value=20,
                    max_value=80,
                    value=int(self.notebook.config.layout.vertical_split),
                    step=5,
                    key=state_key("slider_vertical_split"),
                    on_change=on_split_change,
                    help="Adjust the relative width of code editor vs output area"
                )

            st.divider()

            # Technical settings dialog
            self.settings_dialog()
            # Quit button
            self.quit_button()

    def sidebar_chat_mode(self) -> None:
        """Render the AI Assistant chat sidebar.

        The notebook cells remain visible in the main area.
        """
        with st.sidebar:
            # Show chat interface (from chat.py)
            show_chat()

    def settings_dialog(self) -> None:
        """Render the technical settings dialog.

        Provides advanced configuration options:
            - Run cell on submit toggle
            - Display mode selection (all/last/none)
            - Stdout output toggle
            - Stderr output toggle
        """
        @st.dialog("⚙️ Settings")
        def show_settings():
            def on_change():
                self.notebook.config.run_on_submit = not self.notebook.config.run_on_submit
            st.toggle("Run cell on submit", value=self.notebook.config.run_on_submit, on_change=on_change, key=state_key("toggle_run_on_submit"))

            def on_change():
                self.notebook.shell.display_mode = state[state_key("select_display_mode")]
            options = ['all', 'last', 'none']
            st.selectbox("Display mode", options=options, index=options.index(self.notebook.shell.display_mode), on_change=on_change, key=state_key("select_display_mode"))

            def on_change():
                self.notebook.config.show_stdout = state[state_key("toggle_show_stdout")]
            st.toggle("Show stdout output", value=self.notebook.config.show_stdout, on_change=on_change, key=state_key("toggle_show_stdout"))

            def on_change():
                self.notebook.config.show_stderr = state[state_key("toggle_show_stderr")]
            st.toggle("Show stderr output", value=self.notebook.config.show_stderr, on_change=on_change, key=state_key("toggle_show_stderr"))

            def on_change():
                self.notebook.config.layout.horizontal = state[state_key("toggle_horizontal_layout")]
            st.toggle("Horizontal layout", value=self.notebook.config.layout.horizontal, on_change=on_change, key=state_key("toggle_horizontal_layout"), help="Display cells horizontally: code on left, output on right (ideal for dashboards)")

            if st.button("Close", width='stretch', type="primary", key=state_key("settings_close")):
                rerun(wait=False, debug_msg="settings dialog close button")

        if st.button("⚙️ Settings", width='stretch', key=state_key("button_open_settings")):
            show_settings()

    def quit_button(self) -> None:
        """Render the quit button.

        When clicked, calls notebook.quit() which displays a goodbye dialog
        and cleanly shuts down the Streamlit server.

        The button is hidden when no_quit is True (e.g., in cloud deployments).
        """
        # Don't show quit button if no_quit is enabled
        if self.notebook.config.no_quit:
            return

        if st.button("🚪 Quit", width='stretch', key=state_key("button_quit"), type="secondary"):
            self.notebook.quit()

    def control_bar(self) -> None:
        """Render the new cell and execution control bar.

        Displays two rows of buttons:
            - Add cells: Code, Markdown, HTML
            - Execute: Run Next, Run All, Restart Session

        Note:
            Only shown in edit mode (hidden in app view).
        """
        if not self.notebook.config.app_view:
            float_css = """
                position: fixed;
                left: __parent__.geometry.center;
                transform: translateX(-50%);
                bottom: 0.75rem;
                z-index: 1000;
                width: 33vw;
                max-width: 640px;
                min-width: 360px;
                background-color: __theme__.background-color-alpha;
                backdrop-filter: blur(10px);
                border: 1px solid __theme__.border-color;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                border-radius: 12px;
                padding: 1rem 1rem 1rem;
            """
            document_css = """
                @media (max-width: 640px) {
                    __child__ {
                        width: 90vw;
                        min-width: unset;
                        max-width: 90vw;
                        bottom: 0.5rem;
                    }
                }
            """
            with st.container(gap="small", border=False):
                float_container(
                    ref="notebook-main",
                    container_css=float_css,
                    document_css=document_css,
                    padding_bottom="7.5rem",
                    alpha=0.35,
                )
                a,b,c=st.columns(3,gap="small")
                with a:
                    def on_click():
                        self.notebook.new_cell(type="code")
                    st.button("New Code Cell", width='stretch', on_click=on_click, key=state_key("add_code_cell")) 
                with b: 
                    def on_click():
                        self.notebook.new_cell(type="markdown")
                    st.button("New Markdown Cell", width='stretch', on_click=on_click, key=state_key("add_markdown_cell"))
                with c:
                    def on_click():
                        self.notebook.new_cell(type="html")
                    st.button("New HTML Cell", width='stretch', on_click=on_click, key=state_key("add_html_cell"))

                d,e,f=st.columns(3,gap="small")
                with d:
                    def on_click():
                        self.notebook.run_next_cell()
                    st.button("▶️ Run Next",width='stretch', on_click=on_click, key=state_key("exec_run_next"))
                with e:
                    def on_click():
                        self.notebook.run_all_cells()
                    st.button("⏩ Run All",width='stretch', on_click=on_click, key=state_key("exec_run_all"))
                with f:
                    def on_click():
                        self.notebook.restart_session()
                    st.button("🔄 Restart",width='stretch', on_click=on_click, key=state_key("exec_restart"))


    def load_demo(self) -> None:
        """Render demo notebook selection dialog.

        Displays a selectbox with available demo notebooks from the package.
        When a demo is selected, it's loaded via :meth:`~streamlit_notebook.notebook.Notebook.open`.

        Provides user feedback via toast notifications for success and errors.
        """

        source = None
        name = "unknown"

        demo_folder = root_join("demo_notebooks")
        demos = sorted([f for f in os.listdir(demo_folder) if f.endswith('.py')])
        selected=st.selectbox("Choose a demo notebook.", options=demos, index=None, key=state_key("demo_choice"))

        if selected and not selected == state.get(state_key("last_opened_notebook"), None):
            # Clear immediately to prevent re-triggering
            source = os.path.join(demo_folder, selected)
            name = selected
            state[state_key("last_opened_notebook")] = source
            
        if source is not None:
            try:
                self.notebook.open(source)
                self.notebook.notify(f"Loaded demo: {name}", icon="📚")
                state[state_key("show_open_demo")] = False
            except ValueError as e:
                self.notebook.notify(str(e), icon="⚠️")
            except Exception as e:
                self.notebook.notify(f"Failed to load demo: {str(e)}", icon="⚠️")

    def save_notebook(self) -> None:
        """Render the save notebook button with menu.

        Creates a button that toggles a menu with two save options:
            1. Save Locally - saves to current working directory
            2. Download - downloads the ``.py`` file through browser

        The filename is based on the notebook title.

        Provides user feedback via toast notifications for success and errors.

        See Also:
            :meth:`~streamlit_notebook.notebook.Notebook.save`: Core save logic
        """
        # Toggle button to show/hide save options
        if st.button("Save notebook", width='stretch', key=state_key("button_save_notebook_trigger")):
            show_save_key = state_key("show_save_dialog")
            state[show_save_key] = not state.get(show_save_key, False)

        if state.get(state_key("show_save_dialog"), False):
            with st.container():
                col1, col2 = st.columns(2)

                with col1:
                    # Save Locally button
                    def on_save_locally():
                        filename = f"{self.notebook.config.title}.py"
                        filepath = os.path.join(os.getcwd(), filename)
                        try:
                            saved = self.notebook.save(filepath)
                            if saved:
                                self.notebook.notify(f"Saved to {filepath}", icon="💾")
                        except Exception as e:
                            self.notebook.notify(f"Failed to save: {str(e)}", icon="⚠️")

                    st.button("💾 Save Locally", width='stretch', key=state_key("button_save_locally"), on_click=on_save_locally)

                with col2:
                    # Download button
                    filename = f"{self.notebook.config.title}.py"
                    python_code = self.notebook.to_python()

                    st.download_button(
                        label="⬇️ Download",
                        data=python_code,
                        file_name=filename,
                        mime="text/x-python",
                        key=state_key("button_download_notebook"),
                        width="stretch"
                    )

    def open_notebook(self) -> None:
        """Render the open notebook dialog.

        Provides two ways to open notebooks:
            1. File uploader for drag-and-drop (unless in locked app mode)
            2. Selectbox for files in current working directory

        Only shows valid notebook ``.py`` files (validated via
        :meth:`~streamlit_notebook.notebook.Notebook.is_valid_notebook`).

        Provides user feedback via toast notifications for success and errors.

        See Also:
            :meth:`~streamlit_notebook.notebook.Notebook.open`: Core open logic
        """
        
        source = None
        name = "unknown"
        
        # File uploader for drag and drop (only if not in locked app mode)
        if not self.notebook.config.app_mode:

            uploaded_file = st.file_uploader(
                "📎 Drop a notebook file here or browse",
                type=['py'],
                key=state_key("notebook_file_uploader"),
                help="Upload a .py notebook file"
            )

            if uploaded_file is not None:
                try:
                    # Read the uploaded file
                    source = uploaded_file.read().decode('utf-8')
                    name = uploaded_file.name
                except ValueError as e:
                    self.notebook.notify(str(e), icon="⚠️")
                except Exception as e:
                    self.notebook.notify(f"Failed to open uploaded file: {str(e)}", icon="⚠️")

        # Existing selectbox for local files
        cwd = os.getcwd()
        all_files = [f for f in os.listdir(cwd) if f.endswith('.py')]

        # Filter .py files to only show those that look like notebooks
        notebook_files = []
        for f in all_files:
            filepath = os.path.join(cwd, f)
            if self.notebook.is_valid_notebook(filepath):
                notebook_files.append(f)

        if not notebook_files:
            st.info("No notebook files (.py) found in current directory")
        else:        
            selected = st.selectbox(
                "Or select from current directory",
                options=notebook_files,
                index=None,
                key=state_key("open_notebook_choice")
            )

            if selected and not selected == state.get(state_key("last_opened_notebook"), None):
                source = os.path.join(cwd, selected)
                name = selected
                state[state_key("last_opened_notebook")] = source

        if source is not None:
            # Now safely open the notebook
            try:
                self.notebook.open(source)
                self.notebook.notify(f"Opened notebook: {name}", icon="📂")
                # Close the open dialog
                state[state_key("show_open_dialog")] = False
            except ValueError as e:
                self.notebook.notify(str(e), icon="⚠️")
            except Exception as e:
                self.notebook.notify(f"Failed to open: {str(e)}", icon="⚠️")

            

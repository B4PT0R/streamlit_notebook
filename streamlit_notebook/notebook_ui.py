"""UI components for streamlit-notebook.

This module contains all UI-related methods for the Notebook class,
separated from the core notebook logic for better code organization.

The :class:`NotebookUI` class handles:
    - Sidebar rendering (app mode and notebook mode)
    - Logo display
    - Control bars for adding cells
    - Settings popover
    - Demo notebook loading UI
    - Save/open dialogs

See Also:
    :class:`~streamlit_notebook.notebook.Notebook`: Core notebook orchestration
    :class:`~streamlit_notebook.cell_ui.CellUI`: Cell UI components
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import streamlit as st
import os
from .utils import root_join, state

if TYPE_CHECKING:
    from .notebook import Notebook


class NotebookUI:
    """UI component handler for Notebook.

    This class manages all user interface elements for the notebook,
    following the same pattern as :class:`~streamlit_notebook.cell_ui.CellUI`.

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

    def show(self) -> None:
        """Render the complete notebook UI.

        This method displays all components in the correct order:
            1. Logo (if enabled)
            2. Sidebar (app or notebook mode)
            3. Cells (delegated to each cell)
            4. Control bar (in notebook mode)
        """
        self.logo()
        self.sidebar()

        for cell in list(self.notebook.cells):  # list to prevent issues if cells are modified during iteration
            cell.show()

        self.control_bar()

    def logo(self) -> None:
        """Render the notebook logo.

        Displays the streamlit-notebook logo centered at the top of the page
        if ``notebook.show_logo`` is True.
        """
        if self.notebook.show_logo:
            _, c, _ = st.columns([40, 40, 40])
            c.image(root_join("app_images", "st_notebook.png"), use_container_width=True)

    def sidebar(self) -> None:
        """Render the appropriate sidebar based on mode.

        Delegates to either :meth:`sidebar_app_mode` or :meth:`sidebar_notebook_mode`
        depending on the current ``notebook.app_mode`` setting.
        """
        if self.notebook.app_mode:
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
            - Toggle to exit preview mode (if not locked)

        Note:
            In locked mode, users cannot toggle back to notebook mode.
        """
        with st.sidebar:
            st.image(root_join("app_images", "st_notebook.png"), use_container_width=True)
            st.divider()

            st.text_input("Notebook title:", value=self.notebook.title, key="notebook_title_show", disabled=True)

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
                self.notebook.run_next_cell()
            if st.button("⏩​ Run All Cells", use_container_width=True, key="app_run_all"):
                self.notebook.run_all_cells()
            if st.button("🔄 Reset", use_container_width=True, key="app_reset_run"):
                self.notebook.restart_session()

            st.divider()

            # Display settings
            if not self.notebook.locked:
                # In preview mode, allow toggling back to notebook mode
                def on_toggle_app_mode():
                    self.notebook.app_mode = not self.notebook.app_mode
                st.toggle("App mode preview", value=True, on_change=on_toggle_app_mode, key="toggle_app_preview")

            def on_change():
                self.notebook.show_logo = not self.notebook.show_logo
            st.toggle("Show logo", value=self.notebook.show_logo, on_change=on_change, key="toggle_show_logo_app")

            st.divider()

            if self.notebook.locked:
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
            st.image(root_join("app_images", "st_notebook.png"), use_container_width=True)
            st.divider()

            def on_title_change_edit():
                self.notebook.title = state.notebook_title_edit
            st.text_input("Notebook title:", value=self.notebook.title, key="notebook_title_edit", on_change=on_title_change_edit)

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

            st.button("▶️​ Run next cell", on_click=self.notebook.run_next_cell, use_container_width=True, key="button_run_next_cell")
            st.button("⏩ Run all cells", on_click=self.notebook.run_all_cells, use_container_width=True, key="button_run_all_cells")
            st.button("🔄​ Restart session", on_click=self.notebook.restart_session, use_container_width=True, key="button_restart_session")
            st.button("🗑️​ Clear all cells", on_click=self.notebook.clear_cells, use_container_width=True, key="button_clear_cells")

            st.divider()

            # App mode preview toggle (only if not locked)
            if not self.notebook.locked:
                def on_change():
                    self.notebook.app_mode = not self.notebook.app_mode
                st.toggle("App mode preview", value=self.notebook.app_mode, on_change=on_change, key="toggle_app_mode")

            def on_change():
                self.notebook.show_logo = not self.notebook.show_logo
            st.toggle("Show logo", value=self.notebook.show_logo, on_change=on_change, key="toggle_show_logo")

            st.divider()

            # Technical settings in popover
            self.settings_popover()

    def settings_popover(self) -> None:
        """Render the technical settings popover.

        Provides advanced configuration options:
            - Run cell on submit toggle
            - Display mode selection (all/last/none)
            - Stdout output toggle
            - Stderr output toggle
        """
        with st.popover("⚙️ Settings", use_container_width=True):
            def on_change():
                self.notebook.run_on_submit = not self.notebook.run_on_submit
            st.toggle("Run cell on submit", value=self.notebook.run_on_submit, on_change=on_change, key="toggle_run_on_submit")

            def on_change():
                self.notebook.shell.display_mode = state.select_display_mode
            options = ['all', 'last', 'none']
            st.selectbox("Display mode", options=options, index=options.index(self.notebook.shell.display_mode), on_change=on_change, key="select_display_mode")

            def on_change():
                self.notebook.show_stdout = state.toggle_show_stdout
            st.toggle("Show stdout output", value=self.notebook.show_stdout, on_change=on_change, key="toggle_show_stdout")

            def on_change():
                self.notebook.show_stderr = state.toggle_show_stderr
            st.toggle("Show stderr output", value=self.notebook.show_stderr, on_change=on_change, key="toggle_show_stderr")

    def control_bar(self) -> None:
        """Render the new cell control bar.

        Displays three buttons for adding new cells:
            - New code cell
            - New Markdown cell
            - New HTML cell

        Note:
            Only shown in notebook mode (hidden in app mode).
        """
        if not self.notebook.app_mode:
            c1, c2, c3 = st.columns(3)

            code_button = c1.button("New code cell", use_container_width=True, key="new_code_cell_button")
            mkdwn_button = c2.button("New Markdown cell", use_container_width=True, key="new_mkdwn_cell_button")
            html_button = c3.button("New HTML cell", use_container_width=True, key="new_html_cell_button")

            if code_button:
                self.notebook.new_cell(type="code")
            if mkdwn_button:
                self.notebook.new_cell(type="markdown")
            if html_button:
                self.notebook.new_cell(type="html")

    def load_demo(self) -> None:
        """Render demo notebook selection dialog.

        Displays a selectbox with available demo notebooks from the package.
        When a demo is selected, it's loaded via :meth:`~streamlit_notebook.notebook.Notebook.open`.

        Provides user feedback via toast notifications for success and errors.
        """
        demo_folder = root_join("demo_notebooks")
        demos = [f for f in os.listdir(demo_folder) if f.endswith('.py')]

        def on_change():
            if state.demo_choice:
                filepath = os.path.join(demo_folder, state.demo_choice)
                try:
                    self.notebook.open(filepath)
                    self.notebook.notify(f"Loaded demo: {state.demo_choice}", icon="📚")
                except ValueError as e:
                    self.notebook.notify(str(e), icon="⚠️")
                except Exception as e:
                    self.notebook.notify(f"Failed to load demo: {str(e)}", icon="⚠️")

        st.selectbox("Choose a demo notebook.", options=demos, index=None, on_change=on_change, key="demo_choice")

    def save_notebook(self) -> None:
        """Render the save notebook button.

        Creates a button that saves the notebook to a ``.py`` file in the current
        working directory. The filename is based on the notebook title.

        Provides user feedback via toast notifications for success and errors.

        See Also:
            :meth:`~streamlit_notebook.notebook.Notebook.save`: Core save logic
        """
        def on_click():
            filename = f"{self.notebook.title}.py"
            filepath = os.path.join(os.getcwd(), filename)
            try:
                self.notebook.save(filepath)
                self.notebook.notify(f"Saved to {filepath}", icon="💾")
            except Exception as e:
                self.notebook.notify(f"Failed to save: {str(e)}", icon="⚠️")

        st.button("Save notebook", use_container_width=True, key="button_save_notebook", on_click=on_click)

    def open_notebook(self) -> None:
        """Render the open notebook dialog.

        Provides two ways to open notebooks:
            1. File uploader for drag-and-drop (unless locked)
            2. Selectbox for files in current working directory

        Only shows valid notebook ``.py`` files (validated via
        :meth:`~streamlit_notebook.notebook.Notebook.is_valid_notebook`).

        Provides user feedback via toast notifications for success and errors.

        See Also:
            :meth:`~streamlit_notebook.notebook.Notebook.open`: Core open logic
        """
        # File uploader for drag and drop (only if not locked)
        if not self.notebook.locked:
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
                    self.notebook.open(code)
                    self.notebook.notify(f"Opened notebook: {uploaded_file.name}", icon="📂")
                    # Close the open dialog
                    state.show_open_dialog = False
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
            return

        def on_change():
            if state.open_notebook_choice:
                filepath = os.path.join(cwd, state.open_notebook_choice)
                try:
                    self.notebook.open(filepath)
                    self.notebook.notify(f"Opened notebook: {state.open_notebook_choice}", icon="📂")
                    # Close the open dialog
                    state.show_open_dialog = False
                except ValueError as e:
                    self.notebook.notify(str(e), icon="⚠️")
                except Exception as e:
                    self.notebook.notify(f"Failed to open: {str(e)}", icon="⚠️")

        st.selectbox(
            "Or select from current directory",
            options=notebook_files,
            index=None,
            on_change=on_change,
            key="open_notebook_choice"
        )

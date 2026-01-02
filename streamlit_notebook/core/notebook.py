"""Notebook orchestration and management for Streamlit.

This module provides the core :class:`Notebook` class which orchestrates
the entire notebook experience, managing cells, execution, UI, and persistence.

The notebook supports two modes:
    - **Development mode**: Full interactive notebook with code editor
    - **App mode**: Locked, production-ready deployment without editor

Key Features:
    - Pure Python ``.py`` file format (version control friendly)
    - Cell-by-cell execution with persistent namespace
    - Selective reactivity control per cell
    - Fragment support for performance optimization
    - Built-in save/load functionality
    - Demo notebooks for quick start

Examples:
    Create and use a notebook::

        from streamlit_notebook import st_notebook
        import streamlit as st

        # Create notebook instance
        nb = st_notebook(title="My Notebook")

        # Define cells using decorator
        @nb.cell(type='code')
        def hello():
            st.write("Hello from a code cell!")

        # Render the notebook
        nb.render()

    Run in app mode (locked for deployment)::

        nb = st_notebook(title="Dashboard", app_mode=True)

See Also:
    :class:`~streamlit_notebook.cell.Cell`: Individual cell management
    :class:`~streamlit_notebook.shell.Shell`: Code execution engine
"""

from __future__ import annotations

from .cell import Cell
from .echo import echo
from .utils import format, root_join, state, state_key
from .display import display
from .rerun import rerun, check_rerun, wait
from pynteract import Shell
import streamlit as st
import os
from textwrap import dedent, indent
from typing import Any, Callable, Optional, Literal, Union, TYPE_CHECKING
import inspect
from modict import modict
from modict._collections_utils import MISSING

class Layout(modict):
    """Page layout configuration for the notebook.

    This class provides control over the Streamlit page configuration,
    replacing direct calls to st.set_page_config from notebook files.

    Attributes:
        width: Page layout width ("centered" or "wide" or 0-100 number). Defaults to "centered".
        initial_sidebar_state: Initial sidebar state ("auto", "expanded", or "collapsed").
            Defaults to "auto".
        menu_items: Dictionary of menu items to customize the hamburger menu.
            Can include "Get Help", "Report a bug", and "About" keys.
        horizontal: Display cells horizontally (code left, output right). Ideal for dashboards.
            Defaults to False. Note: In app_view mode, output takes full width regardless of split.
        vertical_split: Relative width percentage of left column in horizontal mode (0-100).
            50 means equal split. Defaults to 50. Ignored in app_view mode.

    Examples:
        Configure page layout::

            nb = Notebook(
                title="My Dashboard",
                layout=Layout(
                    width="wide",
                    horizontal=True,
                    vertical_split=40,  # 40% code, 60% output
                    initial_sidebar_state="collapsed"
                )
            )


    """
    _config=modict.config(
        extra='ignore',
        strict=False,
        enforce_json=True
    )
    width: Union[int,float,Literal["centered", "wide"]] = "centered"
    initial_sidebar_state: Literal["auto", "expanded", "collapsed"] = "auto"
    menu_items: Optional[dict[str, str]] = None
    horizontal: bool = False
    vertical_split: Union[int, float] = 50

class NotebookConfig(modict):

    """Configuration model for the notebook.

    This class provides parameters for the Notebook class

    Attributes:
        title: Title of the notebook. Defaults to "new_notebook".
        app_mode: Whether to run in app mode. Defaults to False.
        app_view: Whether to start in app view mode. Defaults to False.
        show_stdout: Whether to show stdout output. Defaults to True.
        show_stderr: Whether to show stderr output. Defaults to False.
        run_on_submit: Whether to run cells on submit. Defaults to True.
        show_logo: Whether to show the logo. Defaults to True.
        no_quit: Whether to disable the quit button. Defaults to False.
        layout: Page layout configuration (dict or Layout model)

    Example:
        Configure notebook settings::
        config = NotebookConfig(
            title="My Notebook",
            app_mode=True,
            no_quit=True,
            layout={
                'width': "wide",
                'horizontal': True
            }
        )
        nb = Notebook(**config)
    """

    _config=modict.config(
        extra='ignore',
        strict=False,
        enforce_json=True
    )
    title: str = "new_notebook"
    app_mode: bool = False
    app_view: bool = False
    show_stdout: bool = True
    show_stderr: bool = False
    run_on_submit: bool = True
    show_logo: bool = True
    no_quit: bool = False
    layout: Layout = modict.factory(Layout)

if TYPE_CHECKING:
    from .notebook_ui import NotebookUI

class Notebook:
    """Main notebook orchestrator managing cells, execution, and UI.

    This class is the central component of streamlit-notebook, coordinating
    all aspects of the notebook experience from cell management to execution
    to UI rendering.

    The notebook can operate in two modes:
        - **Edit mode** (``app_mode=False``): Interactive editing with full UI,
          can toggle to app view
        - **App mode** (``app_mode=True``): Locked in clean app view for production

    Attributes:
        title: The title of the notebook displayed in the UI.
        cells: List of :class:`Cell` objects in execution order.
        app_mode: If True, notebook is locked in app view (production mode).
        app_view: Current view state - True shows app view, False shows edit view.
        run_on_submit: Whether cells auto-execute on code changes.
        show_logo: Whether to display the streamlit-notebook logo.
        show_stdout: Whether to display stdout output from cells.
        show_stderr: Whether to display stderr output from cells.
        shell: The :class:`~streamlit_notebook.shell.Shell` instance for code execution.
        current_cell: The cell currently being executed (for output routing).
        ui: The :class:`~streamlit_notebook.notebook_ui.NotebookUI` instance for rendering.

    Examples:
        Create a notebook and define cells::

            nb = Notebook(title="My Analysis")

            @nb.cell(type='markdown')
            def intro():
                '''# Data Analysis
                Let's analyze some data.'''

            @nb.cell(type='code', reactive=True)
            def plot():
                import numpy as np
                import streamlit as st
                data = np.random.randn(100)
                st.line_chart(data)

            nb.render()

        Deploy as locked app::

            nb = Notebook(
                title="Production Dashboard",
                app_mode=True,
                show_logo=False
            )

    See Also:
        :func:`st_notebook`: Factory function for notebook creation
        :class:`~streamlit_notebook.cell.Cell`: Individual cell management
    """

    def __init__(
        self,
        title: str = "new_notebook",
        app_mode: bool = False,
        app_view:bool = False,
        run_on_submit: bool = True,
        show_logo: bool = True,
        show_stdout: bool = True,
        show_stderr: bool = False,
        layout: Optional[dict] = None,
        no_quit: bool = False
    ) -> None:
        """Initialize a new Notebook instance.

        Args:
            title: The notebook title displayed in the UI and used for filenames.
                Defaults to "new_notebook".
            app_mode: If True, locks the notebook in app view (production mode).
                Users cannot toggle back to edit mode. If False, starts in edit mode
                with a toggle to switch to app view. Defaults to False.
            run_on_submit: If True, cells execute immediately when code changes.
                If False, cells require manual execution via Run button.
                Defaults to True.
            show_logo: If True, displays the streamlit-notebook logo in the sidebar.
                Defaults to True.
            show_stdout: If True, displays stdout output from code cells.
                Defaults to True.
            show_stderr: If True, displays stderr output from code cells.
                Useful for debugging. Defaults to False.
            layout: Page layout configuration as a dict with layout parameters
                (e.g., ``{"width": "wide", "initial_sidebar_state": "collapsed"}``).
                If None, uses default centered layout. Defaults to None.
            no_quit: If True, disables the quit button and prevents programmatic
                shutdown via quit() method. Useful for cloud deployments where
                the server should not be terminated by users. Defaults to False.

        Note:
            The constructor automatically:
                - Patches ``st.echo``, ``st.rerun`` and ``st.stop`` to work within the notebook context
                - Creates a :class:`~streamlit_notebook.shell.Shell` instance
                - Initializes the execution namespace with ``st``, ``__notebook__``, and ``__agent__`` (if available)

        Examples:
            Development notebook (editable, can toggle to app view)::

                nb = Notebook(title="My Analysis")

            Production app (locked in app view, no editing)::

                nb = Notebook(
                    title="Dashboard",
                    app_mode=True,
                    show_logo=False
                )

            Debug mode (show stderr)::

                nb = Notebook(
                    title="Debug Session",
                    show_stderr=True
                )
        """

        if app_mode:
            app_view=True

        # Convert layout to Layout instance if needed (modict coercion + explicit defaults)
        if layout is None:
            layout = Layout()

        self.config=NotebookConfig(
            title=title,
            app_mode=app_mode,
            app_view=app_view,
            run_on_submit=run_on_submit,
            show_logo=show_logo,
            show_stdout=show_stdout,
            show_stderr=show_stderr,
            layout=layout,
            no_quit=no_quit
        )
        self.cells: list[Cell] = []
        self._current_cell: Optional[Cell] = None
        self.current_code: Optional[str] = None
        self.initialized = False
        self._layout_columns: Optional[tuple[Any, Any]] = None

        # Apply patches to Streamlit module
        self._apply_patches()

        self._init_shell()

        # Initialize UI component (imported here to avoid circular import)
        from .notebook_ui import NotebookUI
        self.ui: NotebookUI = NotebookUI(self)

    def _apply_patches(self) -> None:
        """Apply patches to Streamlit module for notebook integration (internal).

        This method patches several Streamlit functions to integrate properly with
        the notebook environment:

        1. **st.echo**: Patches to work with the notebook's code execution tracking
        2. **st.rerun**: Patches to use the notebook's rerun strategy with user guidance
        3. **st.stop**: Raises ``RuntimeError`` to stop cell execution

        The patched ``st`` module is also updated in ``sys.modules`` to ensure the
        interactive shell uses the patched version.

        Note:
            This is an internal method called during notebook initialization.
            The ``st.stop()`` patch raises a ``RuntimeError`` that the shell catches,
            stopping cell execution immediately and displaying an error message.

        See Also:
            :meth:`rerun`: Public rerun method
            :func:`~streamlit_notebook.utils.rerun`: Underlying rerun implementation
        """
        # Apply global patches (idempotent)
        from .utils import apply_global_patches
        apply_global_patches()

        # Patch st.echo to fit the notebook environment
        st.echo = echo(self._get_current_code).__call__

    def _init_shell(self) -> None:
        """Initialize or reinitialize the execution shell (internal).

        Creates a new :class:`~streamlit_notebook.shell.Shell` instance with
        hooks for stdout, stderr, display, exceptions, and input. Updates the
        shell namespace with Streamlit (``st``), the notebook instance (``__notebook__``),
        and the AI agent (``__agent__``) if one exists in session state.

        This method is called automatically during initialization.

        Note:
            This is an internal method. Use :meth:`restart_session` for public API.

        See Also:
            :meth:`restart_session`: Public method for full reset
            :class:`~streamlit_notebook.shell.Shell`: Execution engine documentation
        """
        self.shell = Shell(
            stdout_hook=self._stdout_hook,
            stderr_hook=self._stderr_hook,
            display_hook=self._display_hook,
            exception_hook=self._exception_hook,
            input_hook=self._input_hook
        )

        self.shell.update_namespace(
            st=st,
            __notebook__=self,
        )

        # Get agent from state if it exists
        agent = state.get(state_key("agent"), None)

        if agent is not None:
            agent.init_shell(self.shell)

    @property
    def current_cell(self) -> Optional[Cell]:
        """
        The cell currently executing code.

        This property is used in the shell hooks to know where to direct outputs of execution
        """
        return self._current_cell

    @current_cell.setter
    def current_cell(self, value: Optional[Cell]) -> None:
        self._current_cell = value

    def notify(self, message: str, icon: str = "ℹ️", delay: float = 1.0) -> None:
        """Show a toast notification with guaranteed visibility.

        This is a convenience method that combines ``st.toast()`` with :meth:`wait`
        to ensure notifications are visible to the user before any rerun.

        Args:
            message: The message to display in the toast.
            icon: The emoji icon to show. Defaults to "ℹ️".
            delay: How long to ensure the toast is visible (seconds). Defaults to 1.0.

        Examples:
            From a code cell using ``__notebook__``::

                __notebook__.notify("Saved successfully", icon="💾")
                __notebook__.notify("Error occurred", icon="⚠️", delay=2.0)

        See Also:
            :meth:`wait`: Request delay before pending rerun
            :meth:`rerun`: Trigger a rerun
        """
        st.toast(message, icon=icon)
        self.wait(delay)

    def _input_hook(self, code: str, ctx:str) -> None:
        """Shell hook called whenever code is inputted (internal).

        Args:
            code: The inputted code.
        """
        self.current_code = code

    def _get_current_code(self) -> Optional[str]:
        """Get the code being currently executed (internal).

        Returns:
            The current code being executed.
        """
        return self.current_code

    def _stdout_hook(self, data: str, buffer: str, ctx:str) -> None:
        """Shell hook called whenever the shell writes to stdout (internal).

        Args:
            data: The data being written to stdout.
            buffer: The current content of the stdout buffer.
        """
        current_cell=self.current_cell
        if current_cell and self.config.show_stdout and current_cell.ready:
            with current_cell.stdout_area:
                if buffer:
                    st.code(buffer, language="text")

    def _stderr_hook(self, data: str, buffer: str, ctx:str) -> None:
        """Shell hook called whenever the shell writes to stderr (internal).

        Args:
            data: The data being written to stderr.
            buffer: The current content of the stderr buffer.
        """
        current_cell=self.current_cell
        if current_cell and self.config.show_stderr and current_cell.ready:
            with current_cell.stderr_area:
                if buffer:
                    st.code(buffer, language="text")

    def _display_hook(self, result: Any, kwargs: dict, ctx:str) -> None:
        """Shell hook called whenever the shell displays a result (internal).

        Args:
            result: The result to be displayed.
            backend: Optional display backend to use (e.g., 'json', 'dataframe').
                If None, uses the default 'write' backend.
            **kwargs: Additional display options to pass to the backend
                (e.g., height=400, width='stretch').
        """
        current_cell=self.current_cell
        backend=kwargs.pop('backend','write')
        if current_cell:
            # Store result in results list (for backward compatibility)
            current_cell.results.append(result)
            # Store complete display info including result, backend, and options
            current_cell.displays.append({"result": result, "backend": backend, **kwargs})
            if current_cell.ready:
                with current_cell.display_area:
                    display(result, backend=backend, **kwargs)

    def _exception_hook(self, exception: Exception, ctx:str) -> None:
        """Shell hook called whenever the shell catches an exception (internal).

        Args:
            exception: The caught exception.
        """
        current_cell=self.current_cell
        if current_cell and current_cell.ready:
            with current_cell.exception_area:
                formatted_traceback = f"**{type(exception).__name__}**: {str(exception)}\n```\n{exception.enriched_traceback_string}\n```"
                st.error(formatted_traceback)

    def _show(self) -> None:
        """Render the notebook's UI (internal).

        This method displays all components of the notebook including the logo,
        sidebar, cells, and control bar. Delegates to the NotebookUI component.

        Note:
            This is an internal method. Use :meth:`render` for public API.
        """
        self.ui.show()

    def _render(self) -> None:
        """Main rendering method called in each Streamlit run (internal).

        Note:
            This resets cells' 'has_run' state AFTER show() to prevent duplicate
            execution. Streamlit callbacks fire at the beginning of the run, so
            resetting before would cause cells to run twice.
        """
        # Configure page layout from notebook config
        from .utils import original_set_page_config 

        width=self.config.layout.width

        draw_columns=isinstance(width,(int,float)) # considered 0-100% of width

        original_set_page_config(
            page_title="st.notebook",
            layout="wide" if draw_columns else width if width in ['wide','centered'] else "wide",
            initial_sidebar_state=self.config.layout.initial_sidebar_state,
            menu_items=self.config.layout.menu_items
        )

        self.initialized = True

        if draw_columns:
            width=min(max(width,1),99)
            _,c,_=st.columns([50-width/2,width,50-width/2])
            with c:
                self._show()
        else:
            self._show()

        # Though not very intuitive, resetting cells 'has_run' state AFTER show()
        # instead of before ensures that a cell isn't executed twice in the same run
        # Indeed, in Streamlit, callbacks triggered by UI events are fired AT THE VERY BEGINNING of the current run.
        # So if a callback caused a cell to run during this run, resetting 'has_run' before cells show in the for
        # loop would cause the cell to run AGAIN in the same run when we reach it in the loop.
        # Causing potential DuplicateWidgetID errors and other issues.
        self._reset_run_states()
        check_rerun()

    def render(self):
        """
        Renders the notebook currently stored in session state.

        This function should be used instead of calling nb._render() directly
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
            if state_key("notebook_script") not in state:
                # First run - capture the script
                if os.path.exists(caller_file):
                    with open(caller_file, 'r', encoding='utf-8') as f:
                        state[state_key("notebook_script")] = f.read()
                # Clear notebook on first bootstrap so exec creates it fresh
                notebook_key = state_key("notebook")
                if notebook_key in state:
                    del state[notebook_key]

            # Execute the notebook script
            exec_globals = globals().copy()
            exec_globals.update({
                '__name__': '__main__',
                '__file__': '<notebook_script>',
            })
            code_obj = compile(state[state_key("notebook_script")], '<notebook_script>', 'exec')
            exec(code_obj, exec_globals)
            return  # New script already rendered

        # Normal render
        if state_key("notebook") not in state:
            st.error("No notebook found in session state. Did you call st_notebook() first?")
            return

        state[state_key("notebook")]._render()

    def rerun(self, scope: str = "app", wait: bool | float = True, debug_msg: str = None) -> None:
        """Trigger a rerun of the notebook.

        This is the recommended way to trigger reruns in notebook cells,
        as it integrates with the notebook's rerun strategy using the
        ``wait()`` and ``check_rerun()`` helpers.

        Args:
            scope: Specifies what part of the app should rerun (Streamlit 1.52+):
                - ``"app"`` (default): Rerun the full app
                - ``"fragment"``: Only rerun the current fragment (must be called inside a fragment)
            wait: Controls the rerun behavior:
                - ``True`` (default): Soft rerun as soon as possible (equivalent to wait=0)
                - ``False``: Hard rerun immediately if possible, bypassing delays
                - ``float``: Wait for specified seconds before rerun (e.g., 1.5)

        Examples:
            From a code cell using ``__notebook__``::

                # Soft rerun as soon as possible
                __notebook__.rerun()

                # Fragment rerun (Streamlit 1.52+)
                __notebook__.rerun("fragment")

                # Delayed rerun (useful after showing toast)
                st.toast("Saved!", icon="💾")
                __notebook__.rerun(wait=1.5)

                # Force immediate hard rerun (if possible)
                __notebook__.rerun(wait=False)

            Or import directly::

                from streamlit_notebook import rerun
                rerun("fragment")  # Fragment rerun
                rerun(wait=1.0)    # App rerun with delay
                rerun(wait=False)  # Immediate rerun

        Note:
            Prefer this over ``st.rerun()`` to avoid disrupting the notebook's
            UI lifecycle and rerun strategy.

        See Also:
            :func:`~streamlit_notebook.utils.rerun`: Underlying implementation
            :meth:`wait`: Add delay without triggering rerun
        """
        rerun(scope=scope, wait=wait, debug_msg=debug_msg)

    def wait(self, delay: bool | float = True) -> None:
        """Request a delay before any pending rerun.

        Ensures that UI elements (like toasts) are visible for a specified
        duration before the next rerun occurs.

        Args:
            delay: Controls the delay behavior:
                - ``True`` or ``0`` (default): Does nothing (no additional delay)
                - ``False``: Executes any pending rerun immediately, ignoring previous delays
                - ``float``: Request additional delay (in seconds) before next rerun

        Examples:
            From a code cell using ``__notebook__``::

                # Show toast and ensure it's visible
                st.toast("Processing...", icon="⚙️")
                __notebook__.wait(2.0)

                # Execute pending rerun immediately
                __notebook__.wait(False)

            Or import directly::

                from streamlit_notebook import wait
                wait(1.5)
                wait(False)  # Execute now

        Note:
            This is automatically called by :meth:`notify` to ensure
            toast visibility.

        See Also:
            :func:`~streamlit_notebook.utils.wait`: Underlying implementation
            :meth:`rerun`: Trigger a rerun
            :meth:`notify`: Show toast with automatic wait
        """
        wait(delay)

    @staticmethod
    def is_valid_notebook(source: str) -> bool:
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
                with open(source, 'r', encoding='utf-8') as f:
                    code = f.read()
            else:
                # Treat as code string
                code = source

            # Validate it's a notebook file by checking for the signature
            return all(map(lambda x:x in code,['from streamlit_notebook import st_notebook']))

        except Exception:
            return False



    def clear_cells(self) -> None:
        """Delete all cells in the notebook.

        Removes all cells from the notebook, resetting it to an empty state.
        This is a public API method accessible from code cells.

        Provides user feedback via toast notification.

        Examples:
            From a code cell using ``__notebook__``::

                # Clear all cells programmatically
                __notebook__.clear_cells()
        """
        count = len(self.cells)
        self.cells = []
        self.notify(f"Cleared {count} cell{'s' if count != 1 else ''}", icon="🗑️")
        rerun(debug_msg="notebook.clear_cells()")


    def _reset_run_states(self) -> None:
        """Reset run states for all cells (internal).

        This method resets the has_run flag without deleting cells.

        Note:
            This is an internal method called during render cycle.
        """
        for cell in self.cells:
            cell.has_run = False

    def _reset_cells(self) -> None:
        """Reset all cells in the notebook (internal).

        This method clears the outputs and state of all cells without deleting them.

        Note:
            This is an internal method. Use :meth:`restart_session` for public API.
        """
        for cell in self.cells:
            cell.reset()

    def run_all_cells(self) -> None:
        """Run all cells in the notebook.

        Executes all cells that haven't been run yet in order, updating their outputs.
        This is a public API method accessible from code cells.

        Provides user feedback via toast notification.

        Examples:
            From a code cell using ``__notebook__``::

                # Run all cells programmatically
                __notebook__.run_all_cells()
        """
        count = 0
        for cell in list(self.cells):  # Convert to list to avoid modification during iteration
            if cell in self.cells and not cell.has_run_once:
                cell.run()
                count += 1

        if count > 0:
            self.notify(f"Executed {count} cell{'s' if count > 1 else ''}", icon="⏩")
        else:
            self.notify("All cells already executed", icon="✅")

    def run_next_cell(self) -> None:
        """Run the next unexecuted cell.

        Executes the first cell that hasn't been run yet.
        This is a public API method accessible from code cells.

        Provides user feedback via toast notification.

        Examples:
            From a code cell using ``__notebook__``::

                # Run next cell programmatically
                __notebook__.run_next_cell()
        """
        executed = False
        for cell in list(self.cells):
            if cell in self.cells and not cell.has_run_once:
                cell.run()
                executed = True
                self.notify(f"Executed `{cell.id}`", icon="▶️")
                break

        if not executed:
            self.notify("All cells have been executed", icon="✅")

    def restart_session(self) -> None:
        """Restart the Python session and reset all cells.

        This public method clears all cell outputs and reinitializes the
        execution environment, providing a fresh start.

        Provides user feedback via toast notification.
        """
        self._reset_cells()
        self._init_shell()
        self.notify("Session restarted", icon="🔄")
        rerun(debug_msg="notebook.restart_session()")

    def minimize_all(self) -> None:
        """Minimize all cells in the notebook.

        Sets all cells to minimized state, hiding their code editors.
        This is useful for focusing on outputs or presenting results.

        Provides user feedback via toast notification.

        Examples:
            From a code cell using ``__notebook__``::

                # Minimize all cells programmatically
                __notebook__.minimize_all()
        """
        for cell in self.cells:
            cell.minimized = True
        self.notify("All cells minimized", icon="🔽")
        rerun(debug_msg="notebook.minimize_all()")

    def expand_all(self) -> None:
        """Expand all cells in the notebook.

        Sets all cells to expanded state, showing their code editors.
        This is useful for reviewing or editing code.

        Provides user feedback via toast notification.

        Examples:
            From a code cell using ``__notebook__``::

                # Expand all cells programmatically
                __notebook__.expand_all()
        """
        for cell in self.cells:
            cell.minimized = False
        self.notify("All cells expanded", icon="🔼")
        rerun(debug_msg="notebook.expand_all()")

    def quit(self) -> None:
        """Quit the Streamlit server cleanly.

        This method performs cleanup operations and then terminates
        the Streamlit server process. It can be called from the UI
        or programmatically (e.g., by the AI agent).

        If no_quit is enabled (e.g., in cloud deployments), this method
        does nothing to prevent unauthorized server shutdown.

        The method will:
            1. Display a goodbye dialog with cleanup spinner
            2. Wait a brief moment for the dialog to render
            3. Terminate the server process with SIGTERM
        """
        # Don't allow quitting if no_quit is enabled
        if self.config.no_quit:
            return

        import streamlit as st
        import signal
        import time
        import os

        # Show goodbye dialog
        @st.dialog("👋 Goodbye!", width="small")
        def show_goodbye():
            # Centered goodbye message
            st.markdown(
                "<h3 style='text-align: center;'>Thank you for using Streamlit Notebook! 🎈</h3>",
                unsafe_allow_html=True
            )

            st.divider()

            # Centered spinner container
            with st.container(horizontal=True, horizontal_alignment='center'):
                st.space(size='stretch')
                spinner_zone = st.empty()
                st.space(size='stretch')
                with spinner_zone:
                    with st.spinner("Cleaning up...", width=140):
                        # Allow time for UI to display
                        time.sleep(3)
                    with st.spinner("Shutting down...", width=140):
                        # Allow time for UI to display
                        time.sleep(1)
                
            st.success("See you soon! ✨")
            time.sleep(0.5)

        # Display the dialog
        show_goodbye()

        # Kill the Streamlit server process
        pid = os.getpid()
        os.kill(pid, signal.SIGTERM)

    def get_cell(self, index_or_key: int | str) -> Optional[Cell]:
        """Find a cell by index or unique key.

        Retrieves a cell from the notebook using either its position (index)
        or its unique identifier (key). This is a public API method accessible
        from code cells.

        Args:
            index_or_key: Either the integer index (0-indexed position) or
                the 4-character string key of the cell.

        Returns:
            The corresponding cell, or None if not found.

        Raises:
            TypeError: If index_or_key is neither int nor str.

        Examples:
            From a code cell using ``__notebook__``::

            >>> # Get cell by index
            >>> cell = __notebook__.get_cell(0)
            >>> # Get cell by key
            >>> cell = __notebook__.get_cell("a1b2")
        """
        if isinstance(index_or_key, int):
            if index_or_key < len(self.cells):
                return self.cells[index_or_key]
            else:
                return None
        elif isinstance(index_or_key, str):
            for cell in self.cells:
                if cell.key == index_or_key:
                    return cell
            return None
        else:
            raise TypeError("index_or_key must be either int or str.")

    def _gen_cell_key(self) -> str:
        """Generate a unique key for a cell (internal).

        Returns:
            A unique string ID for the cell (4 characters).

        Note:
            This is an internal method used by :meth:`new_cell`.
        """
        from .utils import short_id
        # Generate unique short_id (collision is extremely unlikely but check anyway)
        while True:
            key = short_id(4)  # 4 chars should be plenty
            if not any(cell.key == key for cell in self.cells):
                return key

    def new_cell(
        self,
        type: Literal["code", "markdown", "html"] = "code",
        code: str = "",
        reactive: bool = False,
        fragment: bool = False,
        minimized: bool = False,
        run_every: Optional[Union[int, float]] = None,
        _rerun_after: bool = True
    ) -> Cell:
        """Add a new cell to the notebook.

        Creates a new cell of the specified type and appends it to the notebook.
        This is a public API method for programmatic cell creation from code cells.

        Args:
            type: The type of cell to create ("code", "markdown", or "html").
                Defaults to "code".
            code: Initial code or content for the cell. Defaults to empty string.
            reactive: If True, the cell will automatically re-run when changed.
                Defaults to False.
            fragment: If True, the cell will run as a Streamlit fragment.
                Defaults to False.
            minimized: If True, the cell code area will be minimized initially.
                Defaults to False.
            run_every: Auto-rerun interval in seconds (Streamlit 1.52+, requires fragment=True).
                None (default) disables auto-rerun. Can be int or float.

        Returns:
            The newly created cell object.

        Examples:
            From a code cell using ``__notebook__``::

                # Create a new code cell
                __notebook__.new_cell(type="code", code="import pandas as pd")

                # Create a markdown cell
                __notebook__.new_cell(type="markdown", code="# My Title")

                # Create auto-updating fragment cell
                __notebook__.new_cell(
                    type="code",
                    code="st.write(time.time())",
                    fragment=True,
                    run_every=1.0
                )
        """
        key = self._gen_cell_key()
        cell = Cell(key, type=type, code=code, reactive=reactive, fragment=fragment, minimized=minimized, run_every=run_every)
        return self.add_cell(cell, _rerun_after=_rerun_after)

    def add_cell(self, cell: Cell, _rerun_after: bool = True) -> Cell:
        """Add an existing cell to the notebook."""
        cell.notebook=self
        self.cells.append(cell)
        if _rerun_after:
            rerun(debug_msg=f"cell added: {cell.id}")
        return cell
    
    def cell(self, type="code", reactive=False, fragment=False, minimized=False, run_every=None):
        """
        Returns a decorator that adds a new cell created from a function's source code.
        Allows programmatic creation of cells from code defined in functions.

        Example::

            @notebook.cell(type="markdown")
            def my_markdown_cell():
                '''
                # This is a markdown cell
                You can write **Markdown** here.
                '''

            @notebook.cell(fragment=True, run_every=1.0)
            def live_updates():
                st.write(f"Time: {time.time()}")

        Args:
            type (str): The type of cell to create ("code", "markdown", or "html").
            reactive (bool): If True, the cell will automatically re-run when changed.
            fragment (bool): If True, the cell will run as a Streamlit fragment.
            minimized (bool): If True, the cell code area will be minimized initially.
            run_every (int | float | None): Auto-rerun interval in seconds (requires fragment=True).

        Returns:
            function: A decorator that adds a new cell from the decorated function's code.
        """
        import inspect

        # Check if running directly (not via main.py's <notebook_script>)
        frame = inspect.currentframe()
        caller_globals = frame.f_back.f_globals if frame else {}
        caller_file = caller_globals.get('__file__', '<notebook_script>')

        skip=(caller_file != '<notebook_script>') or self.initialized

        def decorator(func):
            if skip:
                # do nothing
                return func
            import inspect
            if type in ("markdown","html"):
                # Extract docstring for markdown and html cells
                code=dedent(inspect.getdoc(func) or "")
            else:
                source=self._get_source(func)
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

            self.new_cell(type=type, code=code, reactive=reactive, fragment=fragment, minimized=minimized, run_every=run_every, _rerun_after=False)
            return func
        return decorator
    
    def _get_source(self, func: Callable) -> str:
        """Extract source code from a function for @cell decorator (internal).

        The @cell decorator is only intended for use in Python script files,
        not for interactive shell usage.

        Args:
            func: The function from which to extract the source code.

        Returns:
            The source code of the function.

        Raises:
            ValueError: If the function is not defined in a valid context.

        Note:
            This is an internal method used by the :meth:`cell` decorator.
        """
        import ast

        # Get the filename where the function was defined
        filename = func.__code__.co_filename

        # Retrieve source code based on filename
        if filename == '<notebook_script>':
            # Function defined in the notebook script executed by main.py
            if state_key("notebook_script") in state:
                code = state[state_key("notebook_script")]
            else:
                raise ValueError(
                    f"Cannot retrieve source for function '{func.__name__}': "
                    "notebook_script not found in session state"
                )
        elif os.path.exists(filename):
            # Real file - read it
            with open(filename, 'r', encoding='utf-8') as f:
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
    
    def _format_cell_content(self, cell: Cell) -> str:
        """Format a cell's content for the @cell decorator.

        Args:
            cell: The cell to format.

        Returns:
            Formatted cell function body as a string.
        """
        if cell.code.strip() == "":
            return "    pass"

        if cell.type in ("markdown", "html"):
            # Handle triple quotes properly for docstrings
            content = dedent(cell.code)
            if "'''" in content and '"""' not in content:
                # Use double quotes
                return indent(f'r"""\n{content}\n"""', "    ")
            elif '"""' in content and "'''" not in content:
                # Use single quotes
                return indent(f"r'''\n{content}\n'''", "    ")
            elif "'''" in content and '"""' in content:
                # Both present - escape double quotes
                content = content.replace('"""', r'\"\"\"')
                return indent(f'r"""\n{content}\n"""', "    ")
            else:
                # Neither present - use single quotes by default
                return indent(f"r'''\n{content}\n'''", "    ")
        else:
            # Code cell - indent the code
            return indent(dedent(cell.code), "    ")

    def _get_cell_params(self, cell: Cell) -> str:
        """Get non-default cell parameters as a formatted string.

        Args:
            cell: The cell to get parameters for.
        Returns:
            Comma-separated string of non-default parameters for @cell decorator.
        """
        from .cell import CellConfig
        default=CellConfig()

        diffed=default.diffed(cell.get_config()).exclude('code')

        result = []
        for k, v in diffed.items():
            result.append(f"{k}={repr(v)}")

        return ", ".join(result)

    def _get_notebook_params(self) -> str:
        """Get non-default notebook parameters as a formatted string.

        Returns:
            Comma-separated string of non-default parameters for st_notebook().
        """

        default=NotebookConfig()

        diffed=default.diffed(self.config)

        result = []
        for k, v in diffed.items():
            result.append(f"{k}={repr(v)}")

        return ", ".join(result)


    def _format_cells(self) -> str:
        """Format all cells as @cell decorator functions.

        Returns:
            Formatted string containing all cell definitions.
        """
        cell_defs = []
        for cell in self.cells:
            # Format decorator and function signature
            header = f"@nb.cell({self._get_cell_params(cell)})\ndef cell_{cell.index}():"
            # Get formatted cell content (already indented)
            content = self._format_cell_content(cell)
            # Combine header and content
            cell_def = f"{header}\n{content}\n"
            cell_defs.append(cell_def)
        return "\n".join(cell_defs)


    def to_python(self) -> str:
        """Convert the notebook to a Python script.

        The script recreates the notebook structure using the @cell decorator
        and can be run as a standard Streamlit app.

        Returns:
            A Python script representation of the notebook.
        """
        template = dedent("""\
            # Generated by Streamlit Notebook
            # Original notebook: {title}
            # This file can be run directly with: streamlit run <filename>

            from streamlit_notebook import st_notebook
            import streamlit as st

            nb = st_notebook({params})
            
            {cells}

            # Render the notebook
            nb.render()"""
        )

        return template.format(
            title=self.config.title,
            params=self._get_notebook_params(),
            cells=self._format_cells()
        )
    
    def open(self, source=None) -> None:
        """
        Opens a notebook from a .py file or code string, or creates a new notebook.

        The source can be either:
        - A filepath to a .py notebook file generated by save()
        - A string containing the notebook Python code directly
        - None to create a new empty notebook with default title "new_notebook"

        Works by storing the script in session_state, which will be executed
        by the main script on rerun.

        Args:
            source (str or None): Path to the .py notebook file, notebook code string,
                                  or None to create a new notebook. Defaults to None.

        Raises:
            ValueError: If the source is not a valid notebook Python file
            Exception: If there's an error reading the file or loading the notebook
        """

        # If no source provided, create a new notebook from template
        if source is None:
            from .templates import get_default_notebook_template
            code = get_default_notebook_template()
            self.notify("Created new notebook", icon="📄")
        else:
            # Validate it's a notebook file using the helper
            if not self.is_valid_notebook(source):
                raise ValueError("This doesn't appear to be a valid notebook Python file.")

            # Check if source is a file path or code string
            if os.path.isfile(source):
                with open(source, 'r', encoding='utf-8') as f:
                    code = f.read()
            else:
                # Treat as code string
                code = source

        # Store the notebook script in session state
        state[state_key("notebook_script")] = code

        # Clear current notebook from state so it gets recreated
        notebook_key = state_key("notebook")
        if notebook_key in state:
            del state[notebook_key]

        rerun(debug_msg=f"notebook.open()")
    
    def save(self, filepath=None) -> bool:
        """
        Saves the notebook as a Python script file.

        Args:
            filepath (str): The path where the Python script will be saved.
                            If None, saves to the current working directory with the notebook title.

        Returns:
            bool: True if the file was successfully saved to disk, False if blocked.
                  Note that the in-memory notebook_script is always updated regardless.

        Note:
            When running via 'streamlit run notebook.py' directly, saving to the
            initial notebook file is disabled to prevent Streamlit reload and session reset.
            The in-memory notebook_script is always updated.
            Use the st_notebook launcher for full save functionality.
        """

        current_script=self.to_python()

        # Always update the in-memory script
        state[state_key("notebook_script")] = current_script

        if filepath is None:
            filepath=os.path.join(os.getcwd(),f"{self.config.title}.py")

        filepath_abs = os.path.abspath(filepath)

        # Check if we're in launcher mode (safe to save anywhere)
        is_launcher_mode = os.getenv('ST_NOTEBOOK_LAUNCHER_MODE', '').lower() == 'true'

        # Check if trying to overwrite the forbidden path (initial notebook file in direct mode)
        forbidden_path = state.get(state_key("forbidden_save_path"))
        is_forbidden = (forbidden_path and filepath_abs == forbidden_path)

        if not is_launcher_mode and is_forbidden:
            self.notify(f"**Save to file disabled: would overwrite running script**\n"
                         "Use the `st_notebook` launcher for full save support.", icon="⚠️", delay=5)
            return False

        # Safe to save to file
        with open(filepath,'w', encoding='utf-8') as f:
            f.write(current_script)

        rerun(debug_msg="notebook.save()")

        return True
            


    def delete_cell(self, index_or_key: int|str) -> None:
        """Delete a cell by its unique key.

        Removes a cell from the notebook given its unique identifier.
        This is a public API method accessible from code cells.

        Args:
            index_or_key: index or unique 4-character key identifier of the cell to delete.

        Examples:
            From a code cell using ``__notebook__``::

                # Delete a cell by key
                __notebook__.delete_cell("a1b2")
        """
        cell=self.get_cell(index_or_key)
        if cell:
            cell.delete()

    def get_info(self, minimal: bool = False) -> dict:
        """Get comprehensive notebook information including settings and cell states.

        Returns a dictionary containing all notebook metadata and cell information.
        By default includes complete execution outputs and metadata, designed to be
        easily serialized to JSON for AI agents or external tools.

        Args:
            minimal: If False (default), includes execution outputs, stdout,
                stderr, exceptions, and runtime metadata for each cell.
                If True, returns only the minimal cell definitions needed
                to recreate cells.

        Returns:
            A dictionary containing:
                - **config**: Notebook metadata (title, settings, configuration)
                - **cells**: List of cell dictionaries (one per cell)

        Examples:
            Get complete notebook context for AI agent::

                import json
                nb = __notebook__

                # Get full info and serialize to JSON
                info = nb.get_info()
                context = json.dumps(info, indent=2)

                # Pass context to AI agent
                # agent.chat(context)

            Inspect notebook configuration::

                info = nb.get_info()
                print(f"Notebook: {info['config']['title']}")
                print(f"Cells: {info['config']['cell_count']}")
                print(f"App mode: {info['config']['app_mode']}")

            Get minimal cell definitions::

                info = nb.get_info(minimal=True)
                cells = info['cells']
                # [{'key': 'abc1', 'type': 'code', 'code': '...', ...}, ...]

        See Also:
            :meth:`Cell.to_dict`: Individual cell serialization
        """
        return {
            "config":self.config.to_dict(),
            "initialized": self.initialized,
            "cell_count": len(self.cells),
            "cells": [cell.to_dict(minimal=minimal) for cell in self.cells]
        }
    
def get_notebook() -> Notebook | None:
    """
    Returns the current notebook instance from Streamlit's session state (if any).
    """
    return state.get(state_key("notebook"), None)

def st_notebook(
    title: str = "new_notebook",
    app_mode: bool = False,
    app_view: bool= False,
    run_on_submit: bool = True,
    show_logo: bool = True,
    show_stdout: bool = True,
    show_stderr: bool = False,
    no_quit: bool = False,
    layout: Optional[dict] = None,

) -> Notebook:
    """Get or create a notebook instance with session state management.

    This is the main factory function for creating notebooks. It manages notebook
    instances in Streamlit's session state, ensuring singleton behavior and proper
    parameter updates.

    The function automatically detects deployment mode via:
        - ``--app`` command-line flag
        - ``ST_NOTEBOOK_APP_MODE`` environment variable
        - ``--no-quit`` command-line flag
        - ``ST_NOTEBOOK_NO_QUIT`` environment variable

    When either is detected, it sets ``app_mode=True`` and/or ``no_quit=True`` for 
    production deployment.

    Args:
        title: The notebook title displayed in the UI and used for filenames.
            Defaults to "new_notebook".
        app_mode: If True, locks notebook in app view (production mode).
            If False, starts in edit mode with toggle to app view.
            Overridden to True if ``--app`` flag or env var is set.
            Defaults to False.
        app_view: If True, shows notebook in app view (production mode).
            can be toggled only if not in app_mode. Defaults to False.
        run_on_submit: If True, cells execute immediately when code changes.
            Defaults to True.
        show_logo: If True, displays the streamlit-notebook logo. Defaults to True.
        show_stdout: If True, displays stdout output from cells. Defaults to True.
        show_stderr: If True, displays stderr output from cells. Defaults to False.
        layout: Page layout configuration as a dict with layout parameters
            (e.g., ``{"width": "wide", "initial_sidebar_state": "collapsed"}``).
            If None, uses default centered layout. Defaults to None.
        no_quit: If True, hides the quit button to prevent the user from stopping the server
            Defaults to False.

    Returns:
        The :class:`Notebook` instance from session state, created if it doesn't exist
        or recreated if parameters don't match the existing notebook.

    Note:
        If a notebook already exists and is initialized (has cells), changing parameters
        won't recreate it. Parameters only apply when creating a fresh notebook.
        This happens at startup or when another notebook is opened from the interface.

    Examples:
        Basic notebook creation (editable)::

            from streamlit_notebook import st_notebook

            nb = st_notebook(title="My Notebook")

            @nb.cell(type='code')
            def hello():
                import streamlit as st
                st.write("Hello!")

            nb.render()

        Production deployment (locked in app view)::

            # Run with: st_notebook my_app.py -- --app
            # or set: ST_NOTEBOOK_APP_MODE=true

            nb = st_notebook(title="Dashboard")
            # Automatically becomes app_mode=True

        Or explicitly::

            nb = st_notebook(title="Dashboard", app_mode=True)

        Debug mode::

            nb = st_notebook(
                title="Debug Session",
                show_stderr=True,
                run_on_submit=False  # Manual execution for debugging
            )

        Custom layout::

            from streamlit_notebook import st_notebook

            nb = st_notebook(
                title="Dashboard",
                layout={"width": "wide", "initial_sidebar_state": "collapsed"}
            )

    See Also:
        :class:`Notebook`: The notebook class documentation
        :class:`Layout`: Page layout configuration
        :meth:`Notebook.render`: Render the notebook UI
    """
    import sys

    # If --app flag is present in CLI arguments, set the environment variable
    # This ensures consistent behavior whether using 'st_notebook' or 'streamlit run'
    if '--app' in sys.argv:
        os.environ['ST_NOTEBOOK_APP_MODE'] = 'true'

    # If --no-quit flag is present in CLI arguments, set the environment variable
    if '--no-quit' in sys.argv:
        os.environ['ST_NOTEBOOK_NO_QUIT'] = 'true'

    # Check ST_NOTEBOOK_APP_MODE environment variable to enforce locked app mode
    # This overrides the script's app_mode parameter
    if os.getenv('ST_NOTEBOOK_APP_MODE', '').lower() == 'true':
        app_mode = True

    # Check ST_NOTEBOOK_NO_QUIT environment variable to disable quit button
    # This overrides the script's no_quit parameter
    if os.getenv('ST_NOTEBOOK_NO_QUIT', '').lower() == 'true':
        no_quit = True

    # Check if we need to create or recreate the notebook
    should_create = False

    # Convert layout to Layout instance if needed (modict coercion + explicit defaults)

    layout = Layout(**(layout or {}))
                    
    config=NotebookConfig(
        title=title,
        app_mode=app_mode,
        app_view=app_view,
        run_on_submit=run_on_submit,
        show_logo=show_logo,
        show_stdout=show_stdout,
        show_stderr=show_stderr,
        no_quit=no_quit,
        layout=layout
    )

    if state_key("notebook") not in state:
        should_create = True
        reason="No notebook in state"

        # Store the forbidden filepath on first creation (for direct mode protection)
        # This is the path that would trigger Streamlit reload if overwritten
        if state_key("forbidden_save_path") not in state:
            # Try to get the actual running script path
            import inspect
            frame = inspect.currentframe()
            caller_globals = frame.f_back.f_globals if frame else {}
            caller_file = caller_globals.get('__file__', None)

            # If called from a real file (not <notebook_script>), use that path
            if caller_file and caller_file != '<notebook_script>' and os.path.exists(caller_file):
                state[state_key("forbidden_save_path")] = os.path.abspath(caller_file)
            else:
                # Fallback: use the default path based on title
                state[state_key("forbidden_save_path")] = os.path.abspath(os.path.join(os.getcwd(), f"{title}.py"))
    else:
        # Check if parameters match the existing notebook
        # Only recreate if parameters don't match AND the notebook is not yet initialized
        # (initialized means it went through the exec pass and created cells)
        nb = state[state_key("notebook")]
        should_create= (not nb.initialized and not nb.config.deep_equals(config))
        if should_create:
            reason="Not initialized and config changed"

    if should_create:
        #print("Instance renewed:",reason)
        state[state_key("notebook")] = Notebook(**config)

    return state[state_key("notebook")]

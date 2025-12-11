"""Utility functions for streamlit_notebook.

This module provides core utility functions for state management, UI feedback,
code formatting, and path handling within the streamlit_notebook package.

Key Features:
    - Session state management (init_state, update_state)
    - Smart rerun control with delays (rerun, wait, check_rerun)
    - Template string formatting with <<expression>> syntax
    - Unique ID generation
    - Package path utilities

Examples:
    Basic usage::

        from streamlit_notebook.utils import rerun, wait, format

        # Smart rerun with delay
        st.toast("Saved!")
        rerun(wait=1.5)  # Ensures toast is visible

        # Format strings with expressions
        formatted = format("Result: <<x + y>>", x=10, y=20)
        # Returns: "Result: 30"
"""

from __future__ import annotations

import re
import streamlit as st
from streamlit.errors import DuplicateWidgetID, StreamlitDuplicateElementKey
import random
import string
import os
from typing import Any
import inspect

def set_root_path(file):
    """Set the root package folder path from the given file's location."""
    os.environ['ROOT_PACKAGE_FOLDER'] = os.path.dirname(os.path.abspath(file))

def root_join(*args: str) -> str:
    """Join path components with the root package folder.

    This utility function constructs file paths relative to the package's root folder,
    which is automatically set to the directory containing this module.

    Args:
        *args: Path components to join.

    Returns:
        The joined absolute path string.

    Examples:
        Access package resources::

            # Get path to demo notebooks directory
            demo_path = root_join("demo_notebooks")

            # Get path to a specific image
            img_path = root_join("app_images", "logo.png")

    Note:
        The root package folder is stored in the ``ROOT_PACKAGE_FOLDER``
        environment variable and points to the ``streamlit_notebook`` directory.
    """
    return os.path.join(os.getenv('ROOT_PACKAGE_FOLDER'), *args)

# shortcut for st.session_state
state=st.session_state

def short_id(length: int = 16) -> str:
    """Generate a random unique identifier string.

    Creates a random string of ASCII letters (both uppercase and lowercase)
    of the specified length. Useful for generating unique keys for UI elements.

    Args:
        length: The length of the ID to generate. Defaults to 16.

    Returns:
        A random string of the specified length containing only ASCII letters.

    Examples:
        Generate default 16-character ID::

            id1 = short_id()
            # Returns something like: "aBcDeFgHiJkLmNoP"

        Generate shorter ID::

            id2 = short_id(8)
            # Returns something like: "XyZaBcDe"

    Note:
        This uses :func:`random.choices` which is not cryptographically secure.
        Do not use for security-sensitive purposes like passwords or tokens.
    """
    return ''.join(random.choices(string.ascii_letters, k=length))

def init_state(**kwargs: Any) -> None:
    """Initialize session state variables if they don't exist.

    Sets initial values in ``st.session_state`` for the provided keys,
    but only if those keys haven't been set already. Useful for initializing
    state on first run without overwriting existing values.

    Args:
        **kwargs: Keyword arguments where keys are state variable names
            and values are their initial values.

    Examples:
        Initialize state on first run::

            init_state(
                counter=0,
                user_name="Guest",
                items=[]
            )

            # On first run: sets all values
            # On subsequent runs: preserves existing values

    See Also:
        :func:`update_state`: Update state unconditionally
    """
    for key, value in kwargs.items():
        if key not in state:
            state[key] = value

def update_state(**kwargs: Any) -> None:
    """Update session state variables unconditionally.

    Updates values in ``st.session_state`` with the provided key-value pairs,
    overwriting any existing values. Use this when you want to force-update state.

    Args:
        **kwargs: Keyword arguments where keys are state variable names
            and values are their new values.

    Examples:
        Force update state values::

            update_state(
                counter=counter + 1,
                last_action="submit",
                timestamp=time.time()
            )

    See Also:
        :func:`init_state`: Initialize state only if not exists
    """
    for key, value in kwargs.items():
        state[key] = value

def original_rerun(*args,**kwargs) -> None:
    """Get the original st.rerun function before patching."""
    if hasattr(st.rerun, '_patched'):
        return st.rerun._original(*args,**kwargs)
    else:
        return st.rerun(*args,**kwargs)

def rerun(wait: bool | float = True) -> None:
    """Command a rerun of the app with optional wait control.

    This function sets a flag in the session state to trigger a rerun
    of the Streamlit app after the current execution is complete.

    When called multiple times during the same run, intelligently merges
    the requests to ensure the longest total delay is respected.

    Args:
        wait: Controls the rerun behavior:
            - ``True`` (default): Soft rerun as soon as possible (equivalent to wait=0)
            - ``False``: Hard rerun immediately if possible, bypassing delays
            - ``float``: Wait for specified seconds before rerun (e.g., 1.5)

    Note:
        - Multiple calls to :func:`rerun` during the same execution will merge
          intelligently - the longest total delay will be respected.
        - When ``wait=False``, all pending delayed reruns are cleared and an
          immediate rerun is attempted.

    Examples:
        Soft rerun as soon as possible::

            rerun()  # or rerun(wait=True)

        Ensure toast is visible before rerun::

            st.toast("File saved!", icon="💾")
            rerun(wait=1.5)

        Wait for animation to complete::

            with st.spinner("Processing..."):
                process_data()
            rerun(wait=0.5)  # Let spinner disappear gracefully

        Multiple calls - longest delay wins::

            st.toast("Action 1")
            rerun(wait=1.0)
            st.toast("Action 2")
            rerun(wait=2.0)  # This will execute at 2.0s from now

        Immediate hard rerun (useful in callbacks)::

            st.button("Click me", on_click=lambda: rerun(wait=False))

    See Also:
        :func:`wait`: Request delay without triggering rerun
        :func:`check_rerun`: Execute pending reruns
    """

    # Handle wait=False (immediate hard rerun)
    if wait is False:
        # Execute immediately without waiting for current execution
        # This clears any pending delayed reruns and triggers an immediate rerun
        try:
            state.rerun = None  # Clear any pending rerun
            original_rerun()  # Trigger immediate rerun
        except Exception:
            # st.rerun() raises an exception when called from within a callback context
            # In this case, fall back to soft rerun with zero delay
            rerun(wait=True)
        return

    # Convert wait to delay value
    if wait is True:
        delay = 0.0
    else:
        delay = float(wait)

    import time
    current_time = time.time()

    # If there's already a pending delay or rerun, merge intelligently
    if 'rerun' in state and state.rerun:
        existing = state.rerun
        existing_requested_at = existing.get('requested_at', current_time)
        existing_delay = existing.get('delay', 0)

        # Calculate when the existing would execute
        existing_execute_at = existing_requested_at + existing_delay

        # Calculate when this new rerun would execute
        new_execute_at = current_time + delay

        # Use whichever execution time is later (longest total delay)
        if new_execute_at > existing_execute_at:
            # New request requires longer wait - update to new timestamp and delay
            state.rerun = {
                'requested_at': current_time,
                'delay': delay,
                'requested': True
            }
        else:
            # Existing delay already waits long enough
            # Keep the existing delay but mark as requested
            elapsed = current_time - existing_requested_at
            state.rerun = {
                'requested_at': current_time,
                'delay': max(0, existing_delay - elapsed),
                'requested': True
            }
    else:
        # First request
        state.rerun = {
            'requested_at': current_time,
            'delay': delay,
            'requested': True
        }

def wait(delay: bool | float = True) -> None:
    """Request a minimum delay before any future rerun, without triggering one.

    This function sets a delay requirement that will be honored by any subsequent
    :func:`rerun` call. Unlike :func:`rerun`, this does not trigger a rerun itself.

    Useful when you want to ensure temporal space (e.g., for toasts/animations)
    without causing a rerun yourself.

    Args:
        delay: Controls the delay behavior:
            - ``True`` or ``0`` (default): Does nothing (no additional delay)
            - ``False``: Executes any pending rerun immediately, ignoring previous delays
            - ``float``: Request additional delay (in seconds) before next rerun

    Note:
        Multiple calls to :func:`wait` will use the longest delay.
        The delay is only enforced when :func:`rerun` is eventually called.

    Examples:
        Request delay, someone else will trigger rerun::

            st.toast("Processing complete", icon="✅")
            wait(1.5)  # Ensures toast is visible
            # ... later, someone calls rerun() which will honor the 1.5s delay

        Ensure animation completes::

            st.balloons()
            wait(2.0)  # Balloons get full duration before any rerun

        Execute pending rerun immediately::

            wait(False)  # If a rerun was pending, execute it now

    See Also:
        :func:`rerun`: Trigger a rerun with delay
        :func:`check_rerun`: Execute pending reruns
    """
    # Handle wait(False) - execute pending rerun immediately
    if delay is False:
        if 'rerun' in state and state.rerun:
            existing_requested = state.rerun.get('requested', False)
            if existing_requested:
                # There's a pending rerun - execute it immediately
                state.rerun = None
                original_rerun()
        return

    # Handle wait(True) or wait(0) - do nothing
    if delay is True or delay == 0:
        return

    # Handle numeric delay
    import time
    current_time = time.time()
    delay = float(delay)

    # Check if there's already a delay or rerun request
    if 'rerun' in state and state.rerun:
        existing = state.rerun
        existing_requested_at = existing.get('requested_at', current_time)
        existing_delay = existing.get('delay', 0)
        existing_requested = existing.get('requested', False)

        # Calculate when the existing would execute
        existing_execute_at = existing_requested_at + existing_delay

        # Calculate when we want it to execute (at least delay from now)
        desired_execute_at = current_time + delay

        # If our desired delay is longer, update it
        if desired_execute_at > existing_execute_at:
            state.rerun = {
                'requested_at': current_time,
                'delay': delay,
                'requested': existing_requested  # Preserve requested flag
            }
        else:
            # Keep existing but update timestamp
            elapsed = current_time - existing_requested_at
            state.rerun = {
                'requested_at': current_time,
                'delay': max(0, existing_delay - elapsed),
                'requested': existing_requested
            }
    else:
        # First delay request - create entry with requested=False
        state.rerun = {
            'requested_at': current_time,
            'delay': delay,
            'requested': False
        }

def check_rerun() -> None:
    """Check for pending reruns and execute them with delays.

    This function should be placed as the last command in a Streamlit main script.
    It checks for the rerun flag and triggers a rerun if it's set (requested=True),
    waiting for the requested delay if necessary.

    If only :func:`wait` was called (requested=False), no rerun occurs - the delay
    requirement is just stored for any future :func:`rerun` call.

    Note:
        This function is typically called automatically at the end of notebook
        execution. You rarely need to call it manually.

    Examples:
        Typical usage at the end of a Streamlit script::

            # Your Streamlit app code here
            st.config.title("My App")
            # ...

            # Check and execute any pending reruns
            check_rerun()

    See Also:
        :func:`rerun`: Command a rerun with delay
        :func:`wait`: Request delay without rerun
    """
    import time
    if 'rerun' in state and state.rerun:
        rerun_info = state.rerun
        requested = rerun_info.get('requested', False)

        # Only execute rerun if it was actually requested (not just a delay)
        if requested:
            requested_at = rerun_info.get('requested_at', 0)
            delay_time = rerun_info.get('delay', 0)

            # Calculate elapsed time since rerun was requested
            elapsed = time.time() - requested_at

            # Wait for remaining delay if needed
            remaining_delay = delay_time - elapsed
            if remaining_delay > 0:
                time.sleep(remaining_delay)

            # Clear the rerun flag and execute rerun
            state.rerun = None
            original_rerun()

def format(string: str, **kwargs: Any) -> str:
    """Format string by evaluating <<expression>> tags.

    This function finds all occurrences of ``<<...>>`` in the string and evaluates
    the expressions within them using the provided keyword arguments as context.

    Args:
        string: The input string containing ``<<...>>`` tags.
        **kwargs: Keyword arguments used as the context namespace for evaluating expressions.

    Returns:
        The formatted string with all ``<<...>>`` tags replaced by their evaluated results.
        If an expression fails to evaluate, the original ``<<expression>>`` is preserved.

    Examples:
        Basic expression evaluation::

            result = format("Result: <<x + y>>", x=10, y=20)
            # Returns: "Result: 30"

        Multiple expressions::

            text = format("Hello <<name>>, you are <<age>> years old", name="Alice", age=25)
            # Returns: "Hello Alice, you are 25 years old"

        With error handling::

            result = format("Value: <<undefined_var>>", x=5)
            # Returns: "Value: <<undefined_var>>" (original preserved)

    Note:
        Expressions are evaluated using Python's ``eval()`` function.
        Only use this with trusted input as it can execute arbitrary code.
    """
    if not kwargs:
        context: dict[str, Any] = {}
    else:
        context = kwargs
    def replace_expr(match: re.Match[str]) -> str:
        expr = match.group(1)
        try:
            return str(eval(expr, context))
        except Exception as e:
            return '<<' + expr + '>>'
    return re.sub(r'<<(.*?)>>', replace_expr, string)

def display(obj: Any, backend: str | None = None, **kwargs) -> None:
    """Display an object using Streamlit's rendering system.

    Attempts to display the object using the specified backend, falling back to
    ``st.write`` and finally ``st.text(repr(obj))`` if those fail. Used internally
    for displaying cell execution results.

    Args:
        obj: The object to display. If None, nothing is displayed.
        backend: The Streamlit display backend to use. Defaults to 'write'.
            Can be any Streamlit display function name (without the 'st.' prefix):

            - 'write': ``st.write()`` - smart auto-rendering (default)
            - 'json': ``st.json()`` - JSON viewer for dicts/lists
            - 'code': ``st.code()`` - syntax-highlighted code display
            - 'text': ``st.text()`` - plain text display
            - 'markdown': ``st.markdown()`` - markdown rendering
            - 'dataframe': ``st.dataframe()`` - interactive dataframe
            - 'table': ``st.table()`` - static table display
            - Or any other ``st.*`` display function
        **kwargs: Additional keyword arguments to pass to the backend function.
            For example: ``height=400``, ``width='stretch'``, etc.

    Note:
        This is the default display hook for cells. Custom display behavior
        can be implemented via the notebook's display_hook.

    Examples:
        Basic usage with default backend::

            result = 42
            display(result)  # Uses st.write by default

        With specific backend::

            data = {'a': 1, 'b': 2}
            display(data, backend='json')  # Uses st.json

        With backend options::

            df = pd.DataFrame({'a': [1, 2, 3]})
            display(df, backend='dataframe', height=400, width='stretch')

        Use any Streamlit function::

            display(data, backend='plotly_chart', width='stretch')

    See Also:
        :meth:`~streamlit_notebook.notebook.Notebook.display_hook`: Custom display
    """
    if obj is None:
        return

    # Default to 'write' if no backend specified
    if backend is None:
        backend = 'write'

    # Try the requested backend first using getattr
    display_func = getattr(st, backend, None)
    if display_func and callable(display_func):
        try:
            display_func(obj, **kwargs)
            return
        except (DuplicateWidgetID, StreamlitDuplicateElementKey):
            # Silently skip duplicate display calls (can happen when cell runs multiple times in same turn)
            return
        except Exception as e:
            st.warning(f"Failed to display with {backend} backend: {str(e)}")
            pass  # Fall through to fallback

    # Fallback to st.write if requested backend failed or doesn't exist
    if backend != 'write':
        try:
            st.write(obj)
            return
        except (DuplicateWidgetID, StreamlitDuplicateElementKey):
            # Silently skip duplicate display calls
            return
        except Exception as e:
            st.warning(f"Failed to display with write backend: {str(e)}")
            pass  # Fall through to final fallback

    # Final fallback: plain text representation
    try:
        st.text(repr(obj))
    except (DuplicateWidgetID, StreamlitDuplicateElementKey):
        # Silently skip duplicate display calls
        pass
    except Exception:
        # If even repr fails, show error message
        st.error(f"Failed to display object of type {type(obj).__name__}")

def original_set_page_config(*args,**kwargs) -> None:
    """Get the original st.rerun function before patching."""
    if hasattr(st.set_page_config, '_patched'):
        return st.set_page_config._original(*args,**kwargs)
    else:
        return st.set_page_config(*args,**kwargs)

def set_page_config(*args: Any, **kwargs: Any) -> None:
    """No-op wrapper for st.set_page_config.

    This patched version of Streamlit's ``set_page_config`` is a no-op that
    prevents users from calling it directly from notebook files.

    Page configuration is now managed through the ``Notebook.config.layout``
    attribute instead. This ensures consistent page configuration and prevents
    conflicts.

    Args:
        *args: Ignored positional arguments.
        **kwargs: Ignored keyword arguments.

    Note:
        This function is automatically patched into Streamlit's API when the
        notebook module is imported. To configure the page layout, use the
        ``layout`` parameter when creating your notebook instead.

    Examples:
        Old (deprecated) usage::

            import streamlit as st
            from streamlit_notebook import st_notebook

            # This no longer works
            st.set_page_config(layout="wide")

            nb = st_notebook()

        New usage::

            from streamlit_notebook import st_notebook, Layout

            # Configure layout through the notebook
            nb = st_notebook(
                layout=Layout(
                    width="wide",
                    initial_sidebar_state="collapsed"
                )
            )

    See Also:
        :class:`~streamlit_notebook.core.notebook.Layout`: Layout configuration class
        :class:`~streamlit_notebook.core.notebook.NotebookConfig`: Notebook configuration
    """
    # No-op: page config is now managed by Notebook.config.layout
    pass
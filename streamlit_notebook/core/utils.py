"""Utility functions for streamlit_notebook.

This module provides core utility functions for state management, UI feedback,
code formatting, and path handling within the streamlit_notebook package.

Key Features:
    - Session state management (init_state, update_state)
    - Template string formatting with <<expression>> syntax
    - Unique ID generation
    - Package path utilities
"""

from __future__ import annotations

import re
import streamlit as st
import random
import string
import os
from typing import Any, Literal, Optional

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
STATE_PREFIX = "_streamlit_notebook_"

def state_key(key: str) -> str:
    if key.startswith(STATE_PREFIX):
        return key
    return f"{STATE_PREFIX}{key}"

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


def format(string: str, context: Optional[dict[str, Any]] = None) -> str:
    """Format string by evaluating <<expression>> tags.

    This function finds all occurrences of ``<<...>>`` in the string and evaluates
    the expressions within them using the provided context.

    Args:
        string: The input string containing ``<<...>>`` tags.
        context: dict of keyword arguments used as the context namespace for evaluating expressions.

    Returns:
        The formatted string with all ``<<...>>`` tags replaced by their evaluated results.
        If an expression fails to evaluate, the original ``<<expression>>`` is preserved.

    Examples:
        Basic expression evaluation::

            result = format("Result: <<x + y>>", context={'x': 10, 'y': 20})
            # Returns: "Result: 30"

        Multiple expressions::

            text = format("Hello <<name>>, you are <<age>> years old", context={'name': "Alice", 'age': 25})
            # Returns: "Hello Alice, you are 25 years old"

        With error handling::

            result = format("Value: <<undefined_var>>", context={'x': 5})
            # Returns: "Value: <<undefined_var>>" (original preserved)

    Note:
        Expressions are evaluated using Python's ``eval()`` function.
        Only use this with trusted input as it can execute arbitrary code.
    """

    context = context or {}
    def replace_expr(match: re.Match[str]) -> str:
        expr = match.group(1)
        try:
            return str(eval(expr, context))
        except Exception as e:
            return '<<' + expr + '>>'
    return re.sub(r'<<(.*?)>>', replace_expr, string)

def original_set_page_config(*args,**kwargs) -> None:
    """Get the original st.rerun function before patching."""
    if hasattr(st.set_page_config, '_patched'):
        return st.set_page_config._original(*args,**kwargs)
    else:
        return st.set_page_config(*args,**kwargs)

def set_page_config(*args: Any, **kwargs: Any) -> None:
    """No-op wrapper for st.set_page_config with deprecation warning.

    This patched version of Streamlit's ``set_page_config`` is a no-op that
    prevents users from calling it directly from notebook files and warns them
    about the proper way to configure page layout.

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

            # This no longer works - will show a warning
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
    # Show warning to guide users
    import warnings
    warnings.warn(
        "st.set_page_config() is not supported in streamlit_notebook. "
        "Use the 'layout' parameter when creating your notebook instead:\n\n"
        "  from streamlit_notebook import st_notebook, Layout\n"
        "  nb = st_notebook(\n"
        "      layout=Layout(\n"
        "          width='wide',  # or 'centered'\n"
        "          initial_sidebar_state='auto'  # or 'expanded', 'collapsed'\n"
        "      )\n"
        "  )\n\n"
        "This provides the same functionality as st.set_page_config().",
        DeprecationWarning,
        stacklevel=2
    )


def apply_global_patches() -> None:
    """Apply global patches to Streamlit functions.

    This function patches st.set_page_config, st.rerun, and st.stop to work
    properly within the notebook environment. These patches are global and
    should be applied once at startup.

    The patches are:
        - st.set_page_config: Made into a no-op (config managed by notebook)
        - st.rerun: Redirected to notebook's custom rerun with delays
        - st.stop: Raises RuntimeError to halt cell execution gracefully

    This function is idempotent - calling it multiple times has no effect
    beyond the first call.

    Note:
        This should be called as early as possible when a Streamlit context
        is available, but not from the CLI launcher process.

    See Also:
        :func:`set_page_config`: Patched version of st.set_page_config
        :func:`rerun`: Custom rerun with delay support
    """
    import sys

    # Patch st.set_page_config
    if not hasattr(st.set_page_config, '_patched'):
        set_page_config._patched = True
        set_page_config._original = st.set_page_config
        st.set_page_config = set_page_config
        sys.modules["streamlit"].set_page_config = set_page_config

    # Patch st.rerun
    from .rerun import rerun
    if not hasattr(st.rerun, '_patched'):
        def patched_rerun(scope: Literal['app','fragment']='app', wait: bool | float = True, debug_msg: str = None) -> None:
            """Patched st.rerun that implements the notebook's rerun method."""
            # Use our custom rerun instead
            # If no debug_msg provided, use a default one to identify st.rerun() calls
            if debug_msg is None:
                debug_msg = "st.rerun() called from user code"
            rerun(scope=scope, wait=wait, debug_msg=debug_msg)

        patched_rerun._patched = True
        patched_rerun._original = st.rerun
        st.rerun = patched_rerun
        sys.modules["streamlit"].rerun = patched_rerun

    # Patch st.stop
    if not hasattr(st.stop, '_patched'):
        def patched_stop():
            """Patched st.stop that raises RuntimeError to stop cell execution."""
            raise RuntimeError(
                "Cell execution has been stopped."
            )

        patched_stop._patched = True
        patched_stop._original = st.stop
        st.stop = patched_stop
        sys.modules["streamlit"].stop = patched_stop

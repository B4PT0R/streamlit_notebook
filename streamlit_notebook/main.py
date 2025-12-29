"""Main entry point for streamlit-notebook CLI.

This module provides the main Streamlit script that runs when launching
an empty notebook or loading a notebook file via the CLI.

It handles:
    - Creating default notebook templates
    - Loading notebook files from command line arguments
    - Executing notebook scripts in the proper context
    - Environment variable detection for app mode

The script is invoked via ``st_notebook`` command without arguments,
or internally when running notebooks through the launcher.

Examples:
    Launch empty notebook::

        $ st_notebook
        # Opens empty notebook in browser

    The script can also be called programmatically by the launcher
    to run specific notebook files.

See Also:
    :mod:`~streamlit_notebook.launch_app`: CLI launcher that calls this script
    :func:`~streamlit_notebook.notebook.st_notebook`: Notebook factory function
"""

from __future__ import annotations

import streamlit as st
import os
import sys
from core.utils import state_key
from core.templates import get_default_notebook_template

def main() -> None:
    """Main entry point for the notebook application.

    Initializes and runs the notebook application, handling:
        - Session state initialization for notebook script
        - Loading notebook files from command line arguments
        - Generating default empty notebook if no file provided
        - Executing notebook code in proper context with error handling

    The function uses a special ``<notebook_script>`` filename marker
    to enable proper source introspection for features like ``st.echo``.

    Note:
        This function is called automatically when running ``st_notebook``
        without arguments, or when the launcher needs to run an empty notebook.

    Examples:
        This function is not typically called directly. It runs when::

            $ st_notebook
            # Calls main() -> shows empty notebook

    See Also:
        :func:`get_default_notebook_template`: Default template generator
        :mod:`~streamlit_notebook.launch_app`: CLI launcher module
    """

    # Initialize notebook_script in session_state if not present
    notebook_script_key = state_key("notebook_script")
    if notebook_script_key not in st.session_state:
        # Check if a notebook file was passed via --file= argument
        filepath = None
        for arg in sys.argv[1:]:
            if arg.startswith('--file='):
                filepath = arg.split('=', 1)[1]
                break
            # Also support legacy format for backwards compatibility
            elif arg.endswith('.py') and not arg.startswith('-'):
                filepath = arg
                break

        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    st.session_state[notebook_script_key] = f.read()
            except Exception as e:
                st.error(f"Failed to load notebook: {str(e)}")
                st.session_state[notebook_script_key] = get_default_notebook_template()
        else:
            # No file provided, use default empty notebook template
            st.session_state[notebook_script_key] = get_default_notebook_template()

    # Execute the notebook script
    # Use special filename so get_source() can retrieve the script from session_state
    exec_globals = globals().copy()
    exec_globals.update({
        '__name__': '__main__',
        '__file__': '<notebook_script>',  # Special marker for get_source()
        'streamlit': st,
        'st': st,
    })
    try:
        # Compile with special filename
        code_obj = compile(st.session_state[notebook_script_key], '<notebook_script>', 'exec')
        exec(code_obj, exec_globals)
    except Exception as e:
        import traceback
        st.error(f"Error executing notebook: {str(e)}")
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()

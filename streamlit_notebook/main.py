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

def get_default_notebook_template() -> str:
    """Generate default empty notebook template code.

    Creates a minimal notebook script with environment-aware settings.
    Detects app mode via ``ST_NOTEBOOK_APP_MODE`` environment variable or
    ``--app`` command line flag and adjusts template accordingly.

    Returns:
        Python source code string for a new empty notebook with proper
        imports, configuration, and placeholder cells.

    Examples:
        The generated template looks like::

            from streamlit_notebook import st_notebook
            import streamlit as st

            st.set_page_config(page_title="new_notebook", ...)

            nb = st_notebook(title='new_notebook')

            # Add cells below using @nb.cell() decorator
            # @nb.cell(type='code')
            # def cell_0():
            #     st.write("Hello, World!")

            nb.render()

    Note:
        If app mode is detected, the template includes ``app_mode=True``
        and ``locked=True`` parameters for production deployment.
    """
    # Check for app mode via environment variable or --app flag
    app_mode = os.getenv('ST_NOTEBOOK_APP_MODE', '').lower() == 'true' or '--app' in sys.argv

    params = []
    params.append("title='new_notebook'")
    if app_mode:
        params.append("app_mode=True")
        params.append("locked=True")

    params_str = ", ".join(params)

    return f"""# Streamlit Notebook
# This is a self-contained notebook file

from streamlit_notebook import st_notebook
import streamlit as st

st.set_page_config(page_title="st.notebook", layout="centered", initial_sidebar_state="collapsed")

nb = st_notebook({params_str})

# Add cells below using @nb.cell() decorator
# Example:
# @nb.cell(type='code')
# def cell_0():
#     st.write("Hello, World!")

# Render the notebook
nb.render()
"""

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
    if 'notebook_script' not in st.session_state:
        # Check if a notebook file was passed as command-line argument
        if len(sys.argv) > 1 and sys.argv[1].endswith('.py'):
            filepath = sys.argv[1]
            try:
                with open(filepath, 'r') as f:
                    st.session_state.notebook_script = f.read()
            except Exception as e:
                st.error(f"Failed to load notebook: {str(e)}")
                st.session_state.notebook_script = get_default_notebook_template()
        else:
            # No file provided, use default empty notebook template
            st.session_state.notebook_script = get_default_notebook_template()

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
        code_obj = compile(st.session_state.notebook_script, '<notebook_script>', 'exec')
        exec(code_obj, exec_globals)
    except Exception as e:
        import traceback
        st.error(f"Error executing notebook: {str(e)}")
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()


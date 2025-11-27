"""
Main streamlit script of the notebook app
"""

import streamlit as st
import os
import sys

def get_default_notebook_template():
    """Generate default empty notebook template with environment settings."""
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

def main():
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


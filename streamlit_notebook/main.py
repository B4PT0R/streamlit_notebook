"""
Main streamlit script of the notebook app
"""

import streamlit as st
from streamlit_notebook import st_notebook
import sys
import os

def main():
    st.set_page_config(page_title="st.notebook", layout="centered", initial_sidebar_state="collapsed")

    # Initialize the initial_notebook path in session state if it doesn't exist
    if 'initial_notebook_path' not in st.session_state:
        if len(sys.argv) > 1 and sys.argv[1].endswith('.stnb'):
            st.session_state.initial_notebook_path = sys.argv[1]
        else:
            st.session_state.initial_notebook_path = None

    # Check for app mode via environment variable
    app_mode = os.getenv('ST_NOTEBOOK_MODE', '').lower() == 'app'
    locked = os.getenv('ST_NOTEBOOK_LOCKED', '').lower() == 'true'

    # Pass the initial_notebook_path from session state to st_notebook
    st_notebook(
        st.session_state.initial_notebook_path,
        app_mode=app_mode,
        locked=locked
    )

if __name__ == "__main__":
    main()


"""
Main streamlit script of the notebook app
"""

import streamlit as st
from streamlit_notebook import st_notebook
import sys

def main():
    st.set_page_config(page_title="st.notebook", layout="centered", initial_sidebar_state="collapsed")

    # Initialize the initial_notebook path in session state if it doesn't exist
    if 'initial_notebook_path' not in st.session_state:
        if len(sys.argv) > 1 and sys.argv[1].endswith('.stnb'):
            st.session_state.initial_notebook_path = sys.argv[1]
        else:
            st.session_state.initial_notebook_path = None

    # Pass the initial_notebook_path from session state to st_notebook
    st_notebook(st.session_state.initial_notebook_path)

if __name__ == "__main__":
    main()


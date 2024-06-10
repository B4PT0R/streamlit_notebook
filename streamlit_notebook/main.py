"""
Main streamlit script of the notebook app
"""

import streamlit as st
from streamlit_notebook import st_notebook

st.set_page_config(initial_sidebar_state="collapsed")

st_notebook()

from .notebook import Notebook, get_notebook, render_notebook, set_page_config

# Load .env file if it exists (for ST_NOTEBOOK_APP_MODE and other env vars)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip
    pass

# Patch streamlit.set_page_config to be context-aware
import streamlit as st
import sys

# Replace st.set_page_config in the streamlit module
st.set_page_config = set_page_config
sys.modules['streamlit'].set_page_config = set_page_config
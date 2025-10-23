from .notebook import Notebook, get_notebook, render_notebook

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
import inspect

_original_set_page_config = st.set_page_config

def _patched_set_page_config(*args, **kwargs):
    """
    Patched version of st.set_page_config that only runs during exec context.

    When a notebook is run directly via 'streamlit run notebook.py', this becomes
    a no-op. When render_notebook() re-execs the script with __file__ = '<notebook_script>',
    the actual page config is set. This makes <notebook_script> the canonical execution context.
    """
    # Check if running from exec context (via <notebook_script>)
    frame = inspect.currentframe()
    caller_globals = frame.f_back.f_globals if frame else {}
    caller_file = caller_globals.get('__file__', '<notebook_script>')

    # Only call set_page_config if in exec context
    if caller_file == '<notebook_script>':
        _original_set_page_config(*args, **kwargs)

# Replace st.set_page_config in the streamlit module
st.set_page_config = _patched_set_page_config
sys.modules['streamlit'].set_page_config = _patched_set_page_config
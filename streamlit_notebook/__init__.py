"""Public package exports for ``streamlit_notebook``.

This module exposes the primary entry points of the package so they can be
imported directly from :mod:`streamlit_notebook` while keeping a small, clean
surface for Sphinx autodoc. It also installs the context-aware
``set_page_config`` patch so users can simply ``import streamlit as st`` and
configure their page normally inside notebook files.
"""

from .core.notebook import Notebook, st_notebook, get_notebook, set_page_config
from .core.utils import rerun, wait, set_root_path

set_root_path(__file__)

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
if not hasattr(st.set_page_config, '_patched'):
    set_page_config._patched = True
    set_page_config._original=st.set_page_config
    st.set_page_config = set_page_config
    sys.modules['streamlit'].set_page_config = set_page_config

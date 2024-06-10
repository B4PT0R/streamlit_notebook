import os,sys

# Ajouter le répertoire parent à sys.path pour permettre les imports relatifs
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import streamlit as st
from .notebook import st_notebook

st.set_page_config(initial_sidebar_state="collapsed")

st_notebook()

import streamlit as st
from cell_ui import Editor, CellUI
from utils import state,init_state, check_rerun

init_state()

if 'cell' not in state:
    state.cell=CellUI(code="Ceci est un test",key="mycell")

state.cell.show()

if state.cell.buttons['Auto_rerun'].toggled:
    st.text("Auto rerun toggled")

if state.cell.buttons['Fragment'].toggled:
    st.text("Fragment toggled")


check_rerun()


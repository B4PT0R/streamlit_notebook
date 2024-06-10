import streamlit as st

state=st.session_state

def init_state(**kwargs):
    for name,value in kwargs.items():
        if not name in state:
            state[name]=value


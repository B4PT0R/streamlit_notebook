import streamlit as st

# shortcut to st.session_state
state=st.session_state

def init_state(**kwargs):
    """
    Function to ease state initilization
    """
    for name,value in kwargs.items():
        if not name in state:
            state[name]=value


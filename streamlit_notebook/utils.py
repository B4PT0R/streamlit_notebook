import re
import streamlit as st
import random
import string

# shortcut for st.session_state
state=st.session_state

def short_id(length=16):
    """
    Generates a (most-likely) unique string id of specified length
    """
    return ''.join(random.choices(string.ascii_letters, k=length))

def init_state(**kwargs):
    """
    Initializes st.session_state with given kwargs
    """
    for key,value in kwargs.items():
        if not key in state:
            state[key]=value

def update_state(**kwargs):
    """
    update st.session_state with given kwargs
    """
    for key,value in kwargs.items():
        state[key]=value

def rerun():
    """
    Commands a rerun of the app at the end of the current run
    Doesn't interrupt any pending operation before the current run is finished
    """
    state.rerun=True
    
def check_rerun():
    """
    Placed as a last command in a streamlit main script, checks whether a rerun has been commanded by rerun() and reruns the app if so.
    """
    if 'rerun' in state and state.rerun:
        state.rerun=False
        st.rerun()

def format(string, **kwargs):
    """
    formats all occurrences of <<...>> tagged parts found in a string by evaluating the expressions using the kwargs as context namespace
    """
    if not kwargs:
        context = {}
    else:
        context=kwargs
    def replace_expr(match):
        expr = match.group(1)
        try:
            return str(eval(expr, context))
        except Exception as e:
            return '<<' + expr + '>>'
    return re.sub(r'<<(.*?)>>', replace_expr, string)
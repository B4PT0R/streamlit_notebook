import re
import streamlit as st

state=st.session_state

def init_state(**kwargs):
    if not 'rerun' in state:
        state.rerun=False
    for key,value in kwargs.items():
        if not key in state:
            state[key]=value

def check_rerun():
    if state.rerun:
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
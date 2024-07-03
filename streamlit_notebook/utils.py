import re
import streamlit as st
import random
import string
import os

os.environ['ROOT_PACKAGE_FOLDER']=os.path.dirname(os.path.abspath(__file__))

def root_join(*args):
    """
    Joins path components with the root package folder.

    This utility function is used to construct file paths relative to the package's root folder.

    Args:
        *args: Path components to join.

    Returns:
        str: The joined path string.
    """
    return os.path.join(os.getenv('ROOT_PACKAGE_FOLDER'),*args)

# shortcut for st.session_state
state=st.session_state

def short_id(length=16):
    """
    Generates a (most-likely) unique string id of specified length.

    Args:
        length (int): The length of the ID to generate. Defaults to 16.

    Returns:
        str: A random string of the specified length.
    """
    return ''.join(random.choices(string.ascii_letters, k=length))

def init_state(**kwargs):
    """
    Initializes st.session_state with given kwargs.

    Args:
        **kwargs: Keyword arguments to initialize in the session state.

    This function sets initial values in the Streamlit session state
    if they haven't been set already.
    """
    for key,value in kwargs.items():
        if not key in state:
            state[key]=value

def update_state(**kwargs):
    """
    Updates st.session_state with given kwargs.

    Args:
        **kwargs: Keyword arguments to update in the session state.

    This function updates values in the Streamlit session state,
    overwriting existing values if they exist.
    """
    for key,value in kwargs.items():
        state[key]=value

def rerun():
    """
    Commands a rerun of the app at the end of the current run.

    This function sets a flag in the session state to trigger a rerun
    of the Streamlit app after the current execution is complete.
    """
    state.rerun_flag=True
    
def check_rerun():
    """
    Checks whether a rerun has been commanded and reruns the app if so.

    This function should be placed as the last command in a Streamlit main script.
    It checks for the rerun flag and triggers a rerun if it's set.
    """
    if 'rerun_flag' in state and state.rerun_flag:
        state.rerun_flag=False
        st.rerun()

def format(string, **kwargs):
    """
    Formats all occurrences of <<...>> tagged parts found in a string.

    Args:
        string (str): The input string containing <<...>> tags.
        **kwargs: Keyword arguments used as the context namespace for evaluating expressions.

    Returns:
        str: The formatted string with all <<...>> tags replaced by their evaluated expressions.

    This function evaluates the expressions within <<...>> tags using the provided kwargs as context.
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
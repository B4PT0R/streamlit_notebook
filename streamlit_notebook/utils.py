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

def rerun(delay=0):
    """
    Commands a rerun of the app at the end of the current run.

    This function sets a flag in the session state to trigger a rerun
    of the Streamlit app after the current execution is complete.

    When called multiple times during the same run, intelligently merges
    the requests to ensure the longest total delay is respected.

    Args:
        delay (float): Minimum delay in seconds before executing the rerun.
                      Useful to ensure UI feedback (toasts, animations, etc.)
                      is visible before the rerun.
                      Defaults to 0 (immediate rerun).

    Examples:
        # Ensure toast is visible before rerun
        st.toast("File saved!", icon="💾")
        rerun(delay=1.5)

        # Wait for animation to complete
        with st.spinner("Processing..."):
            process_data()
        rerun(delay=0.5)  # Let spinner disappear gracefully

        # Multiple calls - longest delay wins
        st.toast("Action 1")
        rerun(delay=1.0)
        st.toast("Action 2")
        rerun(delay=2.0)  # This will execute at 2.0s from now

        # Progress bar that needs to be seen
        progress = st.progress(0)
        for i in range(100):
            progress.progress(i + 1)
        rerun(delay=1.0)  # Let user see 100% completion
    """
    import time
    current_time = time.time()

    # If there's already a pending rerun, merge intelligently
    if 'rerun' in state and state.rerun:
        existing = state.rerun
        existing_requested_at = existing.get('requested_at', current_time)
        existing_delay = existing.get('delay', 0)

        # Calculate when the existing rerun would execute
        existing_execute_at = existing_requested_at + existing_delay

        # Calculate when this new rerun would execute
        new_execute_at = current_time + delay

        # Use whichever execution time is later (longest total delay)
        if new_execute_at > existing_execute_at:
            # New request requires longer wait - update to new timestamp and delay
            state.rerun = {
                'requested_at': current_time,
                'delay': delay
            }
        else:
            # Existing request already waits long enough
            # Keep the existing request but adjust delay to account for time passed
            elapsed = current_time - existing_requested_at
            state.rerun = {
                'requested_at': current_time,
                'delay': max(0, existing_delay - elapsed)
            }
    else:
        # First rerun request
        state.rerun = {
            'requested_at': current_time,
            'delay': delay
        }

def check_rerun():
    """
    Checks whether a rerun has been commanded and reruns the app if so.

    This function should be placed as the last command in a Streamlit main script.
    It checks for the rerun flag and triggers a rerun if it's set, waiting
    for the requested delay if necessary.
    """
    import time
    if 'rerun' in state and state.rerun:
        rerun_info = state.rerun
        requested_at = rerun_info.get('requested_at', 0)
        delay = rerun_info.get('delay', 0)

        # Calculate elapsed time since rerun was requested
        elapsed = time.time() - requested_at

        # Wait for remaining delay if needed
        remaining_delay = delay - elapsed
        if remaining_delay > 0:
            time.sleep(remaining_delay)

        # Clear the rerun flag and execute rerun
        state.rerun = None
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
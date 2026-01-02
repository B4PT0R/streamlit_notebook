# Tutorial 09: Rerun Control
# Advanced flow management with rerun(), wait(), and check_rerun()

from streamlit_notebook import st_notebook
import streamlit as st
from streamlit_notebook.core.rerun import rerun, wait

nb = st_notebook(title='09_rerun_control')


@nb.cell(type='markdown', minimized=True)
def intro():
    r'''
    # Rerun Control

    Take fine-grained control over when and how your notebook reruns with
    `rerun()`, `wait()`, and `check_rerun()`.
    '''


@nb.cell(type='markdown', minimized=True)
def rerun_basics():
    r'''
    ## The `rerun()` Function

    `rerun(scope, wait)` triggers an app rerun with precise control:

    - `scope="app"` - Full app rerun (default)
    - `scope="fragment"` - Fragment-scoped rerun
    - `wait=True` - Soft rerun as soon as possible (default)
    - `wait=False` - Hard rerun immediately
    - `wait=<float>` - Wait N seconds before rerun
    '''


@nb.cell(type='code', reactive=True)
def immediate_rerun_demo():
    st.subheader("Immediate Rerun")

    if 'counter_09a' not in st.session_state:
        st.session_state.counter_09a = 0

    st.metric("Counter", st.session_state.counter_09a)

    if st.button("Increment & Rerun Immediately", key='button_immediate_09'):
        st.session_state.counter_09a += 1
        rerun(wait=False)  # Hard rerun immediately


@nb.cell(type='markdown', minimized=True)
def delayed_rerun():
    r'''
    ## Delayed Reruns with `wait`

    Use `wait=<seconds>` to delay reruns. Perfect for:
    - Rate limiting
    - Debouncing user input
    - Timed operations
    '''


@nb.cell(type='code', reactive=True)
def delayed_rerun_demo():
    st.subheader("Delayed Rerun (2 seconds)")

    if 'counter_09b' not in st.session_state:
        st.session_state.counter_09b = 0

    st.metric("Counter", st.session_state.counter_09b)

    if st.button("Increment & Rerun After 2s", key='button_delayed_09'):
        st.session_state.counter_09b += 1
        rerun(wait=2.0)  # Wait 2 seconds before rerunning
        st.info("Rerun scheduled in 2 seconds...")


@nb.cell(type='markdown', minimized=True)
def wait_function():
    r'''
    ## The `wait()` Function

    `wait(delay)` requests a delay without triggering a rerun:

    - `wait(True)` or `wait(0)` - No additional delay
    - `wait(False)` - Execute pending rerun immediately
    - `wait(<float>)` - Request N second delay
    '''


@nb.cell(type='code', reactive=True)
def wait_demo():
    st.subheader("Wait Control")

    if 'pending_09' not in st.session_state:
        st.session_state.pending_09 = False

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Schedule Rerun", key='button_schedule_09'):
            st.session_state.pending_09 = True
            rerun(wait=5.0)
            st.success("Scheduled in 5s")

    with col2:
        if st.button("Add 2s Delay", key='button_add_delay_09'):
            wait(2.0)
            st.info("Added 2s delay")

    with col3:
        if st.button("Execute Now", key='button_execute_09'):
            wait(False)  # Execute pending rerun immediately
            st.warning("Executing!")


@nb.cell(type='markdown', minimized=True)
def delay_merging():
    r'''
    ## Intelligent Delay Merging

    When multiple `rerun()` or `wait()` calls are made, delays are merged intelligently:
    - Multiple reruns take the **maximum** delay
    - Ensures smooth UX without excessive reruns
    '''


@nb.cell(type='code', reactive=True)
def merge_demo():
    st.subheader("Delay Merging Example")

    if st.button("Multiple Reruns", key='button_multiple_09'):
        rerun(wait=1.0)
        rerun(wait=3.0)  # This wins (max delay)
        rerun(wait=2.0)
        st.info("Three reruns scheduled - will execute after 3 seconds (max)")


@nb.cell(type='markdown', minimized=True)
def fragment_scope():
    r'''
    ## Fragment-Scoped Reruns

    In fragment cells, use `rerun(scope="fragment")` to rerun only the fragment:
    '''


@nb.cell(type='code', reactive=True, fragment=True)
def fragment_rerun_demo():
    from datetime import datetime

    st.subheader("Fragment Rerun Demo")

    st.write(f"Fragment time: {datetime.now().strftime('%H:%M:%S')}")

    if st.button("Rerun Fragment Only", key='button_fragment_09'):
        rerun(scope="fragment", wait=0.5)
        st.caption("Fragment will rerun in 0.5s")


@nb.cell(type='markdown', minimized=True)
def use_cases():
    r'''
    ## Use Cases

    ✅ **Debouncing** - Wait for user to finish typing
    ✅ **Rate limiting** - Prevent excessive API calls
    ✅ **Timed operations** - Delayed state updates
    ✅ **Progress indicators** - Update UI during long operations
    ✅ **Interactive animations** - Scheduled visual updates
    '''


@nb.cell(type='markdown', minimized=True)
def api_reference():
    r'''
    ## API Reference

    ```python
    from streamlit_notebook.core.rerun import rerun, wait, check_rerun

    # Rerun control
    rerun(scope="app", wait=True)      # Schedule soft rerun
    rerun(scope="fragment", wait=2.0)  # Fragment rerun in 2s
    rerun(wait=False)                   # Immediate hard rerun

    # Delay control
    wait(delay=3.0)     # Request 3 second delay
    wait(delay=False)   # Execute pending rerun now

    # Check and execute pending reruns (called automatically)
    check_rerun()
    ```
    '''


@nb.cell(type='code', reactive=True, minimized=True)
def navigation():
    st.markdown("---")
    from streamlit_notebook.demo_notebooks.helpers import navigation
    navigation()

nb.render()

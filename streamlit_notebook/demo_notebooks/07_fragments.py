# Tutorial 07: Fragments and Auto-Refresh
# Scoped reruns and automatic updates with run_every

from streamlit_notebook import st_notebook
import streamlit as st

nb = st_notebook(title='07_fragments')


@nb.cell(type='markdown', minimized=True)
def intro():
    r'''
    # Fragments and Auto-Refresh

    **Fragments** allow cells to rerun independently without affecting the rest of the notebook.
    Add `run_every` for automatic periodic updates!
    '''


@nb.cell(type='markdown', minimized=True)
def why_fragments():
    r'''
    ## Why Fragments?

    **Problem**: In reactive cells, every widget interaction reruns the entire notebook, which can be inefficient.

    **Solution**: Mark cells as fragments (`fragment=True`) to:
    - Rerun only that specific cell in response to UI events
    - Avoid expensive recomputations elsewhere
    - Enable auto-refresh with `run_every`

    An event from a widget inside a fragment cell only triggers that cell to rerun.
    Any event from outside (another cell) still reruns the whole notebook (ie. all reactive cells, including the fragment).
    '''


@nb.cell(type='code', reactive=True)
def regular_cell():
    from datetime import datetime

    st.subheader("Regular Reactive Cell")

    mode = st.selectbox(
        "Select mode",
        ["Development", "Staging", "Production"],
        key='selectbox_mode_07'
    )

    st.info(f"Mode: {mode} | Last update: {datetime.now().strftime('%H:%M:%S')}")
    st.write("⚠️ This cell reruns when you change the selectbox");


@nb.cell(type='code', reactive=True, fragment=True)
def fragment_cell():
    from datetime import datetime

    st.subheader("Fragment Cell")

    count = st.slider("Counter", 0, 100, 50, key='slider_count_07')

    st.success(f"Count: {count} | Fragment time: {datetime.now().strftime('%H:%M:%S')}")
    st.write("✅ This fragment reruns independently - the cell above doesn't rerun!");


@nb.cell(type='markdown', minimized=True)
def auto_refresh_intro():
    r'''
    ## Auto-Refresh with `run_every`

    Combine `fragment=True` with `run_every=seconds` for automatic updates.
    Perfect for live dashboards, monitoring, and real-time data.
    '''


@nb.cell(type='code', reactive=True, fragment=True, run_every=2)
def auto_refresh_demo():
    from datetime import datetime
    import random

    st.subheader("⏱️ Auto-Refresh (Every 2 seconds)")

    # Simulate live metrics
    current_time = datetime.now().strftime('%H:%M:%S')
    cpu_usage = random.randint(20, 80)
    memory_usage = random.randint(40, 90)

    col1, col2, col3 = st.columns(3)
    col1.metric("Time", current_time)
    col2.metric("CPU %", f"{cpu_usage}%")
    col3.metric("Memory %", f"{memory_usage}%")

    st.caption("This cell auto-refreshes every 2 seconds without rerunning other cells!");


@nb.cell(type='markdown', minimized=True)
def fragment_syntax():
    r'''
    ## Fragment Syntax

    ```python
    @nb.cell(type='code', reactive=True, fragment=True)
    def my_fragment():
        # Reruns independently
        st.button("Click me", key='btn')

    @nb.cell(type='code', reactive=True, fragment=True, run_every=3)
    def auto_refresh():
        # Reruns every 3 seconds
        st.write(datetime.now())
    ```
    '''


@nb.cell(type='markdown', minimized=True)
def use_cases():
    r'''
    ## Use Cases

    ✅ **Live dashboards** - Real-time metrics and charts
    ✅ **Monitoring** - System stats, logs, alerts
    ✅ **Progress tracking** - Long-running operations
    ✅ **Interactive widgets** - Isolate expensive operations

    **Note**: `run_every` requires `fragment=True`
    '''


@nb.cell(type='code', reactive=True, minimized=True)
def navigation():
    st.markdown("---")
    from streamlit_notebook.demo_notebooks.helpers import navigation
    navigation()

nb.render()

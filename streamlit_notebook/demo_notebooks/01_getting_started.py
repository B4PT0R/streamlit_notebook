# Tutorial 01: Welcome to Streamlit Notebook
# Your first look at cell-based interactive notebooks

from streamlit_notebook import st_notebook
import streamlit as st

nb = st_notebook(title='01_getting_started')

@nb.cell(type='markdown', minimized=True)
def welcome():
    r'''
    # Welcome to Streamlit Notebook!

    **Streamlit Notebook** combines the best of Jupyter notebooks and Streamlit apps:
    - Write notebooks as **plain Python files** (git-friendly!)
    - Run cells **on-demand** instead of top-to-bottom
    - Use the **full Streamlit API** for widgets, charts, and layouts
    - Deploy to production **without changes**
    '''


@nb.cell(type='code', reactive=False)
def first_cell():
    import numpy as np

    # This is a one-shot cell - runs once when you click Run
    data = np.random.randn(100)
    mean_value = data.mean()

    print(f"Generated 100 random numbers with mean: {mean_value:.3f}")


@nb.cell(type='markdown', minimized=True)
def explain_oneshot():
    r'''
    ### Try it out!

    Click **Run** on the cell above. Notice it prints once and stays executed.
    Like Jupyter, it will run only when you trigger it.
    '''


@nb.cell(type='code', reactive=True)
def interactive_demo():
    st.subheader("Interactive Demo")

    # This is a reactive cell - reruns when you interact
    threshold = st.slider(
        "Adjust threshold",
        min_value=0.0,
        max_value=5.0,
        value=2.5,
        key='slider_threshold_demo'
    )

    count = sum(1 for x in data if abs(x) > threshold)
    st.metric("Values beyond threshold", count)

    st.info(f"Mean from previous cell: {mean_value:.3f}");


@nb.cell(type='markdown', minimized=True)
def explain_reactive():
    r'''
    ### How it works

    - **One-shot cells** (⚪): Run once - perfect for data loading
    - **Reactive cells** (🔵): Auto-rerun - great for widgets
    - Variables persist across cells in a shared namespace
    '''


@nb.cell(type='markdown', minimized=True)
def what_next():
    r'''
    ## What's in this tour?

    1. **Cell types** - One-shot vs reactive execution
    2. **Display** - Persistent output with `display()`
    3. **Widgets** - Keys and session state
    4. **Markdown & HTML** - Live interpolation with `<<expr>>`
    5. **Layouts** - Horizontal mode and styling
    6. **Fragments** - Scoped reruns and auto-refresh
    7. **Programmatic API** - Control notebooks with code
    8. **Rerun control** - Advanced flow management
    9. **Deployment** - App mode and file operations
    10. **AI Agent** - Optional assistant integration
    '''


@nb.cell(type='markdown', minimized=True)
def quick_start():
    r'''
    ## Quick Start Commands

    ```bash
    # Edit mode - full notebook interface
    st_notebook my_notebook.py

    # App mode - locked, production-ready view
    st_notebook my_notebook.py -- --app
    ```
    '''


@nb.cell(type='code', reactive=True, minimized=True)
def navigation():
    st.markdown("---")
    from streamlit_notebook.demo_notebooks.helpers import navigation
    navigation()

nb.render()

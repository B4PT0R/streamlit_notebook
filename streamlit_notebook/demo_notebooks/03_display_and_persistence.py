# Tutorial 03: Display and Persistence
# Keep outputs visible with the display() function

from streamlit_notebook import st_notebook
import streamlit as st
from streamlit_notebook.core.display import display

nb = st_notebook(title='03_display_and_persistence')


@nb.cell(type='markdown', minimized=True)
def intro():
    r'''
    # Display and Persistence

    In one-shot cells, outputs disappear after reruns unless you use `display()`.
    '''


@nb.cell(type='markdown', minimized=True)
def problem():
    r'''
    ## The Problem

    When a one-shot cell runs, it creates output. But on subsequent reruns (when you
    interact with widgets), Streamlit clears the output area. The cell doesn't rerun
    (it's one-shot!), so the output disappears.

    **Solution**: Use `display()` to store outputs that persist across reruns.
    '''


@nb.cell(type='code', reactive=False)
def create_data():
    import pandas as pd
    import numpy as np

    # Create sample dataset
    np.random.seed(123)
    df = pd.DataFrame({
        'product': ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon'],
        'sales': np.random.randint(100, 500, 5),
        'profit': np.random.randint(20, 150, 5),
        'rating': np.random.uniform(3.5, 5.0, 5).round(2)
    })

    summary = {
        'total_products': len(df),
        'total_sales': int(df['sales'].sum()),
        'avg_rating': float(df['rating'].mean().round(2))
    }

    print("✓ Data created")


@nb.cell(type='code', reactive=False)
def display_data():
    # display() keeps these visible even after reruns!
    display(df, backend='dataframe', width="stretch")
    display(summary, backend='json', expanded=True)

    # You can also use display without a backend
    display(f"Top product: {df.loc[df['sales'].idxmax(), 'product']}")


@nb.cell(type='markdown', minimized=True)
def display_backends():
    r'''
    ## Display Backends

    `display()` supports various backends:
    - `backend='dataframe'` - Interactive dataframe viewer
    - `backend='json'` - Expandable JSON tree
    - `backend='table'` - Static table
    - `backend='code'` - Code block
    - `backend='metric'` - Metric display
    - any other st.* function's name (e.g., `backend='line_chart'`)
    - No backend - Uses `st.write()` (smart fallback)
    '''


@nb.cell(type='code', reactive=True)
def interactive_check():
    st.subheader("Test Persistence")

    # Try changing this slider - the display() outputs above stay visible!
    test_value = st.slider(
        "Move this slider - notice the data above stays visible",
        0, 100, 50,
        key='slider_test_03'
    )

    st.success(f"Current value: {test_value}. The displayed data persists!");


@nb.cell(type='markdown', minimized=True)
def best_practices():
    r'''
    ## When to Use display()

    ✅ **Use display()** in one-shot cells for:
    - Tables and dataframes
    - Charts and visualizations
    - Summary statistics
    - Any output that should persist

    ✅ **Use st.write()** in reactive cells:
    - They rerun anyway, so persistence isn't needed
    '''


@nb.cell(type='code', reactive=True, minimized=True)
def navigation():
    st.markdown("---")
    from streamlit_notebook.demo_notebooks.helpers import navigation
    navigation()

nb.render()

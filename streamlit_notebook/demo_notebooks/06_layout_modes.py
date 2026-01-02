# Tutorial 06: Layouts and Styling
# Control page width, horizontal mode, and code/output split

from streamlit_notebook import st_notebook
import streamlit as st

nb = st_notebook(
    title='06_layout_modes',
    layout={
        'width': 'wide',
        'horizontal': True,
        'vertical_split': 40
    }
)


@nb.cell(type='markdown', minimized=True)
def intro():
    r'''
    # Layouts and Styling

    **This notebook demonstrates horizontal layout**: code on the left (40%), output on the right (60%).

    Try toggling **App View** in the sidebar to see the output full-width!
    '''


@nb.cell(type='markdown', minimized=True)
def layout_options():
    r'''
    ## Layout Configuration

    Configure layout when creating the notebook:

    ```python
    nb = st_notebook(
        title='my_notebook',
        layout={
            'width': 'wide',              # 'centered', 'wide', or '50%'-'100%'
            'horizontal': True,           # Side-by-side code/output
            'vertical_split': 40,         # Code width (20-80%)
            'initial_sidebar_state': 'auto'  # 'auto', 'expanded', 'collapsed'
        }
    )
    ```
    '''


@nb.cell(type='code', reactive=False)
def load_dashboard_data():
    import pandas as pd
    import numpy as np

    np.random.seed(888)
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=90, freq='D'),
        'users': np.random.randint(1000, 5000, 90),
        'revenue': np.random.randint(5000, 20000, 90),
        'costs': np.random.randint(2000, 10000, 90)
    })
    df['profit'] = df['revenue'] - df['costs']
    df['margin'] = (df['profit'] / df['revenue'] * 100).round(1)

    print(f"✓ Loaded {len(df)} days of data")


@nb.cell(type='code', reactive=True)
def wide_dashboard():
    st.subheader("📊 Business Dashboard")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        min_users = st.slider(
            "Minimum users",
            min_value=int(df['users'].min()),
            max_value=int(df['users'].max()),
            value=int(df['users'].min()),
            key='slider_users_06'
        )
    with col2:
        min_margin = st.slider(
            "Minimum margin %",
            min_value=float(df['margin'].min()),
            max_value=float(df['margin'].max()),
            value=0.0,
            key='slider_margin_06'
        )

    # Filter data
    filtered = df[(df['users'] >= min_users) & (df['margin'] >= min_margin)]

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Days", len(filtered), f"{100*len(filtered)/len(df):.0f}%")
    c2.metric("Avg Users", f"{filtered['users'].mean():.0f}")
    c3.metric("Total Revenue", f"${filtered['revenue'].sum():,}")
    c4.metric("Avg Margin", f"{filtered['margin'].mean():.1f}%")

    # Charts
    st.line_chart(filtered.set_index('date')[['users', 'revenue']], height=300);


@nb.cell(type='markdown', minimized=True)
def layout_tips():
    r'''
    ## Layout Tips

    - **Horizontal mode** is perfect for dashboards and data exploration
    - Adjust the **vertical_split** to balance code visibility vs output space
    - Use **wide** layout for charts and tables
    - Toggle **App View** for presentations
    '''


@nb.cell(type='markdown', minimized=True)
def runtime_control():
    r'''
    ## Runtime Control

    You can also control layout from the sidebar:
    - **Width slider** - Adjust page width
    - **Layout settings** - Toggle horizontal mode in settings dialog
    - **Code/Output split** - Drag the divider between code and output
    '''


@nb.cell(type='code', reactive=True, minimized=True)
def navigation():
    st.markdown("---")
    from streamlit_notebook.demo_notebooks.helpers import navigation
    navigation()

nb.render()

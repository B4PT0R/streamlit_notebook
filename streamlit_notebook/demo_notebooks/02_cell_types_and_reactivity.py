# Tutorial 02: Cell Types and Reactivity
# Master one-shot and reactive execution patterns

from streamlit_notebook import st_notebook
import streamlit as st

nb = st_notebook(title='02_cell_types_and_reactivity')


@nb.cell(type='markdown', minimized=True)
def intro():
    r'''
    # Cell Types and Reactivity

    Understanding when cells run is the key to efficient notebooks.
    '''


@nb.cell(type='markdown', minimized=True)
def execution_modes():
    r'''
    ## Two Execution Modes

    **One-shot cells** (⚪) - Run once when triggered:
    - Perfect for imports, data loading, heavy computations
    - Output persists across reruns
    - Won't rerun unless you click Run again

    **Reactive cells** (🔵) - Auto-rerun on interactions:
    - Great for widgets and dynamic UI
    - Rerun when any widget changes
    - Fast operations only
    '''


@nb.cell(type='code', reactive=False)
def load_data():
    import pandas as pd
    import numpy as np
    from time import sleep

    # Simulate heavy computation
    print("Loading data... (this runs once!)")
    sleep(0.5)

    np.random.seed(42)
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=100, freq='D'),
        'revenue': np.random.randint(5000, 15000, 100),
        'costs': np.random.randint(2000, 8000, 100),
        'region': np.random.choice(['North', 'South', 'East', 'West'], 100)
    })
    df['profit'] = df['revenue'] - df['costs']

    print(f"✓ Loaded {len(df)} rows from 4 regions")


@nb.cell(type='code', reactive=True)
def interactive_dashboard():
    st.subheader("Interactive Dashboard")

    # Widgets in reactive cells
    col1, col2 = st.columns(2)
    with col1:
        region = st.selectbox(
            "Filter by region",
            options=['All'] + sorted(df['region'].unique().tolist()),
            key='selectbox_region_02'
        )
    with col2:
        min_profit = st.slider(
            "Minimum profit threshold",
            min_value=int(df['profit'].min()),
            max_value=int(df['profit'].max()),
            value=int(df['profit'].median()),
            key='slider_min_profit_02'
        )

    # Filter data
    filtered = df.copy()
    if region != 'All':
        filtered = filtered[filtered['region'] == region]
    filtered = filtered[filtered['profit'] >= min_profit]

    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Days", len(filtered), f"{100*len(filtered)/len(df):.0f}% of total")
    c2.metric("Total Revenue", f"${filtered['revenue'].sum():,}")
    c3.metric("Total Profit", f"${filtered['profit'].sum():,}")

    # Chart
    st.line_chart(filtered.set_index('date')[['revenue', 'profit']], height=300);


@nb.cell(type='markdown', minimized=True)
def best_practices():
    r'''
    ## Best Practices

    ✅ **DO**: Put expensive operations in one-shot cells
    ✅ **DO**: Put widgets in reactive cells
    ✅ **DO**: Load data once, filter it reactively

    ❌ **DON'T**: Put widgets in one-shot cells
    ❌ **DON'T**: Reload data on every interaction
    '''


@nb.cell(type='code', reactive=True)
def run_counter():
    # This demonstrates reactive behavior
    if 'run_count_02' not in st.session_state:
        st.session_state.run_count_02 = 0
    st.session_state.run_count_02 += 1

    st.info(f"🔵 This reactive cell has run {st.session_state.run_count_02} times. Try changing the filters above!");


@nb.cell(type='code', reactive=True, minimized=True)
def navigation():
    st.markdown("---")
    from streamlit_notebook.demo_notebooks.helpers import navigation
    navigation()


nb.render()

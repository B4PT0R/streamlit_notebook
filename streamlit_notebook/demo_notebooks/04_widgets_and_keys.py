# Tutorial 04: Widgets and State
# Widget keys and session state patterns

from streamlit_notebook import st_notebook
import streamlit as st

nb = st_notebook(title='04_widgets_and_keys')


@nb.cell(type='markdown', minimized=True)
def intro():
    r'''
    # Widgets and State

    Every widget needs a unique `key` to maintain state across reruns.
    '''


@nb.cell(type='markdown', minimized=True)
def key_requirements():
    r'''
    ## Why Keys Matter

    In Streamlit Notebook, keys serve two purposes:
    1. **Uniquely identify** widgets across the entire notebook
    2. **Preserve state** across cell reruns

    Without keys, widgets may conflict or lose their state.
    '''


@nb.cell(type='code', reactive=True)
def basic_widgets():
    st.subheader("Basic Widgets")

    # Use descriptive keys with prefixes
    product = st.selectbox(
        "Select product",
        ['Alpha', 'Beta', 'Gamma', 'Delta'],
        key='selectbox_product'
    )

    quantity = st.slider(
        "Quantity",
        min_value=1,
        max_value=100,
        value=10,
        key='slider_quantity'
    )

    rush_order = st.checkbox(
        "Rush order (+$50)",
        value=False,
        key='checkbox_rush'
    )

    # Calculate price
    base_price = {'Alpha': 100, 'Beta': 150, 'Gamma': 200, 'Delta': 250}
    total = base_price[product] * quantity + (50 if rush_order else 0)

    st.metric("Total Price", f"${total:,}");


@nb.cell(type='markdown', minimized=True)
def session_state_intro():
    r'''
    ## Session State

    Use `st.session_state` to store data that persists across reruns.
    It's like a Python dictionary that survives app reruns.
    '''


@nb.cell(type='code', reactive=True)
def session_state_demo():
    st.subheader("Session State Demo")

    # Initialize state
    if 'counter' not in st.session_state:
        st.session_state.counter = 0
    if 'history' not in st.session_state:
        st.session_state.history = []

    # Buttons modify state
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("➕ Increment", key='button_inc', width="stretch"):
            st.session_state.counter += 1
            st.session_state.history.append('+1')

    with col2:
        if st.button("➖ Decrement", key='button_dec', width="stretch"):
            st.session_state.counter -= 1
            st.session_state.history.append('-1')

    with col3:
        if st.button("🔄 Reset", key='button_reset', width="stretch"):
            st.session_state.counter = 0
            st.session_state.history = []

    # Display state
    st.metric("Counter", st.session_state.counter)

    if st.session_state.history:
        st.caption(f"History: {' '.join(st.session_state.history[-10:])}");


@nb.cell(type='markdown', minimized=True)
def key_best_practices():
    r'''
    ## Key Best Practices

    ✅ **DO**:
    - Use descriptive names: `slider_temperature`
    - Add widget type prefixes: `selectbox_`, `button_`, `slider_`

    ❌ **DON'T**:
    - Use generic keys: `key='x'`, `key='1'`
    - Forget keys on widgets
    - Reuse keys across different widgets
    '''


@nb.cell(type='code', reactive=True)
def state_across_cells():
    st.subheader("State Across Cells")

    # Access state from previous cell
    counter_value = st.session_state.get('counter', 0)

    st.info(f"The counter from above is: {counter_value}")
    st.write("Session state is shared across all cells!")


@nb.cell(type='code', reactive=True, minimized=True)
def navigation():
    st.markdown("---")
    from streamlit_notebook.demo_notebooks.helpers import navigation
    navigation()

nb.render()

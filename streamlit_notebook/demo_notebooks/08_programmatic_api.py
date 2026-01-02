# Tutorial 08: Programmatic API
# Control notebooks dynamically with __notebook__

from streamlit_notebook import st_notebook
import streamlit as st

nb = st_notebook(title='08_programmatic_api')


@nb.cell(type='markdown', minimized=True)
def intro():
    r'''
    # Programmatic API

    Access the running notebook via `__notebook__` to control cells,
    configuration, and execution programmatically.
    '''


@nb.cell(type='markdown', minimized=True)
def notebook_object():
    r'''
    ## The `__notebook__` Object

    Inside any cell, `__notebook__` gives you access to the notebook instance.
    Use it to inspect state, create cells, or control execution.
    '''


@nb.cell(type='code', reactive=False)
def inspect_notebook():

    nb = __notebook__

    info = {
        'title': nb.config.title,
        'cell_count': len(nb.cells),
        'app_mode': nb.config.app_mode,
        'app_view': nb.config.app_view,
        'horizontal_layout': nb.config.layout.horizontal
    }

    display(info, backend='json', expanded=True)
    print(f"✓ Notebook has {len(nb.cells)} cells")


@nb.cell(type='markdown', minimized=True)
def dynamic_cells():
    r'''
    ## Creating Cells Dynamically

    Use `nb.new_cell()` to add cells at runtime. Perfect for:
    - Code generators
    - Template systems
    - AI assistants
    - Data-driven notebooks
    '''


@nb.cell(type='code', reactive=True)
def cell_creator():
    st.subheader("Dynamic Cell Creator")

    col1, col2 = st.columns(2)
    with col1:
        cell_type = st.selectbox(
            "Cell type",
            ['code', 'markdown', 'html'],
            key='selectbox_cell_type_08'
        )
    with col2:
        is_reactive = st.checkbox("Reactive?", value=False, key='checkbox_reactive_08')

    content = st.text_area(
        "Cell content",
        value="# Hello from a dynamic cell!" if cell_type == 'markdown' else "print('Hello!')",
        key='textarea_content_08',
        height=100
    )

    if st.button("➕ Create Cell", key='button_create_08'):
        nb = __notebook__
        new_cell = nb.new_cell(
            type=cell_type,
            code=content,
            reactive=is_reactive
        )
        st.success(f"✓ Created {new_cell.id}")
        st.caption("Scroll down to see the new cell!")


@nb.cell(type='markdown', minimized=True)
def cell_control():
    r'''
    ## Cell Control Methods

    ```python
    nb = __notebook__

    # Cell management
    cell = nb.get_cell(0)          # Get cell by index
    cell.run()                      # Execute cell
    cell.reset()                    # Clear outputs
    cell.delete()                   # Remove cell

    # Bulk operations
    nb.run_all_cells()             # Run all cells
    nb.minimize_all()              # Hide all editors
    nb.expand_all()                # Show all editors
    nb.restart_session()           # Clear and restart
    ```
    '''


@nb.cell(type='code', reactive=True)
def bulk_operations():
    st.subheader("Bulk Operations")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("▶️ Run All", key='button_run_all_08', width="stretch"):
            __notebook__.run_all_cells()
            st.success("Running all cells...")

    with col2:
        if st.button("⬇️ Minimize", key='button_minimize_08', width="stretch"):
            __notebook__.minimize_all()
            st.success("Minimized all cells")

    with col3:
        if st.button("⬆️ Expand", key='button_expand_08', width="stretch"):
            __notebook__.expand_all()
            st.success("Expanded all cells")


@nb.cell(type='markdown', minimized=True)
def use_cases():
    r'''
    ## Use Cases

    ✅ **Code generation** - Create cells from templates
    ✅ **AI assistants** - Let AI create and modify cells
    ✅ **Data exploration** - Generate analysis cells from data
    ✅ **Testing** - Programmatically control execution
    ✅ **Notebooks as apps** - Dynamic interfaces based on user input
    '''


@nb.cell(type='code', reactive=True, minimized=True)
def navigation():
    st.markdown("---")
    from streamlit_notebook.demo_notebooks.helpers import navigation
    navigation()

nb.render()

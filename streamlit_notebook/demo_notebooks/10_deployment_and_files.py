# Tutorial 10: Deployment and File Operations
# App mode, file I/O, and production deployment

from streamlit_notebook import st_notebook
import streamlit as st

nb = st_notebook(title='10_deployment_and_files')


@nb.cell(type='markdown', minimized=True)
def intro():
    r'''
    # Deployment and File Operations

    Deploy notebooks as production apps and manage notebook files programmatically.
    '''


@nb.cell(type='markdown', minimized=True)
def modes_explained():
    r'''
    ## App Mode vs Edit Mode

    **Edit Mode** (default):
    - Full notebook editing interface
    - Create, edit, and delete cells
    - Access all configuration options

    **App Mode** (`--app` flag):
    - Locked, production-ready view
    - Only shows outputs (no code editors)
    - Clean interface for end users
    '''


@nb.cell(type='code', reactive=True)
def check_current_mode():
    nb = __notebook__

    st.subheader("Current Configuration")

    config_info = {
        'app_mode': nb.config.app_mode,
        'app_view': nb.config.app_view,
        'title': nb.config.title,
        'layout_width': nb.config.layout.width,
        'horizontal_layout': nb.config.layout.horizontal
    }

    col1, col2 = st.columns(2)
    with col1:
        st.json(config_info)
    with col2:
        st.info("💡 Toggle **App View** in the sidebar to preview app mode")


@nb.cell(type='markdown', minimized=True)
def running_notebooks():
    r'''
    ## Running Notebooks

    **Development** (with editing):
    ```bash
    st_notebook my_notebook.py
    streamlit run my_notebook.py
    ```

    **Production** (app mode, locked):
    ```bash
    st_notebook my_notebook.py -- --app
    streamlit run my_notebook.py -- --app
    ```

    **With options**:
    ```bash
    st_notebook my_notebook.py -- --app --no-quit
    export ST_NOTEBOOK_APP_MODE=true
    export ST_NOTEBOOK_NO_QUIT=true
    ```
    '''


@nb.cell(type='markdown', minimized=True)
def file_operations():
    r'''
    ## File Operations

    Programmatically save, open, and manage notebooks:
    '''


@nb.cell(type='code', reactive=True)
def file_operations_demo():
    st.subheader("File Operations")

    nb = __notebook__

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Save notebook**")
        st.code("nb.save('my_notebook.py')", language='python')

        st.write("**Open notebook**")
        st.code("nb.open('other_notebook.py')", language='python')

    with col2:
        st.write("**Convert to Python**")
        st.code("python_code = nb.to_python()", language='python')

        st.write("**Get notebook info**")
        st.code("info = nb.get_info(minimal=False)", language='python')


@nb.cell(type='markdown', minimized=True)
def notebook_format():
    r'''
    ## Notebook File Format

    Notebooks are **plain Python files** with decorated functions:
    '''


@nb.cell(type='code', reactive=False)
def show_format():
    example = """from streamlit_notebook import st_notebook
    import streamlit as st

    nb = st_notebook(title='my_notebook')

    @nb.cell(type='code', reactive=False)
    def load_data():
        import pandas as pd
        df = pd.read_csv('data.csv')
        print(f"Loaded {len(df)} rows")

    @nb.cell(type='markdown', minimized=True)
    def summary():
        r'''
        ## Data Summary

        Total rows: <<len(df)>>
        '''

    @nb.cell(type='code', reactive=True)
    def interactive():
        threshold = st.slider("Threshold", 0, 100, 50, key='slider_threshold')
        st.write(f"Filtered: {len(df[df['value'] > threshold])} rows");

    nb.render()
    """

    display(example, backend='code', language='python')


@nb.cell(type='markdown', minimized=True)
def deployment_tips():
    r'''
    ## Deployment Best Practices

    ✅ Use `--app` flag for production
    ✅ Set `no_quit=True` for cloud deployments
    ✅ Store notebooks in version control (they're just Python!)
    ✅ Use environment variables for config
    ✅ Test both edit and app modes

    **Cloud Deployment** (Streamlit Community Cloud, etc.):
    ```toml
    # .streamlit/config.toml
    [runner]
    magicEnabled = false

    # In your notebook
    nb = st_notebook(title='app', app_mode=True, no_quit=True)
    ```
    '''


@nb.cell(type='code', reactive=True, minimized=True)
def navigation():
    st.markdown("---")
    from streamlit_notebook.demo_notebooks.helpers import navigation
    navigation()

nb.render()


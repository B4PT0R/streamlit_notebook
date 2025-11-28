Welcome to streamlit-notebook's documentation!
==============================================

**streamlit-notebook** brings Jupyter-style interactive development to Streamlit,
allowing you to develop and deploy data applications seamlessly.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   user_guide
   api_reference
   examples

Features
--------

* **Pure Python Format**: Version control friendly ``.py`` files instead of JSON
* **Jupyter-like Experience**: Cell-by-cell code execution with persistent namespace
* **Selective Reactivity**: Control which cells auto-rerun and which stay one-shot
* **Seamless Deployment**: Run notebooks as Streamlit apps with ``--app`` mode
* **Rich Execution Environment**: IPython-style magics, system commands, and hooks
* **Built-in Editor**: Code editor with syntax highlighting integrated in the UI

Quick Example
-------------

Create a notebook file ``my_notebook.py``:

.. code-block:: python

    from streamlit_notebook import st_notebook
    import streamlit as st

    st.set_page_config(page_title="My Notebook", layout="centered")

    nb = st_notebook(title="My First Notebook")

    @nb.cell(type='markdown')
    def intro():
        '''
        # Welcome to streamlit-notebook!

        This is a markdown cell.
        '''

    @nb.cell(type='code')
    def hello():
        import numpy as np
        data = np.random.randn(100)
        st.line_chart(data)

    # Render the notebook
    nb.render()

Run it::

    st_notebook my_notebook.py

Installation
------------

.. code-block:: bash

    pip install streamlit-notebook

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

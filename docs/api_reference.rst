API Reference
=============

This page contains the API reference for streamlit-notebook.

Core Components
---------------

Notebook
~~~~~~~~

.. autoclass:: streamlit_notebook.notebook.Notebook
   :members:
   :special-members: __init__
   :show-inheritance:

.. autofunction:: streamlit_notebook.notebook.st_notebook

Cells
~~~~~

.. autoclass:: streamlit_notebook.cell.Cell
   :members:
   :special-members: __init__
   :show-inheritance:

.. autoclass:: streamlit_notebook.cell.CodeCell
   :members:
   :show-inheritance:

.. autoclass:: streamlit_notebook.cell.MarkdownCell
   :members:
   :show-inheritance:

.. autoclass:: streamlit_notebook.cell.HTMLCell
   :members:
   :show-inheritance:

Shell (Execution Engine)
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: streamlit_notebook.shell.Shell
   :members:
   :special-members: __init__
   :show-inheritance:

.. autoclass:: streamlit_notebook.shell.ShellResponse
   :members:
   :show-inheritance:

.. autoclass:: streamlit_notebook.shell.Stream
   :members:
   :show-inheritance:

.. autoclass:: streamlit_notebook.shell.StdinProxy
   :members:
   :show-inheritance:

Utility Functions
-----------------

.. automodule:: streamlit_notebook.utils
   :members:
   :undoc-members:
   :show-inheritance:

UI Components
-------------

.. automodule:: streamlit_notebook.cell_ui
   :members:
   :undoc-members:
   :show-inheritance:

Echo Context Manager
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: streamlit_notebook.echo.echo
   :members:
   :special-members: __init__, __call__
   :show-inheritance:

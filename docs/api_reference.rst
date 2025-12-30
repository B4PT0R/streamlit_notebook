API Reference
=============

This page contains the API reference for streamlit-notebook.

Core Components
---------------

Notebook
~~~~~~~~

.. autoclass:: streamlit_notebook.core.notebook.Notebook
   :members:
   :special-members: __init__
   :show-inheritance:

.. autofunction:: streamlit_notebook.core.notebook.st_notebook

Cells
~~~~~

.. autoclass:: streamlit_notebook.core.cell.Cell
   :members:
   :special-members: __init__
   :show-inheritance:

Cell Types
~~~~~~~~~~

.. autoclass:: streamlit_notebook.core.cell_types.BaseCellType
   :members:
   :special-members: __init__
   :show-inheritance:

.. autoclass:: streamlit_notebook.core.cell_types.PyType
   :members:
   :show-inheritance:

.. autoclass:: streamlit_notebook.core.cell_types.MDType
   :members:
   :show-inheritance:

.. autoclass:: streamlit_notebook.core.cell_types.HTMLType
   :members:
   :show-inheritance:

Utility Functions
-----------------

.. automodule:: streamlit_notebook.core.utils
   :members:
   :undoc-members:
   :show-inheritance:

UI Components
-------------

Cell UI
~~~~~~~

.. automodule:: streamlit_notebook.core.cell_ui
   :members:
   :undoc-members:
   :show-inheritance:

Notebook UI
~~~~~~~~~~~

.. autoclass:: streamlit_notebook.core.notebook_ui.NotebookUI
   :members:
   :special-members: __init__
   :show-inheritance:

Echo Context Manager
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: streamlit_notebook.core.echo.echo
   :members:
   :special-members: __init__, __call__
   :show-inheritance:

Audio & Chat
------------

Auto Play
~~~~~~~~~

.. automodule:: streamlit_notebook.core.auto_play
   :members:
   :undoc-members:
   :show-inheritance:

Chat Interface
~~~~~~~~~~~~~~

.. automodule:: streamlit_notebook.core.chat
   :members:
   :undoc-members:
   :show-inheritance:

Templates
---------

.. automodule:: streamlit_notebook.core.templates
   :members:
   :undoc-members:
   :show-inheritance:

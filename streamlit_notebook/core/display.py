from typing import Any
import streamlit as st
from streamlit.errors import DuplicateWidgetID, StreamlitDuplicateElementKey

def display(obj: Any, backend: str | None = None, **kwargs) -> None:
    """Display an object using Streamlit's rendering system.

    Attempts to display the object using the specified backend, falling back to
    ``st.write`` and finally ``st.text(repr(obj))`` if those fail. Used internally
    for displaying cell execution results.

    Args:
        obj: The object to display. If None, nothing is displayed.
        backend: The Streamlit display backend to use. Defaults to 'write'.
            Can be any Streamlit display function name (without the 'st.' prefix):

            - 'write': ``st.write()`` - smart auto-rendering (default)
            - 'json': ``st.json()`` - JSON viewer for dicts/lists
            - 'code': ``st.code()`` - syntax-highlighted code display
            - 'text': ``st.text()`` - plain text display
            - 'markdown': ``st.markdown()`` - markdown rendering
            - 'dataframe': ``st.dataframe()`` - interactive dataframe
            - 'table': ``st.table()`` - static table display
            - Or any other ``st.*`` display function
        **kwargs: Additional keyword arguments to pass to the backend function.
            For example: ``height=400``, ``width='stretch'``, etc.

    Note:
        This is the default display hook for cells. Custom display behavior
        can be implemented via the notebook's display_hook.

    Examples:
        Basic usage with default backend::

            result = 42
            display(result)  # Uses st.write by default

        With specific backend::

            data = {'a': 1, 'b': 2}
            display(data, backend='json')  # Uses st.json

        With backend options::

            df = pd.DataFrame({'a': [1, 2, 3]})
            display(df, backend='dataframe', height=400, width='stretch')

        Use any Streamlit function::

            display(data, backend='plotly_chart', width='stretch')

    See Also:
        :meth:`~streamlit_notebook.notebook.Notebook.display_hook`: Custom display
    """
    if obj is None:
        return

    # Default to 'write' if no backend specified
    if backend is None:
        backend = 'write'

    # Try the requested backend first using getattr
    display_func = getattr(st, backend, None)
    if display_func and callable(display_func):
        try:
            display_func(obj, **kwargs)
            return
        except (DuplicateWidgetID, StreamlitDuplicateElementKey):
            # Silently skip duplicate display calls (can happen when cell runs multiple times in same turn)
            return
        except Exception as e:
            st.warning(f"Failed to display with {backend} backend: {str(e)}")
            pass  # Fall through to fallback

    # Fallback to st.write if requested backend failed or doesn't exist
    if backend != 'write':
        try:
            st.write(obj)
            return
        except (DuplicateWidgetID, StreamlitDuplicateElementKey):
            # Silently skip duplicate display calls
            return
        except Exception as e:
            st.warning(f"Failed to display with write backend: {str(e)}")
            pass  # Fall through to final fallback

    # Final fallback: plain text representation
    try:
        st.text(repr(obj))
    except (DuplicateWidgetID, StreamlitDuplicateElementKey):
        # Silently skip duplicate display calls
        pass
    except Exception:
        # If even repr fails, show error message
        st.error(f"Failed to display object of type {type(obj).__name__}")
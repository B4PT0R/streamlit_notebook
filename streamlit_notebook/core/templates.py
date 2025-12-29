"""Notebook templates for streamlit-notebook."""

from __future__ import annotations

import os


def get_default_notebook_template(title: str = "new_notebook") -> str:
    """Generate default empty notebook template code.

    Creates a minimal notebook script with environment-aware settings.
    Detects app mode via ``ST_NOTEBOOK_APP_MODE`` environment variable
    and adjusts template accordingly.

    Args:
        title: Notebook title to embed in the template.

    Returns:
        Python source code string for a new empty notebook with proper
        imports, configuration, and placeholder cells.
    """
    app_mode = os.getenv("ST_NOTEBOOK_APP_MODE", "").lower() == "true"

    params = [f"title='{title}'"]
    if app_mode:
        params.append("app_mode=True")

    params_str = ", ".join(params)

    return f"""# Streamlit Notebook
# This is a self-contained notebook file

from streamlit_notebook import st_notebook
import streamlit as st

# Create the notebook instance
nb = st_notebook({params_str})

# Add cells below using @nb.cell() decorator
# Example:
# @nb.cell(type='code')
# def cell_0():
#     st.write("Hello, World!")

# Render the notebook
nb.render()
"""

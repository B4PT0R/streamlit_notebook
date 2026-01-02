"""Public package exports for ``streamlit_notebook``."""

from __future__ import annotations

import os
import sys

__all__ = [
    "Notebook",
    "st_notebook",
    "get_notebook",
    "Layout",
    "NotebookConfig",
    "rerun",
    "wait",
]


def _ensure_root_path(file_path: str) -> None:
    os.environ["ROOT_PACKAGE_FOLDER"] = os.path.dirname(os.path.abspath(file_path))


_ensure_root_path(__file__)

# Load .env file if it exists (for ST_NOTEBOOK_APP_MODE and other env vars)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.getcwd(), ".env"))
except ImportError:
    # python-dotenv not installed, skip
    pass

def _just_trying_to_access_launch_app_entry_point() -> bool:
    """
    True when the module is first imported via the CLI entry point 'st_notebook'.
    It's just trying to access launch_app.py without really needing to import the Streamlit 
    or streamlit-notebook machinery at all.

    importing Streamlit at this stage can cause bare-mode warnings and other issues because 
    streamlit runtime isn't yet initialized.
    As a matter of fact, the CLI launcher just wants to delegate to streamlit run main.py + args in a
    subprocess.

    Once the subprocess is running, main.py will reimport the full package
    and Streamlit can be safely imported there.
    """
    return os.path.basename(sys.argv[0]) in {"st_notebook", "st_notebook.exe"}

# Avoid importing Streamlit during CLI startup to prevent bare-mode warnings.
if not _just_trying_to_access_launch_app_entry_point():
    from .core.utils import apply_global_patches
    from .core.rerun import rerun, wait
    from .core.notebook import Notebook, st_notebook, get_notebook, NotebookConfig, Layout
    apply_global_patches()
    


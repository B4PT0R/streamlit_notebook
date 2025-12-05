"""CLI launcher for streamlit-notebook.

This module provides the ``st_notebook`` command-line interface for launching
notebooks in development or production mode.

The launcher handles:
    - Running notebook ``.py`` files directly with Streamlit
    - Launching empty notebooks for new projects
    - App mode deployment with ``--app`` flag
    - Environment variable configuration (``ST_NOTEBOOK_APP_MODE``)
    - File validation and error handling

Command Line Usage::

    # Start empty notebook
    $ st_notebook

    # Run existing notebook in dev mode
    $ st_notebook my_notebook.py

    # Run in locked app mode (deployment)
    $ st_notebook my_notebook.py --app

    # Or via environment variable
    $ ST_NOTEBOOK_APP_MODE=true st_notebook my_notebook.py

Examples:
    Development workflow::

        # Create and iterate on notebook
        $ st_notebook analysis.py

    Production deployment::

        # Deploy as locked app (no code editor)
        $ st_notebook dashboard.py --app

See Also:
    :mod:`~streamlit_notebook.main`: Main script for empty notebooks
    :func:`~streamlit_notebook.notebook.st_notebook`: Notebook factory
"""

from __future__ import annotations

import subprocess
import os
import sys
import argparse

def main() -> None:
    """Launch streamlit-notebook via command line.

    Parses command-line arguments and launches Streamlit with the appropriate
    notebook file or empty notebook template. Supports app mode deployment
    via ``--app`` flag or ``ST_NOTEBOOK_APP_MODE`` environment variable.

    Command Line Arguments:
        notebook (optional): Path to ``.py`` notebook file to run.
            If omitted, launches empty notebook.
        --app: Enable locked app mode (hides editor, production deployment).

    Environment Variables:
        ST_NOTEBOOK_APP_MODE: Set to ``'true'`` to enable app mode.
            Alternative to ``--app`` flag, useful for deployment platforms.

    Raises:
        SystemExit: If notebook file is not found or invalid format.

    Examples:
        Launch empty notebook::

            $ st_notebook

        Run notebook file::

            $ st_notebook my_analysis.py

        Deploy as app::

            $ st_notebook dashboard.py --app

        Via environment variable::

            $ ST_NOTEBOOK_APP_MODE=true st_notebook dashboard.py

    Note:
        The ``--app`` flag sets both ``app_mode=True`` and ``locked=True``,
        creating a production-ready deployment that prevents access to the
        code editor.

    See Also:
        :func:`~streamlit_notebook.notebook.st_notebook`: Notebook creation
        :mod:`~streamlit_notebook.main`: Empty notebook template
    """
    parser = argparse.ArgumentParser(
        description='Launch Streamlit Notebook interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  st_notebook                     # Start empty notebook in dev mode
  st_notebook my_notebook.py      # Run .py notebook in dev mode
  st_notebook my_notebook.py --app  # Run in locked app mode (deployment)

Environment variable (alternative to --app flag):
  ST_NOTEBOOK_APP_MODE=true    # Enable locked app mode
        '''
    )

    parser.add_argument(
        'notebook',
        nargs='?',
        help='Path to notebook file (.py)'
    )
    parser.add_argument(
        '--app',
        action='store_true',
        help='Launch in locked app mode (hides code, prevents editing - for deployment)'
    )

    args = parser.parse_args()

    # Set environment variable based on --app flag
    if args.app:
        os.environ['ST_NOTEBOOK_APP_MODE'] = 'true'

    # If a notebook file path was provided, run it
    if args.notebook:
        if args.notebook.endswith('.py'):
            # For .py notebooks, run them directly with streamlit
            # Check if it's a valid notebook file
            try:
                with open(args.notebook, 'r') as f:
                    if 'from streamlit_notebook import st_notebook' not in f.read():
                        print(f"Warning: {args.notebook} doesn't appear to be a notebook file.")
                        print("Expected to find 'from streamlit_notebook import st_notebook'")
            except FileNotFoundError:
                print(f"Error: File {args.notebook} not found.")
                sys.exit(1)

            # Run the .py notebook directly
            command = ["streamlit", "run", args.notebook]
            subprocess.run(command)

        else:
            print(f"Error: {args.notebook} is not a valid notebook file.")
            print("Supported format: .py")
            sys.exit(1)
    else:
        # No notebook specified, launch empty notebook interface
        script_directory = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_directory, 'main.py')
        command = ["streamlit", "run", script_path]
        subprocess.run(command)

if __name__ == '__main__':
    main()


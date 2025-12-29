"""CLI launcher for streamlit-notebook.

This module provides the ``st_notebook`` command-line interface for launching
notebooks in development or production mode.

The launcher is a thin wrapper around ``streamlit run`` that:
    - Passes all arguments through to streamlit unchanged
    - Defaults to empty notebook template when no file is provided
    - Provides identical behavior to ``streamlit run``

Command Line Usage::

    # Start empty notebook
    $ st_notebook

    # Run existing notebook in dev mode
    $ st_notebook my_notebook.py

    # Run in locked app mode (use -- separator for script args)
    $ st_notebook my_notebook.py -- --app

    # Or via environment variable
    $ ST_NOTEBOOK_APP_MODE=true st_notebook my_notebook.py

Examples:
    Development workflow::

        # Create and iterate on notebook
        $ st_notebook analysis.py

    Production deployment::

        # Deploy as locked app (no code editor)
        $ st_notebook dashboard.py -- --app

Note:
    Arguments are passed to ``streamlit run`` as follows:

    - Options **before** ``--`` are passed to streamlit itself
    - Options **after** ``--`` are passed to your script (available in sys.argv)
    - The ``--app`` flag must come after ``--`` to be detected by the notebook

    This matches standard ``streamlit run`` behavior.

    You can pass custom flags for your own use cases::

        $ st_notebook my_notebook.py -- --app --debug --mode=production

    These will be available in ``sys.argv`` and can be used to customize
    notebook behavior (e.g., enable debug logging, switch data sources, etc.).

See Also:
    :mod:`~streamlit_notebook.main`: Main script for empty notebooks
    :func:`~streamlit_notebook.notebook.st_notebook`: Notebook factory
"""

from __future__ import annotations

import subprocess
import os
import sys

def main() -> None:
    """Launch streamlit-notebook via command line.

    Acts as a wrapper around ``streamlit run`` that defaults to the empty
    notebook template when no file is provided. All arguments are passed
    through to streamlit unchanged, providing identical behavior.

    Command Line Arguments:
        All arguments are passed directly to ``streamlit run``.

        If no notebook file is provided, launches the empty notebook template.
        Script arguments (like ``--app``) must be separated with ``--``.

    Environment Variables:
        ST_NOTEBOOK_APP_MODE: Set to ``'true'`` to enable app mode.
            Alternative to ``-- --app`` flag, useful for deployment platforms.

    Raises:
        SystemExit: If streamlit command fails.

    Examples:
        Launch empty notebook::

            $ st_notebook

        Run notebook file::

            $ st_notebook my_analysis.py

        Deploy as app (use -- separator for script args)::

            $ st_notebook dashboard.py -- --app

        Via environment variable::

            $ ST_NOTEBOOK_APP_MODE=true st_notebook dashboard.py

    Note:
        This command behaves identically to ``streamlit run``. The only
        difference is that running ``st_notebook`` with no arguments
        launches an empty notebook template instead of failing.

        Arguments are passed through as follows:
        - Options **before** ``--`` go to streamlit (e.g., ``--server.port``)
        - Options **after** ``--`` go to your script (e.g., ``--app``)
        - The ``--app`` flag must be after ``--`` to reach your notebook code

        Custom flags after ``--`` are available in ``sys.argv`` for custom logic::

            $ st_notebook notebook.py -- --app --debug --data-source=prod

        You can then use these in your notebook to implement custom behavior.

    See Also:
        :func:`~streamlit_notebook.notebook.st_notebook`: Notebook factory
        :mod:`~streamlit_notebook.main`: Empty notebook template
    """

    # Set environment variable to indicate we're in launcher mode
    # This allows save() to work properly without triggering Streamlit reloads
    env=os.environ.copy()
    env['ST_NOTEBOOK_LAUNCHER_MODE'] = 'true'


    # Get all arguments after 'st_notebook' command
    args = sys.argv[1:]

    # Determine if a notebook file is provided
    # Look for the first non-flag argument (doesn't start with - or --)
    notebook_file = None
    for arg in args:
        if arg == '--':
            # Separator reached, no file found before it
            break
        if not arg.startswith('-'):
            # Found a positional argument (likely the notebook file)
            notebook_file = arg
            break

    # Always delegate to main.py to avoid file locking and hot-reload issues
    # This allows the notebook file to be edited and saved while running
    script_directory = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_directory, 'main.py')

    if notebook_file is None:
        # Launch empty notebook interface
        command = ["streamlit", "run", script_path]
        # Add any arguments that were provided (e.g., -- --app)
        if args:
            command.extend(args)
    else:
        # Pass notebook file via argument to main.py
        # Remove the notebook file from args and pass it after --
        remaining_args = [arg for arg in args if arg != notebook_file]
        command = ["streamlit", "run", script_path]
        # Add streamlit options (before --)
        if remaining_args and '--' in remaining_args:
            separator_idx = remaining_args.index('--')
            streamlit_args = remaining_args[:separator_idx]
            script_args = remaining_args[separator_idx:]  # Includes the --
            command.extend(streamlit_args)
            command.extend(script_args)
            command.append(f"--file={notebook_file}")
        elif remaining_args:
            # Args exist but no separator, treat as streamlit args
            command.extend(remaining_args)
            command.extend(["--", f"--file={notebook_file}"])
        else:
            # No other args, just pass the file
            command.extend(["--", f"--file={notebook_file}"])

    subprocess.run(command, env=env)


if __name__ == '__main__':
    main()

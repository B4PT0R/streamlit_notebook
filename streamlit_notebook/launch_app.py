import subprocess
import os
import sys
import argparse

def main():
    """
    Runs the streamlit app by calling 'streamlit run .../main.py'
    Supports command-line arguments for notebook path and app mode settings.
    """
    parser = argparse.ArgumentParser(
        description='Launch Streamlit Notebook interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  st_notebook                          # Start empty notebook in dev mode
  st_notebook my_notebook.stnb         # Open notebook in dev mode
  st_notebook my_notebook.stnb --app-mode        # Open in app mode (preview)
  st_notebook my_notebook.stnb --app-mode --locked  # Locked app mode (deployment)

Environment variables:
  ST_NOTEBOOK_MODE=app     # Enable app mode
  ST_NOTEBOOK_LOCKED=true  # Lock app mode (requires ST_NOTEBOOK_MODE=app)
        '''
    )

    parser.add_argument(
        'notebook',
        nargs='?',
        help='Path to .stnb notebook file (optional)'
    )
    parser.add_argument(
        '--app-mode',
        action='store_true',
        help='Launch in app mode (hides code cells, minimal UI)'
    )
    parser.add_argument(
        '--locked',
        action='store_true',
        help='Lock app mode (prevents toggling back to notebook mode, for deployment)'
    )

    args = parser.parse_args()

    script_directory = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_directory, 'main.py')

    # Set environment variables based on flags
    if args.app_mode:
        os.environ['ST_NOTEBOOK_MODE'] = 'app'
    if args.locked:
        os.environ['ST_NOTEBOOK_LOCKED'] = 'true'
        # If locked is set, app mode must be enabled
        if not args.app_mode:
            os.environ['ST_NOTEBOOK_MODE'] = 'app'

    command = ["streamlit", "run", script_path]

    # If a notebook file path was provided, add it to the command
    if args.notebook:
        if args.notebook.endswith('.stnb'):
            command.append(args.notebook)
        else:
            print(f"Error: The file {args.notebook} is not a valid .stnb file.")
            sys.exit(1)

    subprocess.run(command)

if __name__ == '__main__':
    main()


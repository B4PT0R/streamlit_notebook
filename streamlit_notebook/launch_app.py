import subprocess
import os
import sys
import argparse

def main():
    """
    Runs the streamlit app by calling 'streamlit run <notebook.py>' or 'streamlit run .../main.py'
    Supports command-line arguments for notebook path and app mode settings.

    For .py notebook files, delegates directly to streamlit run.
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
                    if 'from streamlit_notebook import notebook' not in f.read(500):
                        print(f"Warning: {args.notebook} doesn't appear to be a notebook file.")
                        print("Expected to find 'from streamlit_notebook import notebook'")
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


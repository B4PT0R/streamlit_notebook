import subprocess
import os
import sys
import urllib.parse

def main():
    """
    Runs the streamlit app by calling 'streamlit run .../main.py'
    Optionally accepts a path to a .stnb notebook file as a command-line argument.
    """
    script_directory = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_directory, 'main.py')
    
    command = ["streamlit", "run", script_path]

    # If a notebook file path was provided, add it to the command
    if len(sys.argv) > 1:
        notebook_path = sys.argv[1]
        if notebook_path.endswith('.stnb'):
            command.append(notebook_path)
        else:
            print(f"Error: The file {notebook_path} is not a valid .stnb file.")
            return

    subprocess.run(command)

if __name__ == '__main__':
    main()


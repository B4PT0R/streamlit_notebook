import subprocess
import os

def main():
    """
    Runs the streamlit app by calling 'streamlit run .../streamlit_notebook/main.py'
    """


    # Get the directory of the current script
    script_directory = os.path.dirname(os.path.abspath(__file__))

    # Path to the Streamlit app
    script_path = os.path.join(script_directory, 'main.py')

    # Command to run the Streamlit app as a list
    command = ["streamlit", "run", script_path]

    # Execute the command
    subprocess.run(command)

if __name__ == '__main__':
    main()
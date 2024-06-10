import subprocess
import os

def main():
    """
    Runs the streamlit app by calling 'streamlit run .../main.py'
    """

    # Get the directory of the current script
    script_directory = os.path.dirname(os.path.abspath(__file__))

    # Command to run the Streamlit app
    command = f"streamlit run {os.path.join(script_directory, 'main.py')}"

    # Execute the command
    subprocess.run(command, shell=True)

if __name__ == '__main__':
    main()
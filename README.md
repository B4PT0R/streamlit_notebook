
# Streamlit Notebook

`streamlit_notebook` is a reactive notebook interface for Streamlit.

Pretty much like a Jupyter notebook, you can create and run Code cells (supporting Streamlit commands) or Markdown/HTML cells. These cells will be executed dynamically and their output will be rendered under each cell box.

The main feature of this notebook is to bridge the gap between a persistent python interactive session and a Streamlit app, to achieve selective reactivity in your notebook. A custom shell is implemented with its own internal namespace which is preserved through reruns and allows to achieve session persistence reducing greatly the need to cache results or store them in `st.session_state` manually. The possibility to make chosen cells auto-rerun (possibly as fragments) based on UI events allows to use streamlit code seamlessly and manage UI reactivity with fine-grained control. 

This notebook is meant to be fully compatible with Streamlit and doesn't introduce much complexity beyond standard Streamlit functionning. All Streamlit commands should work out of the box. If it's not the case, it should be reported as a bug.

I hope users already familiar with Streamlit will have great fun with this notebook.

## Technical Explanations

(Skip if bored by long reading)

In a standard python interactive console/notebook, code blocks/cells are run sequentially, and only one time (unless you choose to restart the session or rerun cells manually). The python shell maintains a persistent namespace (the "state" of the python session) so that the variables/objects declared by running a code cell are accessible in the next. But it doesn't provide in itself a suitable framework to implement real time updates triggered by external UI events. This is why all GUI frameworks rely on a foundational "mainloop", basically an infinite while loop, collecting external events from a UI, triggering computations according to the collected events, sending back signals to the frontend to refresh the UI state, and so on. This mainloop is generally running in a global, persistent python session, so that the backend data is preserved in the namespace and can be reused in the next loop. The python session only ends when the mainloop if terminated (you exit the program).

In the other hand, a Streamlit app works by running a whole python script several times in a looped fashion (the loop itself being taken care of by the asynchronous streamlit server). This loop enacts the GUI mainloop of your Streamlit app, which provides a flexible foundation to implement reactive web programming. Basically, any event changing the state of the UI will trigger a full rerun of the backend script to let it receive and process the new data, run backend computations accordingly, trigger refresh of the ui state, and so on. This design choice comes at the cost of loosing persisence of the python session between reruns: any rerun restarts the whole python session (resets its namespace to initial state), and all backend data produced is lost at the end of the script (unless it is saved in the external session_state storage).

One way to work around this situation and restore persitence of the python session in a streamlit app is to declare a custom Python shell object, with its own internal namespace, and store it in the session_state storage. We can then redirect inputs and outputs of this shell to custom frontend widgets and thus implement a persistent python console with a Streamlit interface (which is nice already). But the cool thing is that we can also use this custom shell to run streamlit commands within the preserved internal namespace (not the vanishing global one). The effect will be the same as running it in the main streamlit script, except that changes made to the internal namespace will be permanent. By providing an additional mechanism to make relevant cells rerun on every streamlit loop, the streamlit code will get re-executed whenever the UI tiggers an event, just as it would in a normal Streamlit script, and update the internal namespace accordingly.

This setting allows to get the best of both worlds. Using single-shot cells for costly computations that need to run only once, as well as reactive cells that will deal with interactive widgets and being rerun automatically based on UI events. These cells may also run as fragments to avoid refreshing the whole notebook's UI where it's not needed.

## Features

- Switch to "App" mode by hiding code cells and notebook specific controls.
- Create and delete cells easily, move cells up and down, control how they execute.
- Create reactive Markdown or HTML cells by adding formatting tags `<<my_expression>>` that let you insert the current value of any global / state variable or evaluated expression into the text/code.
- Special `display` function that you can use even in one-shot cells to display python data in a pretty manner to the frontend (uses `st.write` as a default backend). 
- Automatic evaluation and display of single expressions. Can be selectively deactivated using semicolons at the end of the expression or by switching the display mode in the sidebar menu.
- Easily download / upload your notebooks as json files.
- The whole notebook UI can be controled dynamically from code cells. This feature will be refined as I advance this project, but can already be played with. You can refer to the notebook object as `notebook` from within the session and call its methods programmaticaly. For instance you can programmatically create, edit and run cells:

```python
# Create a new cell and run it
cell=notebook.new_cell(code="print('Hello!')",type="code")
cell.run()
```

```python
# Edit and existing cell and run it
cell=notebook.cells[1]
cell.code="print('Hello world!')"
cell.run()
```


## Screenshot

![In notebook mode](./streamlit_notebook/app_images/st_notebook_demo.png)


![In app mode](./streamlit_notebook/app_images/st_notebook_demo_2.png)

## Installation

```bash
pip install streamlit-notebook
```

## Usage

You may open a new notebook from anywhere by just running `st_notebook` in the terminal.

You may as well create a python file like so :

```python 
# notebook.py
from streamlit_notebook import st_notebook

st_notebook()
```

and run it using `streamlit run notebook.py` from the terminal.

The `st_notebook()` function imported from the package is a complete app in itself rather than a single component, and only serves as an entry point.

The app is meant to be run locally on your computer, the browser only being used as a GUI interface. It can still be deployed to be used online, but keep in mind that in this case, the code will run remotely in the cloud server and you will be able to use only preinstalled packages. It is discouraged to introduce any sensitive data in your session, as there is no inherent limitation on the code that can be run in the notebook (appart from limitations on the python packages that can be used). The app doesn't provide any additional security beyond those already implemented by Streamlit. A clever malvolent user could potentially reach your data or spy your session.

The app is available online [here](https://st-notebook.streamlit.app/) as a demo.

## Contribution

This App is still in early stage of development and any feedbacks / contributions are welcome!

I think it has a lot of potential and would benefit greatly from community engagement.

In case you want to give feedback or report a bug / suggest an improvement. Please open an new issue.

If you wish to contribute to this project, you're welcome to:

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

- june 11th 2024:
    - Added HTML cells
    - Enabled uploading / downloading the notebook as a json file
    - Added a demo notebook (more to come)
    - Fixed st.echo that didn't work in an interactive environment 

- june 24th 2024:
    - Introduced the custom shell object and redirection utilities to integrate the shell smoothly in the notebook, making the session persistent across reruns.
    - Introduced ast parsing with asttokens library to evaluate and selectively display chosen expressions on the frontend, based on the presence of a trailing semicolon.
    - Added the `display` function, used for rich display of data in the notebook (using `st.write` as a backend) in one-shot cells.

- july 2nd 2024:
    - Improved dynamic cell creation, edition, and execution.
    - Added a couple demo notebooks to showcase these features. 
# Streamlit Notebook Documentation

Welcome to the documentation for the Streamlit Notebook project! This guide will walk you through the features and usage of the notebook, helping you get started with creating interactive and reactive notebooks using Streamlit.

## Table of Contents

1. [Installation](#installation)
2. [Starting a New Notebook](#starting-a-new-notebook)
3. [Notebook Interface](#notebook-interface)
4. [Cell Types](#cell-types)
   - [Code Cells](#code-cells)
   - [Markdown Cells](#markdown-cells)
   - [HTML Cells](#html-cells)
5. [Cell Operations](#cell-operations)
   - [Creating and Deleting Cells](#creating-and-deleting-cells)
   - [Moving Cells](#moving-cells)
   - [Controlling Cell Execution](#controlling-cell-execution)
6. [Reactive Cells](#reactive-cells)
7. [Displaying Data](#displaying-data)
8. [Notebook Management](#notebook-management)
   - [Downloading and Uploading Notebooks](#downloading-and-uploading-notebooks)
   - [App Mode](#app-mode)
9. [Notebook Control from Code](#notebook-control-from-code)
10. [Persistent Python Session](#persistent-python-session)
11. [Streamlit Compatibility](#streamlit-compatibility)
12. [Contributing](#contributing)
13. [License](#license)

## Installation

To install the Streamlit Notebook package, run the following command:

```bash
pip install streamlit-notebook
```

## Starting a New Notebook

You can start a new notebook in two ways:

1. Run `st_notebook` in the terminal:

   ```bash
   st_notebook
   ```

   A new notebook will open in your webbrowser. The working directory of the python session will be the directory from which you run the command.

2. You may also create a Python file with the following code and run it using `streamlit run`:

   ```python
   # notebook.py
   from streamlit_notebook import st_notebook

   st_notebook()
   ```

   Then, run the following command in the terminal:

   ```bash
   streamlit run notebook.py
   ```

   For now the terminal command and python st_notebook function take no parameters, I will improve the API at some point to let you pass a notebook file as parameter to let you open it directly, amongst other useful settings.

## Notebook Interface

The Streamlit Notebook provides an intuitive interface similar to Jupyter notebooks. The main components of the interface include:

- Sidebar: Allows you to control notebook settings, download/upload notebooks, and access demo notebooks.
- Control Bar: Provides buttons to create new code, markdown, and HTML cells.
- Cells: Individual units of code, markdown, or HTML that can be executed and rendered.

## Cell Types

The Streamlit Notebook supports three types of cells:

### Code Cells

Code cells allow you to write and execute Python code, including Streamlit commands. The code is executed in a persistent Python session, and the output is rendered below the cell.

### Markdown Cells

Markdown cells support writing content in Markdown format. You can use Markdown syntax to format text, create headings, lists, links, LaTeX formulas and more. The Markdown content is rendered as HTML in the notebook.

### HTML Cells

HTML cells allow you to write HTML code directly in the notebook. The HTML code is rendered as-is in the notebook output.

## Cell Operations

### Creating and Deleting Cells

To create a new cell, click on the corresponding button in the control bar: "New code cell", "New Markdown cell", or "New HTML cell". The new cell will be added below the existing cells.

To delete a cell, click on the "❌" button in the cell's menu bar.

### Moving Cells

You can move cells up or down using the "🔺" and "🔻" buttons in the cell's menu bar. This allows you to rearrange the order of cells in the notebook.

### Controlling Cell Execution

Each cell has a "Run" button that allows you to execute the cell's content. You can also enable "Auto-Rerun" for a cell, which will automatically re-execute the cell whenever a UI event triggers a notebook rerun. The fragment toggle is used when you want a widget event to rerun only the code cell in which it is created and dealt with.

## Reactive Cells

Streamlit Notebook supports reactive cells, which allow you to create dynamic widgets or content that updates based on changes in variables or widget interactions.

By turning the auto-rerun parameter in a code cell, you may run streamlit commands to create any kind of interactive widget, including text inputs, buttons, dynamic plots, editable dataframes, forms and so on. The fragment toggle enables to avoid reruning the entire notebook when a UI event coming from the fragment would require a rerun to process the change. This way only the fragment cell reruns.  

In Markdown and HTML cells, you can use the `<<expression>>` syntax to insert the current value of a variable or an evaluated expression into the text or code. For example:

```markdown
The current value of x is: <<x>>
```

If the value of `x` changes, the rendered output will automatically update to reflect the new value.

## Displaying Data

Streamlit Notebook provides a `display` function that you can use to display Python data in a pretty manner. The `display` function uses `st.write` under the hood to render the data. It can be used even in one-shot cells to display data without requiring reruns of the cell.

If you turn the auto-display parameter on, any single expression in your code cell will be evaluated and displayed automatically. 
You can disable the display of a given expression by using a trailing semilcolon ";". 

## Notebook Management

### Downloading and Uploading Notebooks

You can download the current notebook as a JSON file by clicking on the "Download notebook" button in the sidebar. This allows you to save your work locally.

To upload a previously downloaded notebook, click on the "Upload notebook" button in the sidebar and select the JSON file. The notebook will be loaded into the interface.

### App Mode

Streamlit Notebook provides an "App mode" that hides the code cells and notebook-specific controls, giving your notebook a cleaner presentation. To switch to App mode, toggle the "App mode" option in the sidebar.

## Notebook Control from Code

You can control the notebook UI dynamically from code cells. The notebook object is accessible through `st.notebook`, allowing you to modify its properties and behavior.

For example, you can hide the logo by setting `st.notebook.show_logo = False` in a code cell.

This feature also enables creating new cells and run them programatically.

## Persistent Python Session

One of the key features of Streamlit Notebook is its persistent Python session. The notebook maintains a custom shell with its own internal namespace, which is preserved across reruns. This allows you to retain the state of variables and objects between cell executions.

The persistent session reduces the need for manual caching or storing results in `st.session_state`, making it easier to work with long-running computations and interactive widgets.

## Streamlit Compatibility

Streamlit Notebook is designed to be fully compatible with Streamlit. All Streamlit commands should work seamlessly within the notebook environment. If you encounter any issues or incompatibilities, please report them as bugs.

## Contributing

Streamlit Notebook is an open-source project, and contributions are welcome! If you encounter any bugs, have suggestions for improvements, or want to contribute new features, please open an issue or submit a pull request on the project's GitHub repository.

To contribute, follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them.
4. Push your changes to your forked repository.
5. Open a pull request on the original repository.

Please ensure that your code follows the project's coding style and includes appropriate documentation.

## License

Streamlit Notebook is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

---

We hope this documentation helps you get started with Streamlit Notebook and enables you to create interactive and reactive notebooks effortlessly. If you have any questions or need further assistance, please don't hesitate to reach out to the project maintainers or the community.

Happy notebooking with Streamlit Notebook!


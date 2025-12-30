# Streamlit Notebook

The reactive notebook powered by Streamlit.

Streamlit Notebook combines the interactive development experience of Jupyter notebooks with the reactivity and deployment simplicity of Streamlit apps. Write code in notebook-style cells with a professional-grade Python shell that maintains state across reruns, then deploy the exact same file as a production-ready Streamlit application.

Designed with AI integration in mind, it comes equipped with its own full-featured AI agent having full dynamic control over the notebook (requires an OpenAI API key). It can create, edit, run code cells, read documents, view images, support voice interaction, etc.

## Table of Contents

- [Overview](#overview)
- [Demo](#demo)
- [Installation](#installation)
- [Quick Start](#quick-start)
  - [Create a notebook](#create-a-notebook)
  - [Run it](#run-it)
  - [How it works?](#how-it-works)
- [Notebook Interface - Core Concepts](#notebook-interface---core-concepts)
  - [Cell Types](#cell-types)
  - [Persistent Shell](#persistent-shell)
  - [100% Standard Streamlit API](#100-standard-streamlit-api)
- [Real-World Example](#real-world-example)
- [Easy Deployment](#easy-deployment)
- [Development Features](#development-features)
  - [Two Modes](#two-modes)
  - [File Management](#file-management)
  - [Rich Content](#rich-content)
  - [Advanced Display Control with display()](#advanced-display-control-with-display)
- [Advanced Features](#advanced-features)
  - [Streamlit Fragments](#streamlit-fragments)
  - [Programmatic API](#programmatic-api)
- [AI Agent Integration](#ai-agent-integration)
  - [Installation](#installation-1)
  - [Features](#features)
  - [Quick Start](#quick-start-1)
  - [Accessing the Agent Programmatically](#accessing-the-agent-programmatically)
  - [Agent Capabilities](#agent-capabilities)
  - [Configuration](#configuration)
  - [Example Workflow](#example-workflow)
  - [Best Practices](#best-practices)
  - [Advanced: Custom Tools](#advanced-custom-tools)
- [CLI Options](#cli-options)
- [Deployment](#deployment)
  - [Local Testing](#local-testing)
  - [Streamlit Cloud](#streamlit-cloud)
  - [Docker](#docker)
  - [Production Best Practices](#production-best-practices)
  - [Multi-Notebook Deployments](#multi-notebook-deployments)
- [Use Cases](#use-cases)
- [Contributing](#contributing)
- [License](#license)
- [Changelog](#changelog)

## Overview

We all know Jupyter as the go-to for interactive programming, but it comes with its own limitations:
- JSON format notebooks
- converting notebooks to deployable apps isn't straightforward. 
- limited UI widget ecosystem, 
- limited UI/namespace reactivity
- limited dynamic creation of widgets
- limited programmatic creation and execution of cells
- kernel / frontend dichotomy
- Huge dependency tree

Streamlit on the other hand is great for fast reactive apps development, with a huge components ecosystem (possibility to wrap any web component), and easy deployment on the cloud. But its "rerun the whole script" execution model (without namespace persistence!) can sometimes turn cumbersome, and it lacked a proper notebook ergonomics.

Streamlit Notebook attempts to give you the best of both worlds.

- **Development:** Cell-by-cell execution, full widget support, selective reactivity, persistent namespace, fast iteration, saved as readable and runnable `.py` files.
- **Deployment:** Easily publish your notebook as a Streamlit app, no special runtime, deploy in couple of clicks, works anywhere Streamlit works.

## Demo

Try the hosted demo: [st-notebook.streamlit.app](https://st-notebook.streamlit.app/)

## Installation

**With everything** (recommended for most users):
Includes a complete datascience stack and a full featured AI agent.
```bash
pip install streamlit-notebook[full]
```

**Basic installation** (core notebook functionality only):
```bash
pip install streamlit-notebook
```

**With data science stack**:
```bash
pip install streamlit-notebook[datascience]
```

**With ai agent dependencies**:
```bash
pip install streamlit-notebook[agent]
```

**documents & web scrapping dependencies**:
```bash
pip install streamlit-notebook[documents]
```

**With ai agent + advanced document reading capabilities**:
So that the agent can read a wider range of sources (various file types, web pages, ...).
```bash
pip install streamlit-notebook[agent-full]
```

**What's included:**

- **Core**: `streamlit`, `streamlit-code-editor`, `asttokens`, `python-dotenv`,`filetype`,`pydub`
- **datascience** extra: `matplotlib`, `numpy`, `seaborn`, `pandas`, `pillow`, `openpyxl`, `requests`, `pydub`, `graphviz`, `altair`, `plotly`, `bokeh`, `pydeck`, `scipy`, `sympy`, `scikit-learn`, `vega-datasets`
- **agent** extra: `openai`,`numpy`,`pydantic`,`tiktoken`,`regex`,`pyyaml`,`prompt-toolkit`
- **documents** extra: `requests`,`beautifulsoup4`,`lxml`,`trafilatura`,`PyPDF2`,
`python-docx`,`odfpy`,`pillow`,`selenium`,`get-gecko-driver`

## Quick Start

### Create a notebook

**Option 1: Start from the UI**
```bash
st_notebook  # Opens empty notebook interface
```
Create cells interactively, then click "Save notebook" to save as a `.py` file.

**Option 2: Write the file directly**
```python
# analysis.py
from streamlit_notebook import st_notebook
import streamlit as st

# Create a notebook instance
nb = st_notebook(title='analysis')

# Define cells
@nb.cell(type='code')
def setup():
    import pandas as pd
    df = pd.read_csv("data.csv")
    print(f"Loaded {len(df)} rows")

@nb.cell(type='code', reactive=True)
def explore():
    col = st.selectbox("Column", df.columns)
    st.line_chart(df[col])

# Render the notebook
nb.render()
```

### Run it

You can open it with the st_notebook entry point

```bash

st_notebook analysis.py          # Development mode - full notebook interface
st_notebook analysis.py -- --app # Locked app mode - clean interface, code cells hidden
```

Or run it directly with Streamlit! (same result)
```bash
streamlit run analysis.py          # Development mode
streamlit run analysis.py -- --app # Locked app mode
```

The main difference lies in that streamlit-notebook won't allow you to save changes to the notebook file on which `streamlit run` is currently looping on, which isn't a limitation if you open it with the dedicated `st_notebook` entry point.

### How it works?

A bit of magic needs to happen under the hood to make it possible. Fell free to skip this section if you're not into the technical details. 

Here's a quick overview:

When you run `streamlit run analysis.py`, Streamlit will execute the notebook script in an async loop, reruning it after any UI event, so that each run may process the new state of the UI. Each step of the loop is called a `run`, which is a complete execution of the scipt top to bottom. Let's examine what happens during the first run:

- We import the modules and the required `st_notebook` factory.
- `st_notebook` first attempts to get an existing notebook instance from `st.session_state`. Since it is the first run, none is found, so it creates one with the provided parameters. 
- The `@cell` decorator is used to capture the source code of the functions' bodies and add the corresponding cells to the notebook instance. **This happens only if the notebook instance is not yet 'initialized' (boolean state)**. The decorator is designed to just do nothing if it is (to avoid re-adding the same cells over and over as the script reruns). 
- `nb.render()` sets `nb.initialized=True` if it wasn't, and renders it on screen (full notebook interface).

In subsequent runs of the script, `st_notebook` will find an existing notebook instance in state and just return it, ignoring the parameters. The `@cell` decorators will this time ignore the cell definitions (already initialized) and the script will merely execute `nb.render()` to refresh the notebook instance. The nice thing is that the notebook instance returned by `st_notebook` need not be the same as the one created in the first run. If some UI interaction switches it in state, the new instance will be rendered instead.

As a result, you may open another notebook file from the interface. The notebook will load the code in memory, initialize a new notebook instance from it, store it in state, and rerun the app. In the next run `st_notebook` will fetch the NEW instance, and `nb.render()` will show it, all while still looping on the initial file!

This is why calling `streamlit run analysis.py` still allows you to change notebook live from the interface.

Note: the functions defining the cells will never get called. Doing so would result in errors, as they refer to variables defined out of their local scopes (in other cells!). It's really a nice thing here that python allows to define erroneous function objects, even decorate them, without throwing an exception as long as we don't attempt to call them (lazy evaluation). They still know the file and line range in which they are defined, which is enough for the decorator to retrieve their raw source code. Makes them usable as mere "code bags", ie. containers for source code that gets extracted and used elsewhere.

## Notebook Interface - Core Concepts

### Cell Types

**One-shot cells:** Run only when you trigger them manually. Used for imports, initialization, data loading, expensive computations.

**Reactive cells:** Toggle the `Reactive` option on any code cell to make it reactive. These will rerun automatically on every UI interaction and update the python namespace accordingly. Used for widgets and reactive displays.

This selective reactivity lets you separate expensive setup from interactive exploration.

### Persistent Shell

All cells execute in an embedded interactive shell (see [Pynteract](https://github.com/B4PT0R/pynteract) for more details), stored in `st.session_state`, that maintains a single long-lived Python session. Unlike regular Streamlit apps that restart from scratch on every rerun, imports, variables, and computed results will persist in the shell's namespace across UI interactions.

**Example:**
```python
from streamlit_notebook import st_notebook
import streamlit as st

nb = st_notebook(title="simple_counter")

@nb.cell(type='code',reactive=False)
def cell_0():
    # One-shot cell - Run it once to initialize the counter
    counter=0 


@nb.cell(type='code', reactive=True)
def cell_1():
    # Reactive cell - Reruns on every UI interaction
    if st.button("Increment"):
        counter+=1
    st.write(f"Current counter value: {counter}")

nb.render()
```

Since cell_0 doesn't rerun spontaneously, the counter is not reset to 0 on every interaction. cell_1 will thus work with the last known counter value (persisted in the shell's namespace), and update it when the button is clicked.

### 100% Standard Streamlit API

Every Streamlit widget, chart, and component works out of the box in reactive cells. Just copy-paste your existing Streamlit code there.

```python
@nb.cell(type='code', reactive=True)
def widgets():
    # Standard Streamlit code - nothing new to learn
    value = st.slider("Select value", 0, 100)
    st.metric("Current value", value)
    st.bar_chart([value, value*2, value*3])
```

Streamlit Notebook doesn't do anything too hacky with Streamlit's internals and only uses the stable Streamlit API for its own functionning. You can think of it as an extension, rather than a replacement. It will adapt seamlessly to any future versions of Streamlit you may want to install, thus letting you benefit from new widgets or features in your notebooks.

*Note*: It uses the new `width='stretch'` instead of the now deprecated `use_container_width=True` parameter to control its own widgets layout. It also supports the `scope` parameter in its rerun mechanism as well as `run_every` for fragments, thus requiring Streamlit 1.52.0 or higher.

## Real-World Example

Building a stock price analysis dashboard. This example uses real data from the vega_datasets package (included in the datascience stack) and can be copy-pasted and run directly:

```python
from streamlit_notebook import st_notebook
import streamlit as st

nb = st_notebook(title='stock_dashboard')

@nb.cell(type='code')
def setup():
    import pandas as pd
    import altair as alt
    from vega_datasets import data

@nb.cell(type='code')
def load_data():
    df = data.stocks()
    df['date'] = pd.to_datetime(df['date'])
    print(f"Loaded {len(df):,} records for {df['symbol'].nunique()} stocks")

@nb.cell(type='code', reactive=True)
def filters():
    st.markdown("### Stock Analysis Dashboard")
    symbols = st.multiselect("Select stocks", df['symbol'].unique(), default=['AAPL', 'GOOG'])
    date_range = st.date_input("Date range", [df['date'].min(), df['date'].max()])

@nb.cell(type='code', reactive=True)
def dashboard():
    filtered = df[df['symbol'].isin(symbols)] if symbols else df
    if date_range and len(date_range) == 2:
        filtered = filtered[(filtered['date'] >= pd.Timestamp(date_range[0])) &
                           (filtered['date'] <= pd.Timestamp(date_range[1]))]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Selected Stocks", len(symbols))
    with col2:
        st.metric("Avg Price", f"${filtered['price'].mean():.2f}")
    with col3:
        st.metric("Total Records", f"{len(filtered):,}")

    chart = alt.Chart(filtered).mark_line().encode(
        x='date:T',
        y='price:Q',
        color='symbol:N'
    ).properties(height=400)
    st.altair_chart(chart, width='stretch');

nb.render()
```

## Easy deployment

Once you're done working on your notebook you may run it using:

```bash
streamlit run stock_dashboard.py -- --app
```
Now the same file runs as a locked production app with restricted interface and no visible/editable code.
This prevents untrusted users to run arbitrary code in the cloud environment.
Your notebook can thus safely be published as an online app without more overhead.

The dedicated environment variable does the same as the flag:

```bash
export ST_NOTEBOOK_APP_MODE=true # or use a .env file
streamlit run stock_dashboard.py
```

Useful when you can't modify the command directly (e.g., in Streamlit cloud platform).

## Development Features

### Two Modes

**Notebook Mode** (development):
- Code editor for each cell
- Cell management (create, run, delete, insert, change type, reorder)
- Execution controls (Run Next, Run All, Restart Session, Clear All Cells)
- Save/Open notebooks
- Demo notebooks library

**App Mode** (deployment):
- Restricted interface
- Code editors hidden
- Interactive widgets remain functional
- Clean Streamlit app appearance

In development, you may toggle between modes with the `app view` switch in the sidebar. In production, just set the `ST_NOTEBOOK_APP_MODE` or use the `--app` flag to prevent users toggling back to notebook mode.

### File Management

**From the sidebar:**
- **New** button: creates a new notebook from scratch.
- **Save** button: saves notebook to `./notebook_title.py`
- **Open** button: dropdown of all `.py` notebooks in current directory, or drag/drop/browse files
- **Demo notebooks**: load pre-built example notebooks from the library

**From code:**
See the Programmatic API section for file operations via code cells.

### Rich Content

**Rich display**

Cell results are automatically displayed with pretty formatting when possible (anything that `st.write` can handle).

Control how expression results appear:
- `all` - show every expression result
- `last` - show only the last expression (default)
- `none` - suppress automatic display

Configurable in the sidebar settings.

You may also :
- add a trailing `;` at the end of a line to bypass automatic display
- use the `display()` function to selectively display a given result. More on this below.

### Advanced Display Control with `display()`

The `display()` function provides full control over how results are rendered, with access to any Streamlit display backend and all its parameters.

**Basic usage:**
```python
@nb.cell(type='code')
def load_data():
    import pandas as pd
    df = pd.read_csv('data.csv')

    # Simple display (uses st.write by default)
    display(df)
```

Under the hood, `display(obj, backend='write', **kwargs)` is mostly equivalent to `st.<backend>(obj, **kwargs)`

**Choose any Streamlit backend:**
```python
@nb.cell(type='code', reactive=False)
def visualize():
    data = {'name': 'Alice', 'age': 30, 'city': 'Paris'}

    # Use st.json with expansion control
    display(data, backend='json', expanded=True)

    # Use st.code with syntax highlighting
    code = "def hello():\n    return 'world'"
    display(code, backend='code', language='python')

    # Use st.dataframe with additional parameters
    import pandas as pd
    df = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})
    display(df, backend='dataframe',
            height=400,
            width='stretch',
            hide_index=True)
```

**Available backends:**
Any Streamlit display function works (without the `st.` prefix):
- `'write'` - Smart auto-rendering (default)
- `'json'` - JSON viewer with expansion control
- `'dataframe'` - Interactive DataFrame with custom height, column config, etc.
- `'table'` - Static table display
- `'code'` - Syntax-highlighted code
- `'markdown'` - Rendered markdown with optional HTML
- `'text'` - Plain text
- `'plotly_chart'`, `'altair_chart'`, `'pyplot'` - Chart displays with container options
- Any other `st.*` display function

**Why use `display()` over `st.*()`?**

`display` is designed to store the result and parameters in the cell, so that the notebook can automatically redisplay it after reruns without re-executing the cell. Direct `st.*()` commands need to rerun to stay on screen and thus work only in reactive cells.

This is particularly powerful in **non-reactive cells** where you get the performance of one-time execution combined with rich, customizable output that persists across reruns.

It also works seamlessly in reactive cells, where it behaves exactly like `st.*()` but with the added benefit of storing the result in the cell, useful for inspection and debugging.

### Markdown/HTML cells 

Add rich formatted text or layouts to your notebook with Markdown and HTML cells. They support variable interpolation using the `<<any_expression>>` syntax. The expression will be evaluated and replaced in the code.
If the value changes, the displayed content will change as well.

```markdown
# Analysis Results

We loaded << len(df) >> rows.
The mean value is << df['value'].mean() >>.
```

### System commands and magics

Ipython style commands and magics are supported.
Let's demonstrate this by showing a simple example:
`display(obj, backend='write', **kwargs)` is mostly equivalent to `st.<backend>(obj, **kwargs)`
```python
#Cell 1

#define a new magic
@magic
def upper(text_content):
    if text_content:
        return text_content.upper()

#call it in a single line starting with % and the name of the magic function
%upper This is a test!
```
Result:
```
THIS IS A TEST!
```

The magic input is always processed as a string (the rest of the line following the %<command>) but supports string templating

```python
%upper os.listdir()
```
Result:
```
OS.LISTDIR()
```

vs.

```python
%upper {os.listdir()}
```
Result:
```
['ANALYSIS.PY', 'DATA.CSV', 'README.MD']
```



With `%%`, the whole cell starting at second line is considered the magic input.

```python
#Cell 2
%%upper
All the content of
the cell goes in the
magic input
```
Result:
```
ALL THE CONTENT OF
THE CELL GOES IN THE
MAGIC INPUT
```

Note: A subset of most commonly used IPython magics are available.

To run a system command, use `!` or `!!`.

```python
!echo "Hello World"
```
Stdout:
```
Hello World
```

`!!` captures and returns the result instead of streaming to stdout (stderr still streams):
```python 
result = !!echo "Hello World"
result
```
Result:
```
Hello World
```

To run a full-cell bash script use the `%%bash` cell magic.

For more information about `Pynteract` capabilities as a shell, refer [to the project's repo]().

Disclaimer: The shell is *NOT* an exact replica of Ipython and external API/internal implementation will differ. My goal is to provide a practical and versatile coding environment matching the common needs of interactive programming. Yet, you might encounter situations where you feel like some useful features of Ipython are missing, if so please add a feature request.

## Advanced Features

### Streamlit Fragments

You can enable the "Fragment" option in the Advanced settings panel of a reactive cell to run the cell as a [Streamlit fragment](https://docs.streamlit.io/library/api-reference/performance/st.fragment) for faster, scoped updates:

```python
@nb.cell(type='code', reactive=True, fragment=True)
def fast_widget():
    # Only this cell reruns on interaction
    value = st.slider("Value", 0, 100)
    st.write(f"Selected: {value}")
```

Fragments isolate code reruns and UI updates to just the fragment's scope. When a widget defined inside a fragment triggers a UI event, only that fragment's code is rerun and its UI updated.

Beware that widgets in other reactive cells on the page won't refresh even if they depend on variables changed by the fragment.
So, in general, it's better to group in a same fragment subsets of widgets and that are supposed to react to eachother.

Note: A variable that's changed by a fragment is immediately updated in the namespace and can be used elsewhere in the notebook.

To rerun a fragment cell on every given time delta use the `run_every` parameter

```python
@nb.cell(type='code', reactive=True, fragment=True, run_every=1)
def clock():
    # This cell will rerun every second, not rerunning uselessly the rest of the notebook interface
    with st.empty():
        st.write(datetime.now().strftime("%H:%M:%S"))
```

This is useful to monitor background tasks or create "real-time" widgets, for instance reading data from sensors or APIs at regular intervals and updating the display accordingly.

### Programmatic API

The notebook instance is exposed in the shell's namespace as `__notebook__`, enabling full programmatic control from the shell or code cells.

This level of programmatic control is quite unique to streamlit-notebook and enables workflows not easily achievable in Jupyter or traditional notebooks.

This is especially powerful for automation, AI agents, and dynamic notebook generation.

#### Accessing the Notebook

```python
# From any code cell
nb = __notebook__

# Access notebook properties
print(f"Title: {nb.config.title}")
print(f"Number of cells: {len(nb.cells)}")
print(f"App mode: {nb.config.app_mode}")
```

#### Creating Cells

```python
# Create a new code cell
cell = nb.new_cell(
    type="code",
    code="import pandas as pd\ndf = pd.DataFrame({'x': [1,2,3]})",
    reactive=False,
    fragment=False,
    run_every=None
)

# Create a markdown cell
md_cell = nb.new_cell(
    type="markdown",
    code="# Results\nThe data has <<len(df)>> rows."
)

# Create an HTML cell
html_cell = nb.new_cell(
    type="html",
    code="<div style='color: red;'><<result>></div>"
)
```

#### Modifying Cells

```python
# Access cells by index or key
first_cell = nb.cells[0]
specific_cell = nb.get_cell("my_cell_key")

# Modify cell code (automatically updates UI)
first_cell.code = "import numpy as np\nprint('Updated!')"

# Change cell type
first_cell.type = "markdown"  # "code", "markdown", or "html"

# Toggle cell options
first_cell.reactive = True
first_cell.fragment = True

# Get cell properties
print(f"Cell ID: {first_cell.id}")
print(f"Cell index: {first_cell.index}")
print(f"Cell type: {first_cell.type}")
print(f"Has run: {first_cell.has_run_once}")
```

#### Running Cells

```python
# Run a specific cell
cell.run()

# Run all cells in order
nb.run_all_cells()

# Run the next unexecuted cell
nb.run_next_cell()
```

#### Managing Cell Order

```python
# Move cells up/down
first_cell.move_down()
last_cell.move_up()

# Change cell position directly
cell.index = 2  # Move to position 2

# Insert new cells relative to existing ones
cell.insert_above()  # Inserts a new code cell above (default: empty code cell)
cell.insert_below()  # Inserts a new code cell below (default: empty code cell)

# Insert with custom parameters
new_cell = cell.insert_above(type="markdown", code="# My Title")  # Returns the new cell
new_cell = cell.insert_below(type="code", code="print('hello')", reactive=True)
```

#### Deleting Cells

```python
# Delete a specific cell
cell.delete()

# Delete by key
nb.delete_cell("cell_key")

# Clear all cells
nb.clear_cells()

# Reset a cell (clear outputs and execution state)
cell.reset()
```

#### Session Management

**Restart the Python session:**

Clear the namespace and restart the Python interpreter to start fresh.

```python
nb.restart_session()
```

**Quit the application:**

Cleanly shutdown the Streamlit server. This performs cleanup operations and then terminates the server process.

```python
nb.quit()
```

This can be useful for automation scripts or when the AI agent needs to close the application at the user's request.

**Smart rerun control:**

The notebook provides an improved rerun API with flexible timing control, fragment support (Streamlit 1.52+), and better compatibility.

Signature: `rerun(scope:Literal["app", "fragment"] = "app", wait:bool|float = True)`

```python

nb=__notebook__

# Full app rerun (default)
nb.rerun()  # wait = True : Soft non-interrupting rerun resolved at end of current cycle
```

This requests a rerun at the end of the current Streamlit cycle, letting it finish executing without interrupting subsequent operations.

```python
# Fragment-scoped rerun (Streamlit 1.52+)
@st.fragment
def my_fragment():
    if st.button("Refresh"):
        nb.rerun(scope = "fragment")  # Only reruns this fragment
```

Fragment reruns are immediate and don't use delay management since they're typically fast operations.

The `wait` parameter controls the timing of the rerun. If you request a delay, and the script reaches end of cycle before the delay expires, the rerun will wait until the delay is over before executing.

```python
# Delayed rerun
nb.rerun(wait=1.5)
```

This is useful to ensure animations or toasts display have time to complete before the page refreshes.

```python
# Hard rerun (immediate)
nb.rerun(wait=False)
```

Triggers an immediate rerun, equivalent to standard `st.rerun()` where it doesn't fail (e.g., in widget callbacks). In circumstances where `st.rerun()` would fail, it falls back to requesting a soft rerun as soon as possible (cancelling any pending delays).

**Note:** In the notebook environment, `st.rerun()` is automatically upgraded to use this enhanced implementation with delay management and fragment support. You can use it directly or via `nb.rerun()` - both work identically.

**Control pending reruns with `wait()`:**

The `wait()` function lets you control any pending reruns without requesting one.

```python
# Somewhere in the code: request a rerun
nb.rerun()

# ...

# Somewhere else : Request a delay before resolving the pending rerun
st.balloons()
nb.wait(2.0)  # Ensures the pending rerun waits 2 seconds from this point
```

The parameter works similarly to `rerun()`:
- `wait(2.0)` - Add a 2-second delay before any pending rerun
- `wait()` or `wait(True)` or `wait(0)` - Do nothing (no additional delay)
- `wait(False)` - Execute the pending rerun immediately, cancelling any previous requested delays

```python
nb.rerun(wait=5.0)  # Request rerun with 5 second delay
# ... some code ...
nb.wait(False)  # Changed your mind - execute the rerun now!
```

#### File Operations

```python
# Save notebook to file
nb.save()  # Saves to default location (./notebook_title.py)
nb.save("custom_name.py")  # Save with custom filename

# Open/load a notebook
nb.open("my_notebook.py")
nb.open() # Opens a new empty notebook

# Check if a file is a valid notebook
if nb.is_valid_notebook(source_code):
    nb.open(source_code)
```

#### Notifications

```python
# Show toast notifications with guaranteed visibility
nb.notify("Cell executed successfully!", icon="✅")
nb.notify("Error occurred", icon="⚠️", delay=2.0)
```

#### Converting to Python Code

```python
# Get the complete Python code representation
python_code = nb.to_python()
print(python_code)  # Shows the @nb.cell decorated version
```

#### Inspecting Notebook State

Get complete JSON-serializable state of the notebook, including all information about cells and their execution state:

```python
# Get full notebook info (includes notebook settings and cell states)
info = nb.get_info()  # minimal=False by default

# Access notebook metadata
print(f"Notebook: {info['config']['title']}")
print(f"Cell count: {info['cell_count']}")
print(f"App mode: {info['config']['app_mode']}")

# Iterate through cells
for cell_state in info['cells']:
    print(f"Cell {cell_state['id']} ({cell_state['type']}):")
    print(f"  Has run: {cell_state['has_run_once']}")
    print(f"  Code length: {len(cell_state['code'])} chars")

    if cell_state.get('stdout'):
        print(f"  Stdout: {cell_state['stdout'][:50]}...")

    if cell_state.get('exception'):
        print(f"  Error: {cell_state['exception']['message']}")

# Get minimal info (only cell definitions, no execution state)
minimal_info = nb.get_info(minimal=True)
# Includes: notebook metadata + minimal cell data (key, type, code, reactive, fragment, run_every)

# Get individual cell state
cell = nb.cells[0]
full_state = cell.to_dict(minimal=False)
# Includes: id, index, language, has_run_once, visible, stdout,
# stderr, results, exception

minimal_state = cell.to_dict()  # minimal=True by default
# Only: key, type, code, reactive, fragment

# Serialize to JSON for AI agents or external tools
import json
context = json.dumps(nb.get_info(), indent=2)
```

#### API Reference

**Notebook Methods:**
- `new_cell(type, code, reactive, fragment, run_every)` - Create a new cell
- `get_cell(index_or_key)` - Get cell by position or key
- `get_info(minimal)` - Get complete notebook info including settings and cell states (default: full state)
- `delete_cell(key)` - Remove a cell by key
- `clear_cells()` - Remove all cells
- `run_all_cells()` - Execute all cells in order
- `run_next_cell()` - Execute the next unexecuted cell
- `restart_session()` - Clear namespace and restart Python session
- `quit()` - Cleanly shutdown the Streamlit server
- `rerun(scope, wait)` - Trigger a Streamlit rerun (scope: "app" or "fragment", wait: True/False/float)
- `wait(delay)` - Control pending reruns (delay, execute now, or do nothing)
- `notify(message, icon, delay)` - Show toast notification
- `save(filepath)` - Save notebook to file
- `open(source)` - Load notebook from file or source code. If no source is provided, creates a new empty notebook.
- `to_python()` - Get Python code representation
- `is_valid_notebook(source)` - Check if source is valid notebook

**Cell Methods:**
- `run()` - Execute the cell
- `reset()` - Clear outputs and execution state
- `move_up()` - Move cell up one position
- `move_down()` - Move cell down one position
- `insert_above(type, code, reactive, fragment, run_every)` - Insert new cell above (returns new cell). Defaults: type="code", code="", reactive=False, fragment=False, run_every=None
- `insert_below(type, code, reactive, fragment, run_every)` - Insert new cell below (returns new cell). Defaults: type="code", code="", reactive=False, fragment=False, run_every=None
- `delete()` - Remove this cell
- `to_dict(minimal)` - Get dictionary representation (default: minimal, set minimal=False for full state)

**Cell Properties:**
- `code` (read/write) - Cell code content
- `type` (read/write) - Cell type: "code", "markdown", or "html"
- `reactive` (read/write) - Auto-rerun on UI changes
- `fragment` (read/write) - Run as Streamlit fragment
- `run_every` (read/write) - Auto-rerun interval in seconds (requires fragment=True, Streamlit 1.52+)
- `index` (read/write) - Cell position in notebook
- `key` (read-only) - Unique cell identifier
- `id` (read-only) - Readable cell identifier combining index and key like `Cell[index](key)`
- `language` (read-only) - Cell language ("python" or "markdown")
- `has_run_once` (read-only) - Whether cell has executed with current code

**Notebook Properties:**
- `cells` (list) - All cells in the notebook
- `title` (str) - Notebook title
- `app_mode` (bool) - Whether in locked app mode
- `shell` - Python shell instance
- `current_cell` - Currently executing cell

## AI Agent Integration

Streamlit Notebook includes a full-featured AI agent powered by OpenAI that provides intelligent assistance with full control over the notebook environment.

### Installation

Install with agent support:

```bash
pip install streamlit-notebook[agent]
```

For advanced document reading capabilities (PDF, DOCX, web pages, etc.):

```bash
pip install streamlit-notebook[agent-full]
```

### Features

The AI agent comes with powerful capabilities:

- **Full Notebook Control**: Create, edit, delete, and run code cells programmatically
- **Code Execution**: Run Python code and see results in real-time
- **Vision Support**: Analyze images, charts, and visual content
- **Voice Interaction**: Optional voice input/output for hands-free operation
- **Document Reading**: Read and analyze various file formats (PDF, DOCX, Excel, etc.)
- **Web Scraping**: Fetch and analyze content from web pages
- **Tool System**: Extensible architecture for adding custom capabilities

### Quick Start

1. **Set your OpenAI API key** in your .bashrc or a `.env` file:
   ```bash
   OPENAI_API_KEY=sk-...
   ```

2. **Enable the agent** in your notebook by clicking the chat icon in the sidebar

3. **Start chatting** - the agent can help you write code, analyze data, create visualizations, and more

### Accessing the Agent Programmatically

The agent is available in the shell namespace as `__agent__`:

```python
@nb.cell(type='code')
def interact_with_agent():
    # Access agent configuration
    print(f"Current model: {__agent__.config.model}")

    # Define and register a custom tool
    def my_custom_tool(param: str) -> str:
        """
        description: A custom tool for processing input parameters
        parameters:
            param:
                type: string
                description: The parameter to process
        required:
            - param
        """
        return f"Processed: {param}"

    # Register the tool (auto-extracts metadata from YAML docstring)
    __agent__.add_tool(my_custom_tool)

    print("Custom tool registered!")
```

### Agent Capabilities

**Code Generation & Execution:**
- Ask the agent to create cells with specific functionality
- Agent can run cells and see the output
- Automatically handles errors and suggests fixes

**Data Analysis:**
- Upload datasets and ask for analysis
- Agent creates visualizations and statistical summaries
- Iteratively refine analysis based on conversation

**Documentation:**
- Agent reads markdown/HTML cells
- Can reference previous cell outputs
- Maintains context throughout the conversation

**Voice Mode** (optional):
- Enable in agent settings
- Speak your requests naturally
- Agent responds with voice output
- Great for hands-free coding sessions

### Configuration

Access agent settings through the sidebar:

- **Model Selection**: Choose amongst a variety of OpenAI models (gpt-5.1, gpt-5.1-mini, etc.)
- **Temperature**: Control response creativity
- **Token Limits**: Configure context and completion limits
- **Vision**: Toggle image/chart analysis
- **Voice**: Enable/disable voice interaction
- **Custom System Prompt**: Customize agent behavior

### Example Workflow

```python
# Natural language data analysis workflow:
# 1. User uploads CSV through sidebar
# 2. Asks agent: "Analyze this dataset and create a dashboard"
# 3. Agent:
#    - Creates a cell to load and inspect the data
#    - Creates cells for data cleaning
#    - Generates multiple visualization cells
#    - Adds markdown cells explaining findings
#    - All without user writing any code!
```

### Best Practices

**Security:**
- Never share notebooks containing API keys
- Use st.secrets for sensitive data
- Agent respects app mode - won't be loaded in production

**Performance:**
- Agent responses count toward OpenAI API usage
- Use specific requests for faster responses
- Complex tasks may require multiple iterations

**Collaboration:**
- Agent-generated cells are regular cells - edit freely
- Mix agent-created and manual cells seamlessly
- Agent learns from conversation context

### Advanced: Custom Tools

Extend the agent with domain-specific capabilities:

```python
@nb.cell(type='code')
def add_custom_tools():

    # Option 1: Direct function call
    def analyze_sentiment(text: str) -> str:
        """
        description: Analyze the sentiment of given text
        parameters:
            text:
                type: string
                description: The text to analyze for sentiment
        required:
            - text
        """
        # Your implementation here
        return "positive"

    __agent__.add_tool(analyze_sentiment)

    # Option 1: Using decorator syntax
    @__agent__.add_tool
    def fetch_stock_price(ticker: str) -> dict:
        """
        description: Fetch current stock price for a given ticker symbol
        parameters:
            ticker:
                type: string
                description: Stock ticker symbol (e.g., AAPL, GOOGL)
        required:
            - ticker
        """
        # Your implementation here
        return {"ticker": ticker, "price": 150.00}

    st.success("Custom tools registered!")
```

**Key Points:**
- **YAML Docstrings**: Tool metadata is automatically extracted from the function's docstring in YAML format
- **Decorator Syntax**: Use `@__agent__.add_tool` for clean, declarative tool registration
- **Direct Call**: Use `__agent__.add_tool(func)` for conditional or dynamic registration

Now the agent can use these tools in its responses!

## CLI Options

The schema for passing CLI arguments is:

`st_notebook Optional[notebook_file] Optional[options_1] -- Optional[options_2]`

or equivalently,

`streamlit run [notebook_file] Optional[options_1] -- Optional[options_2]`

Options before `--` are for Streamlit (e.g., `--server.port 8080`), options after `--` are for your script (e.g., `--app`).

Example with both:
```bash
st_notebook analysis.py --server.port 8080 -- --app  # Custom port + app mode
```

**Custom flags:** You can pass your own flags after `--` to implement custom behavior:
```bash
streamlit run dashboard.py -- --app --data-source=production --debug
```

Then somewhere in your notebook:
```python
import sys

# sys.argv contains only [options_2] group of CLI arguments (as a single string)

# Check for custom flags
is_debug = '--debug' in sys.argv
data_source = next((arg.split('=')[1] for arg in sys.argv if arg.startswith('--data-source=')), 'dev')

if is_debug:
    st.write(f"Debug mode enabled, using {data_source} data source")
```

**Built-in flags:**

- `--app`: Locks the notebook in app mode (production mode) where users cannot edit cells or toggle back to edit mode
- `--no-quit`: Disables the quit button and prevents programmatic shutdown via `nb.quit()`. Useful for cloud deployments where the server should not be terminated by users

Example:
```bash
# Deploy with app mode and disable quit functionality
st_notebook dashboard.py -- --app --no-quit
```

Alternatively, you can use environment variables:
```bash
# Using environment variables
ST_NOTEBOOK_APP_MODE=true ST_NOTEBOOK_NO_QUIT=true st_notebook dashboard.py
```

## Deployment

### Local Testing

First make sure your notebook looks and runs nice as an app. 

```bash
# Test in locked app mode (production simulation)
st_notebook my_notebook.py -- --app
```

### Streamlit Cloud

1. Create `requirements.txt`:
    ```
    streamlit-notebook
    # ... other dependencies
    ```

2. Create `.streamlit/config.toml` (optional - for page config):
    ```toml
    [theme]
    primaryColor = "#F63366"
    backgroundColor = "black"
    ```

3. Create `.env` file to enable locked app mode and disable quit:
    ```bash
    ST_NOTEBOOK_APP_MODE=true
    ST_NOTEBOOK_NO_QUIT=true
    ```

4. Push to GitHub:
    ```bash
    git add my_notebook.py requirements.txt .env
    git commit -m "Add dashboard"
    git push
    ```

5. Deploy on [share.streamlit.io](https://share.streamlit.io):
   - Connect your GitHub repo
   - Select `my_notebook.py` as main file
   - Click "Deploy"

Since notebooks are just Python files, Streamlit Cloud runs them directly — no wrapper needed.

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY my_notebook.py .

EXPOSE 8501

# Option 1: Use flags for app mode and disabled quit
CMD ["streamlit", "run", "my_notebook.py", "--", "--app", "--no-quit"]

# Option 2: Use environment variables
# ENV ST_NOTEBOOK_APP_MODE=true
# ENV ST_NOTEBOOK_NO_QUIT=true
# CMD ["streamlit", "run", "my_notebook.py"]
```

Build and run:
```bash
docker build -t my-dashboard .
docker run -p 8501:8501 my-dashboard
```

Deploy to AWS ECS, Google Cloud Run, Azure Container Apps, or any container platform.

### Production Best Practices

✅ **Do:**
- Use one shot cells for expensive operations
- Test with `--app` flag locally first
- Setup a `.env` file with `ST_NOTEBOOK_APP_MODE=true` to ensure locked app mode once deployed.
- Include `streamlit-notebook` and all external dependencies in `requirements.txt`
- Use `st.secrets` for secrets (API keys, database credentials, etc.)

❌ **Don't:**
- Allow code editing in production deployments (the user could read `st.secrets` or run malicious scripts)
- Hardcode API keys or credentials in any file exposed in the public repo.
- Assume filesystem persistence. Changes you make to the files will be discarded when the container reboots. (use databases/cloud storage instead)

### Multi-Notebook Deployments

Deploy multiple related notebooks in a single repo, allowing users to navigate between them while keeping everything in locked app mode.

**Use case:** A data engineer creates several analysis notebooks (Sales, Customers, Forecasting) and wants to deploy them all as apps with simple navigation.

**Setup:**
```
my-analytics/
├── .env                          # ST_NOTEBOOK_APP_MODE=true
├── requirements.txt
├── sales_analysis.py
├── customer_segmentation.py
└── forecasting_model.py
```

**How it works:**
- Deploy to Streamlit Cloud pointing to any notebook as the main file
- Users see "Open notebook" dropdown to switch between notebooks
- `ST_NOTEBOOK_APP_MODE=true` in `.env` ensures ALL notebooks are locked apps
- Safe for end users—no code editing allowed on any notebook

This is perfect for demos, dashboards, or sharing multiple analyses with stakeholders without creating separate deployments for each notebook.

## Use Cases

**Data Exploration → Dashboard:** Build analysis interactively with selective reactivity, then deploy as a polished dashboard with the `--app` flag.

**Prototyping → Production:** Develop proof-of-concept in notebook mode with instant feedback, deploy as locked app without rewriting code.

**Interactive Reports:** Blend narrative (Markdown/HTML) with live data, widgets, and dynamic visualizations in a single document.

**Teaching & Demos:** Create interactive tutorials with executable code cells that students can run and modify step-by-step.

**AI-Assisted Development:** Use the integrated AI agent to generate code, analyze data, create visualizations, and build entire workflows through natural language. The agent has full programmatic control and can be extended with custom tools via `__agent__`.

## Contributing

Contributions welcome! File issues for bugs or feature requests. Submit PRs for improvements.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-idea`)
3. Commit changes (`git commit -m "Add feature"`)
4. Push (`git push origin feature/my-idea`)
5. Open a pull request

## License

MIT License—see [LICENSE](LICENSE).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history and release notes.

---

**Develop with notebooks. Deploy as apps.** 🚀

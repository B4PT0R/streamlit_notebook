# Streamlit Notebook

The reactive notebook powered by Streamlit.

Streamlit Notebook combines the interactive development experience of Jupyter notebooks with the deployment simplicity of Streamlit apps. Write code in notebook-style cells with a professional-grade Python shell that maintains state across reruns, then deploy the exact same file as a production-ready Streamlit application.

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

Streamlit on the other hand is great for fast reactive apps development, with a huge components ecosystem, and easy deployment on the cloud. But its "rerun the whole script" execution model (without namespace persistence!) can sometimes turn cumbersome, and it lacked a proper notebook ergonomics.

Streamlit Notebook attempts to give you the best of both worlds.

- **Development:** Cell-by-cell execution, full widget support, selective reactivity, persistent namespace, fast iteration, saved as readable and runnable `.py` files.
- **Deployment:** Easily publish your notebook as a Streamlit app, no special runtime, deploy in couple of clicks, works anywhere Streamlit works.

## Demo

Try the hosted demo: [st-notebook.streamlit.app](https://st-notebook.streamlit.app/)

## Installation

```bash
pip install streamlit-notebook
```

The package comes equiped with the latest version of `streamlit` and a comprehensive starter data-science pack including: 
`matplotlib, numpy, seaborn, pandas, pillow, openpyxl, requests,
pydub, graphviz, altair, plotly, bokeh, pydeck, scipy, sympy,
scikit-learn, vega-datasets`

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

st.set_page_config(page_title="Analysis")

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

st_notebook analysis.py         # Development mode - full notebook interface
st_notebook analysis.py --app   # Locked app mode - clean interface, code cells hidden
```

Or run it directly with Streamlit! (same result)
```bash
streamlit run analysis.py        # Development mode
streamlit run analysis.py --app  # Locked app mode
```

### How it works?

A bit of magic needs to happen under the hood to make it possible
- `st_notebook` first attempts to get an existing notebook instance from `st.session_state`, if none is found, it creates one. 
- The `@cell` decorator is used to capture the source code of the functions' bodies and add the corresponding cells to the notebook instance. **This happens only at the first pass of the script**, and the decorator is no-oped afterwards (to avoid adding the same cells over and over as the script reruns). 
- `nb.render()` finally takes care of fetching and displaying the current notebook instance from state.

Subsequent runs of the script will ignore the cell definitions and merely loop on `nb = st_notebook(...)` and `nb.render()` to refresh whatever notebook instance is living in the session's state.

Note: the functions defining the cells will never get called. Doing so would result in errors, as they refer to variables defined out of their local scopes (in other cells!). It's really a nice thing here that python allows to define erroneous function objects, even decorate them, without throwing an exception as long as we don't attempt to call them (lazy evaluation). They still know the file and line range in which they are defined, which is enough for the decorator to retrieve their raw source code. Makes them usable as mere "code bags", ie. containers for source code that gets extracted and executed elsewhere.

## Core Concepts

### Cell Types

**One-shot cells:** Run only once when you click Run. Used for imports, data loading, expensive computations.

**Reactive cells:** Toggle the `Reactive` option on any code cell to make it reactive. These will rerun automatically on every UI interaction and update the python namespace accordingly. Used for widgets and reactive displays.

This selective reactivity lets you separate expensive setup from interactive exploration.

### Persistent Shell

All cells execute in a shared long-lived Python session. Unlike regular Streamlit apps that restart from scratch on every rerun, imports, variables, and computed results persist across UI interactions.

**Example:**
```python
@nb.cell(type='code')
def load_data():
    import pandas as pd
    df = pd.read_csv("large_file.csv") # One shot cell, runs only once

@nb.cell(type='code', reactive=True)
def explore():
    threshold = st.slider("Threshold", 0, 100)
    st.write(df[df['value'] > threshold]) # no need to redefine df, even after reruns
```

Cell 1 loads data once. Cell 2 reruns on slider changes. Both execute in the same namespace.

### Standard Streamlit APIs

Every Streamlit widget, chart, and component works out of the box. Just copy-paste your existing Streamlit code into cells.

```python
@nb.cell(type='code', reactive=True)
def widgets():
    # Standard Streamlit code - nothing new to learn
    value = st.slider("Select value", 0, 100)
    st.metric("Current value", value)
    st.bar_chart([value, value*2, value*3])
```

## Real-World Example

Building a stock price analysis dashboard. This example uses real data from the vega_datasets package (included) and can be copy-pasted and run directly:

```python
from streamlit_notebook import st_notebook
import streamlit as st

st.set_page_config(page_title="Stock Dashboard", layout="wide")
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
    st.altair_chart(chart, use_container_width=True);

nb.render()
```

## Easy deployment

Once you're done working on your notebook you may run it using:

```bash
streamlit run stock_dashboard.py --app
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
- Cell management (create, delete, insert, change type, reorder)
- Execution controls (Run Next, Run All, Restart Session, Clear All Cells)
- Save/Open notebooks
- Demo notebooks library

**App Mode** (deployment):
- Restricted interface
- Code editors hidden
- Interactive widgets remain functional
- Clean Streamlit app appearance

In development, you may toggle between modes with the sidebar switch, or run with enforced app mode to prevent users toggling back to notebook mode.

### File Management

**Save/Load from UI:**
- **Save** button: saves notebook to `./notebook_title.py`
- **Open** button: dropdown of all `.py` notebooks in current directory, or drag/drop/browse files
- **Demo notebooks**: load pre-built example notebooks from the library

**Save/Load from code:**
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
- use the `display` function to selectively display a given result

*Tip*: Use `display` instead of `st.write` to pretty print results in one-shot cells. They basically do the same, but the difference is that `display` is designed to store the reference to the object, allowing the notebook to redraw it on screen after every rerun without having to rerun the cell.  

**Markdown/HTML cells** 

Add rich formatted text or layouts to your notebook with Markdown and HTML cells. They support variable interpolation using the `<<any_expression>>` syntax. The expression will be evaluated and replaced in the code.
If the value changes, the displayed content will change as well.

```markdown
# Analysis Results

We loaded << len(df) >> rows.
The mean value is << df['value'].mean() >>.
```

**System commands and magics**

Ipython style commands and magics are supported.
Let's demonstrate this by defining a new magic to integrate a basic AI assistant in the session.

```python
#Cell 1

#system command to install the openai package
!pip install openai

from openai import OpenAI

#simple agent class
class Agent:
    
    def __init__(self):
        self.messages=[]
        self.client=OpenAI() #will use the OPENAI_API_KEY provided as env variable if any

    def add_message(self,**kwargs):
        self.messages.append(kwargs)

    def __call__(self,prompt):
        
        self.add_message(role="user",content=prompt)

        response=self.client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=self.messages
        ).choices[0].message.content

        self.add_message(role="assistant",content=response)

        return response

#create an agent instance 
agent=Agent()

#define a new magic to call our agent
@magic
def ai(text_content):
    if text_content:
        response=agent(text_content)
        display(response) # we use display instead of print for prettier markdown rendering

#call it in a single line starting with % (takes the rest of the line after the %<command> as input string)
%ai Hello, this is a test!
```

With `%%`, the whole cell starting at second line is considered the magic input.

```python
#Cell 2
%%ai
All the content of
the cell goes in the
magic input
```

Note: Only the mechanism is supported, no predefined magics are provided (yet) so you have to declare your own magics.

Warning: contrary to Ipython, `!` and `!!` here work the same as `%` and `%%`, namely they distinguish between single line and full-cell magics. They just execute the input as a system command/script.

Disclaimer: The shell is *NOT* meant to be an exact replica of Ipython. My goal is to provide a practical and versatile coding environment matching the common needs of interactive programming. Yet, you might encounter situations where you feel like some useful features of Ipython are missing, if so please add a feature request.

## Advanced Features

### Streamlit Fragments

You may toggle the "Fragment" option of a reactive cell to run the cell as a [Streamlit fragment](https://docs.streamlit.io/library/api-reference/performance/st.fragment) for faster, scoped updates:

```python
@nb.cell(type='code', reactive=True, fragment=True)
def fast_widget():
    # Only this cell reruns on interaction
    value = st.slider("Value", 0, 100)
    st.write(f"Selected: {value}")
```

This way the page reloads only the UI fragment in which the interaction happens.
Beware that other widgets on the page won't refresh even if they depend on variables changed by the fragment.
So, in general, it's better to group in a same fragment subsets of widgets and that are supposed to react to eachother.

Note: A variable that's changed by a fragment is immediately updated in the namespace and can be used elsewhere in the notebook. The isolation is just ui-side, not backend-side.

### Programmatic API

The notebook instance is exposed in the shell's namespace as `__notebook__`, enabling full programmatic control from code cells. This is especially powerful for automation, AI agents, and dynamic notebook generation.

#### Accessing the Notebook

```python
# From any code cell
nb = __notebook__

# Access notebook properties
print(f"Title: {nb.title}")
print(f"Number of cells: {len(nb.cells)}")
print(f"App mode: {nb.app_mode}")
```

#### Creating Cells

```python
# Create a new code cell
cell = nb.new_cell(
    type="code",
    code="import pandas as pd\ndf = pd.DataFrame({'x': [1,2,3]})",
    reactive=False,
    fragment=False
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
print(f"Cell rank: {first_cell.rank}")
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
cell.rank = 2  # Move to position 2

# Insert new cells relative to existing ones
cell.insert_above()  # Inserts a new cell above this one
cell.insert_below()  # Inserts a new cell below this one
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

```python
# Restart the Python session (clears namespace)
nb.restart_session()

# Control reruns with delays
nb.rerun(delay=1.5)  # Requires a rerun once the current execution is complete, with a minimal 1.5s delay from the calling point
nb.rerun(no_wait=True)  # Immediate rerun (when possible)

# Request delay without triggering rerun
nb.wait(2.0)  # Ensures any future rerun waits 2 seconds
```

#### File Operations

```python
# Save notebook to file
nb.save()  # Saves to default location (./notebook_title.py)
nb.save("custom_name.py")  # Save with custom filename

# Open/load a notebook
nb.open("my_notebook.py")

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

Get complete information about cells and their execution state:

```python
# Get full state of all cells (includes outputs and metadata)
state = nb.get_cells_state()  # minimal=False by default

for cell_state in state:
    print(f"Cell {cell_state['id']} ({cell_state['type']}):")
    print(f"  Has run: {cell_state['has_run_once']}")
    print(f"  Code length: {len(cell_state['code'])} chars")

    if cell_state.get('stdout'):
        print(f"  Stdout: {cell_state['stdout'][:50]}...")

    if cell_state.get('exception'):
        print(f"  Error: {cell_state['exception']['message']}")

# Get individual cell with full state
cell = nb.cells[0]
full_state = cell.to_dict(minimal=False)
# Includes: id, rank, language, has_run_once, visible, stdout,
# stderr, results, exception

# Get minimal cell definition (for saving)
minimal_state = cell.to_dict()  # minimal=True by default
# Only: key, type, code, reactive, fragment
```

#### Complete Example: AI Agent Integration

```python
# Cell 1: Setup AI agent with context awareness
from openai import OpenAI
import json

class NotebookAgent:
    def __init__(self, notebook):
        self.nb = notebook
        self.client = OpenAI()

    def get_context(self):
        """Build context from notebook state for the AI"""
        state = self.nb.get_cells_state()  # Get full state (minimal=False)

        context = f"Notebook: {self.nb.title}\n"
        context += f"Total cells: {len(state)}\n\n"

        for cell in state:
            context += f"Cell {cell['rank']} ({cell['type']}):\n"
            context += f"Code:\n{cell['code']}\n"

            if cell['has_run_once']:
                if cell.get('stdout'):
                    context += f"Output: {cell['stdout']}\n"
                if cell.get('exception'):
                    context += f"Error: {cell['exception']['message']}\n"

            context += "\n"

        return context

    def create_new_cell(self, prompt):
        # Get current notebook state as context
        context = self.get_context()

        # Ask AI to generate code with full context
        response = self.client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are a Streamlit notebook AI assistant. Your task is to produce new Streamlit code cells matching the user's request. Output only valid python code (use comments to verbalize explanations). Modules and data loaded in previous cells don't need to be redefined in next cells (shared namespace)."},
                {"role":"system", "content":f"Current notebook state:\n{context}"}
                {"role": "user", "content": prompt}
            ]
        )
        code = response.choices[0].message.content

        # Create and run the cell
        cell = self.nb.new_cell(type="code", code=code, reactive=True)
        cell.run()

        return cell

agent = NotebookAgent(__notebook__)

@magic
def ai(prompt):
    agent.create_new_cell(prompt)

# Cell 2: Use the agent with context awareness
%ai Please create a dashboard to let me analyze the iris dataset using seaborn
```

A real life implementation would obviously be much more sophisticated, involving agentic tools and so on, but you get the basic idea. 

This level of programmatic control is quite unique to streamlit-notebook and enables workflows not easily achievable in Jupyter or traditional notebooks.

#### API Reference

**Notebook Methods:**
- `new_cell(type, code, reactive, fragment)` - Create a new cell
- `get_cell(rank_or_key)` - Get cell by position or key
- `get_cells_state(minimal)` - Get state of all cells as list of dicts (default: full state)
- `delete_cell(key)` - Remove a cell by key
- `clear_cells()` - Remove all cells
- `run_all_cells()` - Execute all cells in order
- `run_next_cell()` - Execute the next unexecuted cell
- `restart_session()` - Clear namespace and restart Python session
- `rerun(delay, no_wait)` - Trigger a Streamlit rerun
- `wait(delay)` - Request delay before next rerun
- `notify(message, icon, delay)` - Show toast notification
- `save(filepath)` - Save notebook to file
- `open(source)` - Load notebook from file or source code
- `to_python()` - Get Python code representation
- `is_valid_notebook(source)` - Check if source is valid notebook

**Cell Methods:**
- `run()` - Execute the cell
- `reset()` - Clear outputs and execution state
- `move_up()` - Move cell up one position
- `move_down()` - Move cell down one position
- `insert_above()` - Insert new cell above
- `insert_below()` - Insert new cell below
- `delete()` - Remove this cell
- `to_dict(minimal)` - Get dictionary representation (default: minimal, set minimal=False for full state)

**Cell Properties:**
- `code` (read/write) - Cell code content
- `type` (read/write) - Cell type: "code", "markdown", or "html"
- `reactive` (read/write) - Auto-rerun on UI changes
- `fragment` (read/write) - Run as Streamlit fragment
- `id` (read-only) - Unique cell identifier
- `rank` (read/write) - Cell position in notebook
- `language` (read-only) - Cell language ("python" or "markdown")
- `has_run_once` (read-only) - Whether cell has executed with current code

**Notebook Properties:**
- `cells` (list) - All cells in the notebook
- `title` (str) - Notebook title
- `app_mode` (bool) - Whether in locked app mode
- `shell` - Python shell instance
- `current_cell` - Currently executing cell

## Deployment

### Local Testing

First make sure your notebook looks and runs nice as an app. 

```bash
# Test in locked app mode (production simulation)
st_notebook my_notebook.py --app
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

3. Create `.env` file to enable locked app mode:
    ```bash
    ST_NOTEBOOK_APP_MODE=true
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

# Option 1: Use --app flag
CMD ["streamlit", "run", "my_notebook.py", "--app"]

# Option 2: Use environment variable
# ENV ST_NOTEBOOK_APP_MODE=true
# CMD ["streamlit", "run", "my_dashboard.py"]
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

**Data Exploration → Dashboard:** Build analysis interactively, deploy as dashboard.

**Prototyping → Production:** Develop proof-of-concept in notebook mode, deploy as locked app without rewriting.

**Interactive Reports:** Blend narrative (Markdown) with live data and widgets.

**Teaching & Demos:** Create interactive tutorials for step-by-step learning.

**AI Agent Integration:** Let LLMs generate and execute cells programmatically for coding assistance and autonomous analysis.

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

### 2025-11

**Code Quality & API Improvements:**
- **Cell Types**: Improved type management using internal `CellType` mixins (instead of direct `Cell` subclasses), making it straightforward to support new cell types with custom behaviour while still being able to change a cell's type dynamically without having to recreate the cell instance.
- **UI/Logic Separation**: Moved all UI rendering logic to dedicated `NotebookUI` class (following the `Cell`/`CellUI` pattern)
- **Public/Private API Distinction**: Renamed internal methods with `_` prefix for clear API boundaries
- **Template-Based Code Generation**: Refactored `to_python()` to use clean string templates instead of manual concatenation
- **Enhanced Documentation**: Added comprehensive Google-style docstrings with examples for all public methods (~85% coverage)
- **Streamlit Patches**: Centralized all Streamlit module patches in `_apply_patches()` method:
  - `st.echo` - Transparent patching for code execution tracking
  - `st.rerun` - UserWarning guiding users to `__notebook__.rerun()` or package-level import
  - `st.stop` - RuntimeError to properly stop cell execution
- **Rerun API Enhancements**:
  - Added `no_wait` parameter to `rerun()` for immediate reruns (when possible)
  - Exposed `rerun()` and `wait()` as both public notebook methods and package-level exports
  - Improved delay merging logic with clear documentation

**Bug Fixes & UX Improvements:**

- Cell type can now be manually changed after creation ('code', 'markdown', or 'html')
- Fixed bug when inserting new cells above/below existing ones
- Safer UI behavior for dynamic cell creation and execution
- Programmatic cell code modifications now automatically reflect in the editor UI
- Updated `.gitignore` to track Sphinx documentation source files while ignoring build artifacts

**Breaking Changes:**

- Saved notebook `.py` files now use simpler API with `st_notebook()` factory and `nb.render()` method directly, instead of previous `get_notebook()` and `render_notebook()` helpers
  - **Migration**: Update existing notebook files to use new pattern shown in Quick Start

### 2025-10

**Major update:** Notebooks are now pure Python files (`.py`), not JSON.

- Pure Python format with `@nb.cell()` decorator syntax
- Self-contained notebook .py files
- Run directly with `streamlit run notebook.py`
- Locked App mode deployment option
- Removed `.stnb` JSON format entirely

### 2024-09 
- Improved shell behaviour
- Implemented basic magic commands support

### 2024-07

- `.stnb` JSON format as default
- `st_notebook` accepts file paths or JSON strings

### 2024-06

- Custom shell with AST-based execution
- Expression display modes
- HTML cells
- Demo notebooks

---

**Develop with notebooks. Deploy as apps.** 🚀

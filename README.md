# Streamlit Notebook

The reactive notebook powered by Streamlit you've been waiting for.

Streamlit Notebook combines the interactive development experience of Jupyter notebooks with the deployment simplicity of Streamlit apps. Write code in notebook-style cells with a professional-grade Python shell that maintains state across reruns, then deploy the exact same file as a production-ready Streamlit application.

## Overview

We all know Jupyter as the go-to for interactive programming, but it comes with its own limitations:
- JSON format notebooks
- converting notebooks to deployable apps means rewriting everything. 
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
from streamlit_notebook import get_notebook, render_notebook
import streamlit as st

st.set_page_config(page_title="Analysis")
nb = get_notebook(title='analysis')

@nb.cell(type='code')
def setup():
    import pandas as pd
    df = pd.read_csv("data.csv")
    print(f"Loaded {len(df)} rows")

@nb.cell(type='code', reactive=True)
def explore():
    col = st.selectbox("Column", df.columns)
    st.line_chart(df[col])

render_notebook()
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
- `get_notebook` first attempts to get an existing notebook instance from `st.session_state`, if none is found, it creates one. 
- The `@cell` decorator is used to capture the source code of the functions' bodies and add the corresponding cells to the notebook instance. **This happens only at the first pass of the script**, and the decorator is no-oped afterwards (to avoid adding the same cells over and over as the script reruns). 
- `render_notebook` finally takes care of fetching and displaying the current notebook instance from state.

Subsequent runs of the script will ignore the cell definitions and merely loop on `get_notebook()` and `render_notebook()` to refresh whatever notebook instance is living in the session's state.

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

Every Streamlit widget, chart, and component works out of the box. Copy-paste your existing Streamlit code into cells.

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
from streamlit_notebook import get_notebook, render_notebook
import streamlit as st

st.set_page_config(page_title="Stock Dashboard", layout="wide")
nb = get_notebook(title='stock_dashboard')

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

render_notebook()
```

## Easy deployment

Once you're done working on your notebook you may run it using:

```bash
streamlit run sales_dashboard.py --app
```
Now the same file runs as a locked production app with restricted interface and no visible/editable code.
This prevents untrusted users to run arbitrary code in the cloud environment.
Your notebook can thus safely be published as an online app without more overhead.

The dedicated environment variable does the same as the flag:

```bash
export ST_NOTEBOOK_APP_MODE=true # or use a .env file
streamlit run sales_dashboard.py
```

Useful when you can't modify the command directly (e.g., in Streamlit cloud platform).

## Development Features

### Two Modes

**Notebook Mode** (development):
- Code editor for each cell
- Cell management (create, delete, reorder)
- Execution controls (Run Next, Run All, Restart Session, Clear All Cells)
- Save/Open notebooks
- Demo notebooks library

**App Mode** (deployment):
- Restricted interface
- Code editors hidden
- Interactive widgets remain functional
- Clean Streamlit appearance

In development, you may toggle between modes with the sidebar switch, or run with enforced app mode to prevent users toggling back to notebook mode.

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

**Markdown/HTML cells** 

Add rich formatted text or layouts to your notebook with Markdown and HTML cells. They support variable interpolation using the `<<any_expression>>` syntax. The expression will be evaluated and replaced in the code.

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

#simple agent class
class Agent:
    
    def __init__(self):
        from openai import OpenAI
        self.messages=[]
        self.client=OpenAI() #we use the OPENAI_API_KEY provided as env variable

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

This way the page reloads only the UI fragment in which interaction happens.
It just won't refresh other widgets on the page even if they depend on variables changed by the fragment.
So, in general, it's better to group in a same fragment subsets of widgets that are supposed to react to eachother.

Note: A variable that's changed by a fragment is immediately updated in the namespace and can be used elsewhere in the notebook.
So that the isolation is just ui-side, not backend-side.

### Programmatic API

The notebook object is exposed in the shell's namespace as `__notebook__` and can be controled programmaticaly from code cells — useful for automation or AI agents:

```python
# get the notebook instance
nb=__notebook__

# Create cells programmatically
cell = nb.new_cell(
    type="code",
    code="st.line_chart([1,2,3])",
    reactive=True
)
cell.run()

# Edit existing cells
nb.cells[0].code = "import pandas as pd"
nb.cells[0].run()
```

Not really possible in Jupyter or very hacky!

### File Operations

**From the interface:**
- **Save** button: saves to `./notebook_title.py`
- **Open** button: dropdown of all `.py` notebooks in current directory
- **Demo notebooks**: load pre-built examples

**From code:**
```python
__notebook__.save()
__notebook__.save("my_notebook.py")
__notebook__.open("my_notebook.py")
```


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
    pandas
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
- Add `--app` flag to deployment command or set environment variables
- Include all dependencies in `requirements.txt`
- Use `st.secrets` for secrets (API keys, database credentials, etc.)

❌ **Don't:**
- Allow code editing in production deployments (the user could read `st.secrets` or run malicious scripts)
- Hardcode API keys or credentials.
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

**Data Exploration → Dashboard:** Build analysis interactively, deploy as stakeholder dashboard.

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

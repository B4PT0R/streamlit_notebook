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

## Installation

```bash
pip install streamlit-notebook
```

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

@nb.cell(type='code', auto_rerun=True)
def explore():
    col = st.selectbox("Column", df.columns)
    st.line_chart(df[col])

render_notebook()
```

### Run it

```bash
# Development mode - full notebook interface
st_notebook analysis.py

# Locked app mode - clean interface, code hidden
st_notebook analysis.py --app

# Or run directly with Streamlit
streamlit run analysis.py        # Development mode (uses script parameters)
streamlit run analysis.py --app  # Locked app mode (overrides script parameters)
```

## Core Concepts

### Cell Types

**One-shot cells:** Run only once when you click Run. Used for imports, data loading, expensive computations.

**Reactive cells:** Toggle `auto-rerun` on any code cell to make it reactive. These will rerun automatically on every UI interaction and update the python namespace accordingly. Used for widgets and reactive displays.

This selective reactivity lets you separate expensive setup from interactive exploration.

### Persistent Shell

All cells share a long-lived Python namespace with Ipython-style ergonomics. Unlike regular Streamlit apps that restart from scratch on every rerun, imports, variables, and computed results persist across UI interactions.

**Example:**
```python
# Cell 1 (one-shot) - runs once
import pandas as pd
df = pd.read_csv("large_file.csv")  # 10 seconds to load

# Cell 2 (auto-rerun) - reruns on interaction
threshold = st.slider("Threshold", 0, 100)
st.write(df[df['value'] > threshold])  # Instant - df already in memory
```

Cell 1 loads data once. Cell 2 reruns on slider changes but `df` is already in memory—no re-loading.

### Standard Streamlit APIs

Every Streamlit widget, chart, and component works out of the box. Copy-paste your existing Streamlit code into cells.

```python
@nb.cell(type='code', auto_rerun=True)
def my_widget():
    # Standard Streamlit code - nothing new to learn
    value = st.slider("Select value", 0, 100)
    st.metric("Current value", value)
    st.bar_chart([value, value*2, value*3])
```

## Real-World Example

Building a dashboard for 1M rows of sales data:

```python
from streamlit_notebook import get_notebook, render_notebook
import streamlit as st

st.set_page_config(page_title="Sales Dashboard", layout="wide")
nb = get_notebook(title='sales_dashboard')

@nb.cell(type='code')
def setup():
    import pandas as pd
    import plotly.express as px

@nb.cell(type='code')
def load_data():
    df = pd.read_csv("sales_data.csv")  # 1M rows, ~10 seconds
    df['date'] = pd.to_datetime(df['date'])
    print(f"Loaded {len(df):,} records")

@nb.cell(type='code', auto_rerun=True)
def filters():
    region = st.multiselect("Regions", df['region'].unique())
    date_range = st.date_input("Date range", [df['date'].min(), df['date'].max()])

@nb.cell(type='code', auto_rerun=True)
def dashboard():
    filtered = df[df['region'].isin(region)] if region else df
    st.metric("Total Sales", f"${filtered['amount'].sum():,.2f}")
    st.plotly_chart(px.line(filtered.groupby('date')['amount'].sum()))

render_notebook()
```

**Performance:** Setup and data loading run once (~10 sec). Filters and dashboard rerun instantly on interaction. No re-loading 1M rows.

**Deploy:**
```bash
streamlit run sales_dashboard.py --app
```
The same file now runs as a locked production app with working filters and no visible code.

## Development Features

### Two Modes

**Notebook Mode** (development):
- Code editor for each cell
- Cell management (create, delete, reorder)
- Execution controls (Run, Run All, Restart Shell)
- Save/Open notebooks
- Demo notebooks library

**App Mode** (deployment):
- Code editors hidden
- Interactive widgets remain functional
- Clean Streamlit appearance
- Optional locked mode prevents toggling back

Toggle between modes with the sidebar switch, or use the `--app` flag.

### Rich Content

**Rich display**

Cell results are automatically displayed with pretty formatting (anything that `st.write` can handle).

Control how expression results appear:
- `all` - show every expression result
- `last` - show only the last expression (default)
- `none` - suppress automatic display

Configurable in the sidebar settings.

You may also :
- add a trailing `;` at the end of a line to bypass automatic display
- use the `display` function to selectively display a given result

**Markdown/HTML cells** 

Supporting variable interpolation using `<<any_expression>>`

```markdown
# Analysis Results

We loaded << len(df) >> rows.
The mean value is << df['value'].mean() >>.
```

**System commands and magics**

Ipython style commands and magics are supported. It's still basic but works.
(would require a proper parsing at token level to mimic Ipython more closely)

```python
#Cell 1

#system commands
!pip install requests

#define a new magic
@magic
def my_new_magic(content):
    print(content.upper())

#call it in a single line with % (takes the whole line trailing the %<command> as input string)
%my_new_magic hello, this is a test!
```

With `%%`, the whole cell starting at second line is considered the magic input.

```python
#Cell 2
%%my_new_magic
All the content of
the cell goes in the
magic input
```

Note: Only the mechanism is supported and you have to declare your own magics.

Warning: contrary to Ipython, `!` and `!!` here work the same as `%` and `%%`, namely they distinguish between single line and full-cell magics. They just route the arg to be run as a system command/script.

Note: The shell is *NOT* meant to be an exact reproduction of Ipython. My goal is to provide a practical and versatile coding environment matching the common needs of interactive execution. Yet, you might encounter situations where you feel like some useful features of Ipython are missing, if so please add a feature request.

## Advanced Features

### Streamlit Fragments

Auto-rerun cells can use [Streamlit fragments](https://docs.streamlit.io/library/api-reference/performance/st.fragment) for faster, scoped updates:

```python
@nb.cell(type='code', auto_rerun=True, fragment=True)
def fast_widget():
    # Only this cell reruns on interaction
    value = st.slider("Value", 0, 100)
    st.write(f"Selected: {value}")
```

### File Operations

**In development mode:**
- **Save** button: saves to `./notebook_title.py`
- **Open** button: dropdown of all `.py` notebooks in current directory
- **Demo notebooks**: load pre-built examples

**From code:**
```python
notebook.save()
notebook.save("my_notebook.py")
notebook.open("my_notebook.py")
```

### Programmatic API

The notebook object is exposed in the shell's namespace as `__notebook__` and can be controled programmaticaly from code cells — useful for automation or AI agents:

```python
# get the notebook instance
nb=__notebook__

# Create cells programmatically
cell = nb.new_cell(
    type="code",
    code="st.line_chart([1,2,3])",
    auto_rerun=True
)
cell.run()

# Edit existing cells
nb.cells[0].code = "import pandas as pd"
nb.cells[0].run()
```

Not really possible in Jupyter or very hacky!

## Deployment

### Local Testing

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
   [server]
   headless = true
   ```

3. Create `.env` file to enable locked app mode:
   ```bash
   ST_NOTEBOOK_APP_MODE=true
   ```

   **Note:** Since Streamlit Cloud doesn't let you control the `streamlit run` command, use the `.env` file to set the environment variable. This ensures your notebook deploys in locked app mode.

4. Push to GitHub:
   ```bash
   git add my_dashboard.py requirements.txt .env
   git commit -m "Add dashboard"
   git push
   ```

5. Deploy on [share.streamlit.io](https://share.streamlit.io):
   - Connect your GitHub repo
   - Select `my_dashboard.py` as main file
   - Click "Deploy"

Since notebooks are just Python files, Streamlit Cloud runs them directly — no wrapper needed.

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY my_dashboard.py .

EXPOSE 8501

# Option 1: Use --app flag
CMD ["streamlit", "run", "my_dashboard.py", "--app"]

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

### Environment Variables

Control behavior via CLI flag or environment variable:

**CLI flag (recommended):**
```bash
streamlit run notebook.py --app  # Locked app mode
```

**Environment variable:**
```bash
export ST_NOTEBOOK_APP_MODE=true  # Locked app mode
```

The `--app` flag is simpler and works everywhere. The environment variable is useful when you can't modify the command line (e.g., some cloud platforms).

### Production Best Practices

✅ **Do:**
- Test with `--app` flag locally first
- Use `@st.cache_data` for expensive operations
- Add `--app` flag to deployment command or set environment variables
- Include all dependencies in `requirements.txt`
- Use `st.secrets` for secrets (API keys, database credentials, etc.)

❌ **Don't:**
- Allow code editing in production deployments (the user could read `st.secrets` or run malicious scripts)
- Hardcode API keys or credentials
- Assume filesystem persistence (use databases/cloud storage)

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

**AI Agent Integration:** Let LLMs generate and execute cells programmatically for autonomous analysis.

## Demo

Try the hosted demo: [st-notebook.streamlit.app](https://st-notebook.streamlit.app/)

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

### 2025-10 - Pure Python Format

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

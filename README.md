# Streamlit Notebook

**The notebook interface Streamlit users have been waiting for.**

Build interactive analyses with notebook-style cells. Deploy them as polished Streamlit apps. Zero rewriting required.

> **For Streamlit users:** Get Jupyter-style cell execution without leaving the Streamlit ecosystem.
> **For Jupyter users:** Keep your notebook workflow, gain Streamlit's deployment power and widget ecosystem.
> **Compared to Marimo:** Same reactive notebook vision, but leverage Streamlit's mature ecosystem and zero learning curve.

## Why Streamlit Notebook?

### The Problem
- **Jupyter → Production** is painful. Converting notebooks to deployable apps means rewriting everything.
- **Streamlit development** lacked a notebook ergonomics. The edit-refresh cycle slows down exploration, and **every script rerun starts from scratch** — you constantly re-import libraries, redefine functions/objects and recompute expensive operations unless you properly cache them or store them in `st.session_state`.
- **Marimo** is promising, but requires learning new APIs, and leaves the Streamlit ecosystem behind.

### The Solution
Streamlit Notebook gives you **notebook ergonomics during development** and **Streamlit apps for deployment** — using the exact same `.stnb` file.

```bash
# Develop locally with full notebook interface
st_notebook my_analysis.stnb

# Deploy as a locked Streamlit app (no code editing)
st_notebook my_analysis.stnb --app-mode --locked
```

**Same file. Two modes. Zero rewriting.**

## Key Advantages

### ✅ **For Streamlit Users**
- **Zero learning curve** – uses standard Streamlit APIs (`st.slider`, `st.write`, etc.)
- **Drop-in compatibility** – copy/paste your existing Streamlit code into cells
- **Persistent namespace** – imports, variables, and state survive across reruns (no more re-importing pandas every refresh!)
- **Better dev experience** – cell-by-cell execution beats the edit-refresh loop
- **Deploy anywhere** – works with Streamlit Cloud, Docker, Kubernetes, etc.

### ✅ **vs. Jupyter**
- **Deployment story** – notebooks become apps instantly, no conversion needed
- **Native widgets** – Streamlit's rich widget ecosystem built-in
- **Reactive UI** – interactive dashboards without complex callbacks
- **Modern stack** – all the React ecosystem easily wrapped as Streamlit components

### ✅ **vs. Marimo**
- **Mature ecosystem** – 35K+ Streamlit stars, thousands of components, enterprise support
- **No migration** – if you know Streamlit, you know Streamlit Notebook
- **Proven deployment** – Streamlit Cloud, Docker, Kubernetes all just work
- **Community resources** – thousands of StackOverflow answers, tutorials, examples

## Screenshots

**Development Mode:**
![Notebook mode](./streamlit_notebook/app_images/st_notebook_demo.png)

**Deployed App Mode:**
![App mode](./streamlit_notebook/app_images/st_notebook_demo_2.png)

## Quick Start

### Installation
```bash
pip install streamlit-notebook
```

### Development Mode
```bash
st_notebook                     # Start empty notebook
st_notebook my_analysis.stnb    # Open existing notebook
```

**Quick example - mixing one-shot and auto-rerun cells:**

```python
# Cell 1 (one-shot): Run once, results persist
import pandas as pd
df = pd.read_csv("data.csv")

# Cell 2 (auto-rerun): Runs on every widget interaction
column = st.selectbox("Choose column", df.columns)
st.line_chart(df[column])
```

**Key insight:** Cell 1 loads data once. Cell 2 reruns when the selectbox changes, but `df` is already in memory — no re-importing, no re-loading!

### App Mode (Deployment)

**Preview locally:**
```bash
st_notebook my_analysis.stnb --app-mode
```

**Deploy locked (production):**
```bash
st_notebook my_analysis.stnb --app-mode --locked
```

**Docker deployment:**
```dockerfile
FROM python:3.11
RUN pip install streamlit-notebook
COPY dashboard.stnb /app/
ENV ST_NOTEBOOK_MODE=app
ENV ST_NOTEBOOK_LOCKED=true
CMD ["st_notebook", "/app/dashboard.stnb"]
```

**Environment variables:**
```bash
export ST_NOTEBOOK_MODE=app      # Enable app mode
export ST_NOTEBOOK_LOCKED=true   # Lock app mode
```

## Core Features

### 🎯 **Selective Reactivity**
Control exactly what runs when by choosing the right cell type:

| Cell Type | When it runs | Best for |
|-----------|-------------|----------|
| **One-shot** | Once (when you click Run) | Imports, data loading, expensive computations, function definitions |
| **Auto-rerun** | Every UI interaction | Widgets (`st.slider`), live charts, reactive displays |

This gives you **notebook-style persistence** for heavy operations + **Streamlit-style reactivity** for interactive elements.

### 🔄 **Persistent Shell**
All cells share a long-lived Python namespace **stored in session state**. Unlike regular Streamlit apps that restart from scratch on every rerun, imports, variables, and computed results persist across UI interactions.

**Regular Streamlit:** Reruns entire script on every button click → re-imports, re-loads data, re-computes everything.

**Streamlit Notebook:** One-shot cells run once, results persist → import once, load once, compute once. Only auto-rerun cells refresh on interactions.

### 🎨 **Full Streamlit API**
Every Streamlit widget, chart, and component works out of the box. No new APIs to learn.

```python
# This just works - standard Streamlit code
import streamlit as st
import pandas as pd

df = pd.read_csv("data.csv")
selected = st.slider("Select rows", 0, len(df))
st.dataframe(df.head(selected))
```

### 🚀 **Streamlit Fragments**
Auto-rerun cells can run as [Streamlit fragments](https://docs.streamlit.io/library/api-reference/performance/st.fragment) for faster, scoped updates.

### 🤖 **Programmable Notebooks**
Manipulate notebooks from code — perfect for AI agents or automation:

```python
# Create cells programmatically
cell = notebook.new_cell(type="code", code="st.line_chart([1,2,3])", auto_rerun=True)
cell.run()

# Edit existing cells
notebook.cells[0].code = "import pandas as pd"
notebook.cells[0].run()
```

### 📝 **Rich Content**
- **Markdown cells** with `<< variable >>` interpolation
- **HTML cells** for custom visualizations
- **Magic commands** (`%timeit`, `%%bash`, etc.)
- **System commands** (`!ls`, `!pip install`, etc.)

## Two-Mode Workflow

### Development Mode
**Full notebook interface with:**
- Code editor for each cell
- Cell management (create, delete, reorder)
- One-shot vs auto-rerun toggle
- Fragment execution option
- Run all, restart shell, clear cells
- Save/Open from current directory
- Upload/Download for sharing

### App Mode
**Clean, production-ready UI with:**
- Code editors hidden
- Interactive widgets remain functional
- Execution controls (Run All, Reset & Run)
- Download notebook option
- Professional Streamlit appearance

**Toggle modes:**
- **Preview:** "App mode preview" toggle in sidebar (development)
- **Locked:** `--locked` flag prevents toggling back (deployment)

## Understanding Cell Types

### Simple Rule
- **One-shot cells:** Run once when you click Run. For imports, data loading, heavy computation.
- **Auto-rerun cells:** Run automatically on every UI interaction. For widgets and reactive displays.

### Common Patterns

✅ **Do this:**
```python
# Cell 1 (one-shot)
import pandas as pd
df = pd.read_csv("data.csv")
model = train_model(df)

# Cell 2 (auto-rerun)
threshold = st.slider("Threshold", 0, 100)
st.line_chart(df[df['value'] > threshold])
```

❌ **Not this:**
```python
# Cell 1 (auto-rerun) - BAD: re-loads data on every slider change!
import pandas as pd
df = pd.read_csv("data.csv")
threshold = st.slider("Threshold", 0, 100)
st.line_chart(df[df['value'] > threshold])
```

**Important:** Auto-rerun cells only execute after being run manually once. Toggle auto-rerun on, then click Run to start the reactive behavior.

## Real-World Example: Sales Dashboard

Building a dashboard for 1M rows of sales data:

```python
# Cell 1 (one-shot): Setup - run once
import pandas as pd
import plotly.express as px

# Cell 2 (one-shot): Load & preprocess - run once (~10 seconds)
df = pd.read_csv("sales_data.csv")  # 1M rows
df['date'] = pd.to_datetime(df['date'])
print(f"Loaded {len(df):,} records")

# Cell 3 (auto-rerun): Interactive filters - instant
region = st.multiselect("Select regions", df['region'].unique())
date_range = st.date_input("Date range", [df['date'].min(), df['date'].max()])

# Cell 4 (auto-rerun): Live results - instant
filtered = df[df['region'].isin(region)] if region else df
st.metric("Total Sales", f"${filtered['amount'].sum():,.2f}")
st.plotly_chart(px.line(filtered.groupby('date')['amount'].sum()))
```

**Performance:** Cells 1-2 run once (10 sec). Cells 3-4 rerun instantly on filter changes. **No re-loading 1M rows!**

**Deploy:** `st_notebook sales_dashboard.stnb --app-mode --locked` → Professional app with working filters, no code visible.

**Want to deploy to the cloud?** See the [Deploying to the Cloud](#deploying-to-the-cloud) section for step-by-step guides.

## File Operations

### Local Development
- **Save** button: Saves to `./notebook_title.stnb` in current directory
- **Open** button: Opens dropdown with:
  - Selectbox showing all `.stnb` files in current directory
  - File uploader below for importing notebooks from elsewhere
- **Download** button (tertiary): Export to Downloads folder if needed

### Embedding in Apps
```python
import streamlit as st
from streamlit_notebook import st_notebook

# Start with empty notebook
st_notebook()

# Load from file
st_notebook("path/to/notebook.stnb")

# App mode from code
st_notebook("dashboard.stnb", app_mode=True, locked=True)
```

## Advanced Features

### Display Modes
Control how expression results appear:
- **`all`**: show every expression result
- **`last`**: show only the last expression (default)
- **`none`**: suppress automatic display

### Reactive Markdown
```markdown
# Analysis Results

We loaded << len(df) >> rows.
The mean value is << df['value'].mean() >>.
```

### System Commands & Magics
```python
# Shell commands
!pip install requests
!ls -la

# IPython-style magics
%timeit sum(range(1000))
%%bash
echo "Hello from bash"
```

## Deployment Considerations

**Local development** (recommended use case):
- Full filesystem access
- Install any packages
- Save/load notebooks freely
- Complete control

**Cloud deployment** (possible, with caveats):
- Code runs on server
- Preinstall dependencies
- Read-only filesystem (container restarts)
- Use `--locked` to prevent code editing
- Add authentication for public deployments

## Comparison Matrix

| Feature | Streamlit Notebook | Jupyter | Marimo | Plain Streamlit |
|---------|-------------------|---------|--------|-----------------|
| **Development UX** | ✅ Cell-by-cell | ✅ Cell-by-cell | ✅ Cell-by-cell | ⚠️ Edit-refresh loop |
| **Persistent namespace** | ✅ Yes (session state) | ✅ Yes (kernel) | ✅ Yes | ❌ No (reruns from scratch) |
| **Deployment** | ✅ One-click | ❌ Requires rewrite | ✅ Built-in | ✅ Native |
| **API familiarity** | ✅ Standard Streamlit | ✅ Standard Python | ⚠️ New Marimo API | ✅ Standard Streamlit |
| **Ecosystem size** | ✅ Streamlit (35K+ ⭐) | ✅ Huge | ⚠️ Growing | ✅ Streamlit (35K+ ⭐) |
| **Widget library** | ✅ All Streamlit widgets | ⚠️ Limited (ipywidgets) | ✅ Marimo widgets | ✅ All Streamlit widgets |
| **Reactive UI** | ✅ Selective | ❌ Not reactive | ✅ Automatic | ✅ Automatic |
| **Learning curve** | ✅ Minimal (if you know Streamlit) | ✅ Minimal | ⚠️ New framework | ✅ Minimal |
| **Enterprise support** | ✅ Via Streamlit/Snowflake | ✅ Available | ⚠️ Limited | ✅ Via Streamlit/Snowflake |

## Deploying to the Cloud

### Streamlit Cloud (Easiest)

**1. Prepare your notebook:**
```bash
# Test locally in app mode first
st_notebook my_dashboard.stnb --app-mode --locked
```

**2. Create a requirements.txt:**
```txt
streamlit-notebook
pandas
plotly
# ... other dependencies
```

**3. Create a Streamlit app file (`app.py`):**
```python
from streamlit_notebook import st_notebook
import os

# Deploy in locked app mode
st_notebook(
    "my_dashboard.stnb",
    app_mode=True,
    locked=True
)
```

**4. Push to GitHub:**
```bash
git add my_dashboard.stnb app.py requirements.txt
git commit -m "Add dashboard"
git push
```

**5. Deploy on Streamlit Cloud:**
- Go to [share.streamlit.io](https://share.streamlit.io)
- Connect your GitHub repo
- Select `app.py` as the main file
- Click "Deploy"

Done! Your notebook is now a live app at `https://yourapp.streamlit.app`

### Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy notebook
COPY my_dashboard.stnb .

# Set environment variables for app mode
ENV ST_NOTEBOOK_MODE=app
ENV ST_NOTEBOOK_LOCKED=true

# Expose Streamlit port
EXPOSE 8501

# Run the app
CMD ["st_notebook", "my_dashboard.stnb"]
```

**Build and run:**
```bash
docker build -t my-dashboard .
docker run -p 8501:8501 my-dashboard
```

**Deploy to cloud:**
- **AWS ECS/Fargate**: Push to ECR, create task definition
- **Google Cloud Run**: `gcloud run deploy --image gcr.io/project/my-dashboard`
- **Azure Container Apps**: Deploy from container registry

### Environment Variables

Set these in your deployment platform:

```bash
ST_NOTEBOOK_MODE=app       # Enable app mode
ST_NOTEBOOK_LOCKED=true    # Lock editing (recommended for production)
```

**Streamlit Cloud:** Add to Secrets management
**Docker:** Set in Dockerfile or docker-compose.yml
**Kubernetes:** Add to ConfigMap or deployment YAML

### Best Practices for Production

✅ **Do:**
- Test in `--app-mode --locked` locally first
- Use `@st.cache_data` for expensive operations
- Set `ST_NOTEBOOK_LOCKED=true` to prevent code editing
- Include all dependencies in `requirements.txt`
- Use environment variables for secrets (not hardcoded)

❌ **Don't:**
- Deploy without testing app mode first
- Allow code editing in production (leave unlocked)
- Hardcode API keys or credentials
- Assume filesystem persistence (use databases/cloud storage)

## Demo

Try the hosted demo: [st-notebook.streamlit.app](https://st-notebook.streamlit.app/)

## Use Cases

### Data Exploration → Dashboard
Build an analysis interactively, deploy it as a dashboard for stakeholders.

### Prototyping → Production
Develop proof-of-concept in notebook mode, deploy as locked app without rewriting.

### Interactive Reports
Create notebooks that blend narrative (Markdown) with live data and widgets.

### Teaching & Demos
Build interactive tutorials that students/viewers can follow step-by-step.

### AI Agent Integration
Let LLMs generate and execute cells programmatically for autonomous analysis.

## Contributing & Feedback

This project is evolving quickly. Bug reports, feature ideas, and PRs are welcome!

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-idea`)
3. Commit changes (`git commit -m "Add my idea"`)
4. Push (`git push origin feature/my-idea`)
5. Open a pull request

File issues for anything unexpected or frustrating.

## License

MIT License – see [LICENSE](LICENSE).

## Changelog

- **2025-01-XX**
  - Added app mode with locked deployment option
  - Implemented Save/Open buttons for better local UX
  - Fixed auto-rerun behavior (only triggers after first manual run)
  - Separated notebook mode vs app mode sidebars
- **2024-07-03**
  - `.stnb` becomes the default notebook extension
  - `st_notebook` accepts file paths or JSON strings
- **2024-07-02**
  - Programmatic cell creation/editing improvements
  - Added demo notebooks
- **2024-06-24**
  - Custom shell with AST-based execution
  - Expression display modes
  - `display()` helper function
- **2024-06-11**
  - HTML cells
  - JSON import/export
  - Demo notebooks

---

**Stop rewriting notebooks. Start deploying them.** 🚀

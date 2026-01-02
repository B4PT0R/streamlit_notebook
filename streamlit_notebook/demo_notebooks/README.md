# Streamlit Notebook - Demo Tour

A progressive tour of Streamlit Notebook features. Each tutorial is concise,
interactive, and focused on core concepts.

## Tutorial Series (11 Notebooks)

### 01. Welcome & Quick Start
[01_getting_started.py](01_getting_started.py)

Your first interactive notebook. Learn about one-shot vs reactive cells and see
the full tour overview.

### 02. Cell Types and Reactivity
[02_cell_types_and_reactivity.py](02_cell_types_and_reactivity.py)

Master execution modes: one-shot for data loading, reactive for widgets.
Includes best practices and interactive dashboard example.

### 03. Display and Persistence
[03_display_and_persistence.py](03_display_and_persistence.py)

Use `display()` to keep outputs visible across reruns. Learn about display
backends and when to use each approach.

### 04. Widgets and State
[04_widgets_and_keys.py](04_widgets_and_keys.py)

Widget keys, session state patterns, and state management across cells.

### 05. Markdown and HTML Cells
[05_markdown_and_interpolation.py](05_markdown_and_interpolation.py)

Live variable interpolation with `<<expression>>` syntax. Create formatted
reports and custom HTML with live data.

### 06. Layouts and Styling
[06_layout_modes.py](06_layout_modes.py)

Configure page width, horizontal layout, and code/output split. Perfect for
dashboards and presentations.

### 07. Fragments and Auto-Refresh
[07_fragments.py](07_fragments.py)

Scoped reruns with `fragment=True` and automatic updates with `run_every`.
Build live dashboards and monitoring tools.

### 08. Programmatic API
[08_programmatic_api.py](08_programmatic_api.py)

Control notebooks with `__notebook__`. Create cells dynamically, manage
execution, and build powerful notebook automation.

### 09. Rerun Control
[09_rerun_control.py](09_rerun_control.py)

Advanced flow management with `rerun()`, `wait()`, and `check_rerun()`.
Master delayed reruns, debouncing, and intelligent delay merging.

### 10. Deployment and File Operations
[10_deployment_and_files.py](10_deployment_and_files.py)

Deploy to production with app mode. Learn file I/O, save/open notebooks,
and production deployment best practices.

### 11. AI Agent Integration
[11_ai_agent.py](11_ai_agent.py)

Optional AI assistant integration. Let AI create cells, analyze data,
and help debug your notebooks.

## Quick Reference

**Core Concepts:**
- **One-shot cells** (⚪) - Run once, perfect for data loading and expensive operations
- **Reactive cells** (🔵) - Auto-rerun, great for widgets and interactive UI
- **Fragments** - Scoped reruns for performance
- **display()** - Persistent output in one-shot cells

**Key Patterns:**
```python
# One-shot data loading
@nb.cell(type='code', reactive=False)
def load_data():
    df = pd.read_csv('data.csv')
    display(df, backend='dataframe')

# Reactive widgets
@nb.cell(type='code', reactive=True)
def interactive():
    value = st.slider("Value", 0, 100, 50, key='slider_value')
    st.write(f"Filtered: {len(df[df['col'] > value])} rows")

# Markdown with interpolation
@nb.cell(type='markdown')
def report():
    r'''
    ## Report
    Total rows: <<len(df)>>
    Average: <<df['col'].mean():.2f>>
    '''

# Fragment with auto-refresh
@nb.cell(type='code', reactive=True, fragment=True, run_every=2)
def live_metrics():
    st.metric("Time", datetime.now().strftime('%H:%M:%S'))
```

## Getting Started

1. **Start with 01**: Run `st_notebook 01_getting_started.py`
2. **Follow the tour**: Use Next/Previous buttons to navigate
3. **Experiment**: Run cells, change code, see what happens
4. **Build your own**: Apply what you learn to your projects!

Each notebook builds on previous concepts while staying under 10 cells for
easy comprehension.

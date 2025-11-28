# Documentation for streamlit-notebook

This directory contains the Sphinx documentation for streamlit-notebook.

## Building the Documentation

### Prerequisites

Install the documentation build requirements:

```bash
pip install -r requirements.txt
```

### Build HTML Documentation

```bash
cd docs
make html
```

The generated documentation will be in `_build/html/`. Open `_build/html/index.html` in your browser.

### Clean Build Files

```bash
make clean
```

### Other Formats

Sphinx supports multiple output formats:

```bash
make latexpdf  # PDF via LaTeX
make epub      # EPUB ebook
make man       # Manual pages
```

## Documentation Structure

- `conf.py` - Sphinx configuration
- `index.rst` - Main documentation page
- `api_reference.rst` - API documentation (auto-generated from docstrings)
- `Makefile` - Build automation (Linux/Mac)
- `make.bat` - Build automation (Windows)

## Writing Documentation

### Docstring Format

We use **Google-style docstrings** which are parsed by the Napoleon extension:

```python
def example_function(param1: str, param2: int = 0) -> bool:
    """Brief description of the function.

    Longer description explaining what the function does,
    how it works, and any important details.

    Args:
        param1: Description of param1.
        param2: Description of param2. Defaults to 0.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param2 is negative.

    Examples:
        Basic usage::

            result = example_function("test", 5)

    Note:
        Any additional notes or warnings.

    See Also:
        :func:`related_function`: Related functionality
    """
    pass
```

### Cross-References

- Functions: `:func:`module.function``
- Classes: `:class:`module.ClassName``
- Methods: `:meth:`ClassName.method``
- Modules: `:mod:`module.name``
- Code: ``` ``code`` ```
- Links: `` `text <URL>`_ ``

## Publishing Documentation

### GitHub Pages

1. Build the documentation:
   ```bash
   make html
   ```

2. The `sphinx.ext.githubpages` extension automatically creates a `.nojekyll` file

3. Push the `_build/html` directory to the `gh-pages` branch:
   ```bash
   ghp-import -n -p -f _build/html
   ```

### Read the Docs

1. Create a `.readthedocs.yaml` in the project root (see example below)
2. Connect your GitHub repository to Read the Docs
3. Documentation will be built automatically on each commit

Example `.readthedocs.yaml`:

```yaml
version: 2

build:
  os: ubuntu-22.04
  tools:
    python: "3.9"

sphinx:
  configuration: docs/conf.py

python:
  install:
    - requirements: docs/requirements.txt
    - method: pip
      path: .
```

## Current Status

✅ **Completed:**
- Sphinx configuration with Napoleon (Google-style docstrings)
- API reference structure
- utils.py - Full Sphinx/Google docstrings
- echo.py - Full Sphinx/Google docstrings

🚧 **In Progress:**
- shell.py - Sphinx/Google docstrings
- cell.py - Sphinx/Google docstrings
- cell_ui.py - Sphinx/Google docstrings
- notebook.py - Sphinx/Google docstrings
- main.py - Sphinx/Google docstrings

📝 **To Do:**
- User guide pages
- Tutorial pages
- Example notebooks documentation
- Deployment guide

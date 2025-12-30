# Changelog

All notable changes to this project will be documented in this file.

## 2025-12 (Latest)

### v0.3.4

- New Advanced settings panel with toggle button in cell UI
  - Fragment toggle moved from main UI to Advanced panel (saves UI space)
  - Added `run_every` parameter control for auto-refreshing fragments
  
- All notebook widgets use `state_key()` prefixer to avoid key collisions with user defined widgets in cells.

- **API Change**: `nb.new_notebook()` removed - use `nb.open()` without arguments to create a new notebook
  - `nb.open()` creates new notebook with default title "new_notebook" (editable from UI)
  - `nb.open(path_or_code)` loads existing notebook from file path or code string
  - Cleaner, more intuitive API without parameter ambiguity

### v0.3.2

- **Shell code extraction to `pynteract`**: The former `streamlit_notebook.shell` sub-package has been moved to a standalone package (`pynteract`: [here](https://github.com/B4PT0R/pynteract)) to improve maintainability and separation of concerns.

- Explicit UTF-8 encoding for file IO to fix Windows compatibility issues.
- Internal `st.session_state` keys are now consistently prefixed with `_streamlit_notebook_` to avoid collisions with user-defined keys.
- Sidebar title inputs now properly stays in sync with the current notebook title.
- Threads spawned by the agent stream processing pipeline are registered in a global pool and joined after response generation to avoid stray background threads.
- Added `audioop-lts` as an explicit dependency to ensure pydub compatibility with Python >= 3.13 (the standard lib `audioop` package on which pydub relies has been deprecated and removed from latest python versions). Tested working with 3.14.
- Streamlit import/patching is deferred to avoid `missing ScriptRunContext` in CLI startup.

- `rerun()` now supports Streamlit 1.52+ fragment scope: `rerun("fragment")` for fragment-only reruns, `rerun("app")` for full app reruns (default). Fragment reruns bypass delay management for immediate execution.

### v0.3.0

- Improved UI/UX : better cell UI interface, possibility to minimize cells to free up screen space, new Quit button to close the Streamlit server elegantly (having to hit Ctrl+C in the terminal was not ideal…), and other little stuff.

- new `layout` parameter in the st_notebook factory. Basically equivalent to st.set_page_config, but letting you choose the initial layout width (in %) of the main display, rather than just 'centered' or 'wide'). I also added a slider in the sidebar to adapt the width live from the interface. Note: **You don't need to call st.set_page_config anymore in your notebook files, and attempting to do so will raise an error**.
- most features now working properly (many bug fixes)
- better modularity, organization and documentation of the codebase
- moved the modict utility used throughout the project to a separate package ([here](https://github.com/B4PT0R/modict)).

### v0.2.0

**New Features:**
- **Enhanced AI Agent**: Added comprehensive document reading capabilities
  - Support for PDF, DOCX, XLSX, PPTX, ODT, HTML, and more
  - Web page content extraction with `read()` tool
  - Automatic text extraction from URLs and local files
  - Lightweight fallback mode when optional dependencies unavailable
- **Voice Integration**: Added audio autoplay component for seamless voice interaction
  - Cross-browser compatible audio playback
  - Auto-detection of audio formats (MP3, WAV, OGG, etc.)
  - Silent UI integration for voice responses

**Code Quality & Structure:**
- **Module Reorganization**: Moved core modules into `streamlit_notebook/core/` package
  - Better separation between core notebook functionality and agent features
  - Cleaner import structure and namespace organization
- **Agent Modules**: Consolidated AI agent code in `streamlit_notebook/agent/` package
  - Modular tool system with `Tool` class
  - Separate modules for voice, image, and message handling
  - Enhanced `modict` utility for flexible configuration
- **Bug Fixes**:
  - Fixed typo in `has_fragment_toggle` property setter
  - Improved error handling in AI streaming
  - Better handling of cell display metadata

**Developer Experience:**
- Added comprehensive module-level documentation
- Improved type hints throughout codebase
- Enhanced error messages and debugging output
- Better fallback strategies for optional dependencies

## 2025-11

**Installation Changes:**
- **Optional Dependencies**: Data science packages (matplotlib, pandas, numpy, etc.) are now optional
  - Install with `[datascience]` extra for full stack, or install core only and add libraries manually
  - Reduces base install size significantly for lightweight deployments

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
  - Unified API: `rerun(wait)` and `wait(delay)` now accept bool/float for flexible control
  - `wait=True` (soft rerun), `wait=False` (hard rerun), `wait=<number>` (delayed rerun)
  - Exposed `rerun()` and `wait()` as both public notebook methods and package-level exports
  - Improved delay merging logic with clear documentation
- **AI Agent Integration**:
  - Agent now accessible in shell namespace as `__agent__`
  - Enables dynamic tool registration and programmatic agent control
  - Full documentation added to README with examples

**Bug Fixes & UX Improvements:**

- Cell type can now be manually changed after creation ('code', 'markdown', or 'html')
- Fixed bug when inserting new cells above/below existing ones
- Safer UI behavior for dynamic cell creation and execution
- Programmatic cell code modifications now automatically reflect in the editor UI
- Updated `.gitignore` to track Sphinx documentation source files while ignoring build artifacts

**Breaking Changes:**

- Saved notebook `.py` files now use simpler API with `st_notebook()` factory and `nb.render()` method directly, instead of previous `get_notebook()` and `render_notebook()` helpers
  - **Migration**: Update existing notebook files to use new pattern shown in Quick Start

## 2025-10

**Major update:** Notebooks are now pure Python files (`.py`), not JSON.

- Pure Python format with `@nb.cell()` decorator syntax
- Self-contained notebook .py files
- Run directly with `streamlit run notebook.py`
- Locked App mode deployment option
- Removed `.stnb` JSON format entirely

## 2024-09
- Improved shell behaviour
- Implemented basic magic commands support

## 2024-07

- `.stnb` JSON format as default
- `st_notebook` accepts file paths or JSON strings

## 2024-06

- Custom shell with AST-based execution
- Expression display modes
- HTML cells
- Demo notebooks

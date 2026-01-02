# Tutorial 11: AI Agent Integration
# Optional AI assistant for notebook automation

from streamlit_notebook import st_notebook
import streamlit as st

nb = st_notebook(title='11_ai_agent')


@nb.cell(type='markdown', minimized=True)
def intro():
    r'''
    # AI Agent Integration

    Streamlit Notebook supports an optional AI agent that can:
    - Create and edit cells based on your instructions
    - Analyze data and generate visualizations
    - Answer questions about your notebook
    - Run code and debug issues

    **This is an optional feature** - the agent is not required to use Streamlit Notebook.
    '''


@nb.cell(type='markdown', minimized=True)
def installation():
    r'''
    ## Installation

    Install with agent support:
    ```bash
    pip install streamlit-notebook[agent]
    # or
    pip install streamlit-notebook[full]
    ```

    Configure your API key:
    ```bash
    export OPENAI_API_KEY='your-key-here'
    ```
    '''


@nb.cell(type='code', reactive=True)
def check_agent_status():
    import os

    st.subheader("Agent Status")

    api_key = os.getenv('OPENAI_API_KEY')
    has_key = bool(api_key)

    col1, col2 = st.columns(2)
    with col1:
        if has_key:
            st.success("✓ API key configured")
        else:
            st.warning("⚠️ No API key found")

    with col2:
        try:
            # Try to import agent module
            from streamlit_notebook import agent
            st.success("✓ Agent dependencies installed")
        except ImportError:
            st.warning("⚠️ Agent dependencies not installed")

    if not has_key:
        st.info("Set OPENAI_API_KEY to enable the AI agent");


@nb.cell(type='markdown', minimized=True)
def agent_capabilities():
    r'''
    ## Agent Capabilities

    **Cell Operations:**
    - Create new cells with code, markdown, or HTML
    - Edit existing cell content
    - Run cells and debug errors
    - Delete or reorder cells

    **Data Analysis:**
    - Read and analyze CSV, JSON, Excel files
    - Generate charts and visualizations
    - Perform statistical analysis
    - Clean and transform data

    **Notebook Control:**
    - Access the `__notebook__` API
    - Modify configuration and layout
    - Navigate between notebooks
    - Save and load notebook files

    **Code Assistance:**
    - Debug errors and exceptions
    - Optimize performance
    - Suggest improvements
    - Answer technical questions
    '''


@nb.cell(type='markdown', minimized=True)
def chat_mode():
    r'''
    ## Chat Mode

    When the agent is enabled, you'll see an **AI Chat** button in the sidebar.
    Click it to enter chat mode where you can:

    - Ask the agent to create cells
    - Request data analysis
    - Get help with errors
    - Generate visualizations

    The agent has full access to your notebook via `__notebook__` and can
    programmatically create and modify cells.
    '''


@nb.cell(type='markdown', minimized=True)
def agent_workflow():
    r'''
    ## Example Agent Workflow

    1. **Load data**: "Load the sales.csv file and show me a summary"
       → Agent creates a cell that loads and displays data

    2. **Analyze**: "Show me sales trends by month"
       → Agent creates cells with grouping logic and a line chart

    3. **Refine**: "Make the chart interactive with a region filter"
       → Agent adds widget controls and updates the visualization

    4. **Debug**: "The chart isn't updating when I change the filter"
       → Agent identifies the issue and fixes the code

    The agent understands the notebook context and can build on previous cells.
    '''


@nb.cell(type='markdown', minimized=True)
def system_prompt():
    r'''
    ## Customization

    You can customize the agent's behavior via the settings dialog:
    - **Model selection** - Choose GPT model
    - **Temperature** - Control creativity vs consistency
    - **System prompt** - Customize agent instructions
    - **Token limits** - Control response length

    The agent is powered by OpenAI's API and supports the latest GPT models.
    '''


@nb.cell(type='markdown', minimized=True)
def best_practices():
    r'''
    ## Best Practices

    ✅ **Be specific** in your requests
    ✅ **Review generated code** before running
    ✅ **Iterate** - refine the agent's output
    ✅ **Use for exploration** - let the agent suggest approaches

    ⚠️ **Remember**:
    - The agent executes code in your notebook environment
    - Always review before running on sensitive data
    - Agent responses cost API credits
    '''


@nb.cell(type='markdown', minimized=True)
def conclusion():
    r'''
    ## Congratulations!

    You've completed the Streamlit Notebook tour! You now know how to:

    ✓ Create one-shot and reactive cells
    ✓ Use display() for persistent output
    ✓ Manage widgets and state
    ✓ Interpolate variables in Markdown/HTML
    ✓ Configure layouts and styling
    ✓ Use fragments and auto-refresh
    ✓ Control notebooks programmatically
    ✓ Manage reruns and delays
    ✓ Deploy to production
    ✓ Integrate AI assistance (optional)

    **Ready to build?** Start creating your own interactive notebooks!
    '''


@nb.cell(type='code', reactive=True, minimized=True)
def navigation():
    st.markdown("---")
    from streamlit_notebook.demo_notebooks.helpers import navigation
    navigation()

nb.render()


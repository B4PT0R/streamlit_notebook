# Tutorial 05: Markdown and HTML Cells
# Live variable interpolation with <<expression>> syntax

from streamlit_notebook import st_notebook
import streamlit as st

nb = st_notebook(title='05_markdown_and_interpolation')


@nb.cell(type='markdown', minimized=True)
def intro():
    r'''
    # Markdown and HTML Cells

    Beyond code cells, you can create **Markdown** and **HTML** cells with
    live variable interpolation.
    '''


@nb.cell(type='markdown', minimized=True)
def interpolation_syntax():
    r'''
    ## The `<<expression>>` Syntax

    Use `<<expr>>` to embed live Python expressions in Markdown or HTML cells.
    The expressions are evaluated in the notebook's namespace.
    '''


@nb.cell(type='code', reactive=False)
def setup_data():
    import pandas as pd
    import numpy as np
    from datetime import datetime

    # Create sample data
    np.random.seed(777)
    sales_data = {
        'Q1': 45_230,
        'Q2': 52_100,
        'Q3': 48_900,
        'Q4': 61_450
    }

    total_sales = sum(sales_data.values())
    avg_sales = total_sales // 4
    best_quarter = max(sales_data, key=sales_data.get)

    # Analyst info
    analyst_name = "Jordan Smith"
    report_date = datetime.now().strftime("%B %d, %Y")

    print("✓ Data prepared for interpolation")


@nb.cell(type='markdown', minimized=False)
def markdown_interpolation_demo():
    r'''
    ## Sales Report - <<report_date>>

    **Prepared by**: <<analyst_name>>

    ### Quarterly Performance

    - **Q1**: $<<f"{sales_data['Q1']:,}">>
    - **Q2**: $<<f"{sales_data['Q2']:,}">>
    - **Q3**: $<<f"{sales_data['Q3']:,}">>
    - **Q4**: $<<f"{sales_data['Q4']:,}">>

    ### Summary

    - Total annual sales: **$<<f"{total_sales:,}">>**
    - Average per quarter: **$<<f"{avg_sales:,}">>**
    - Best performing quarter: **<<best_quarter>>** with $<<f"{sales_data[best_quarter]:,}">>
    - Growth potential: <<f"{(sales_data['Q4'] / sales_data['Q1'] - 1) * 100:.1f}">>%
    '''


@nb.cell(type='code', reactive=True)
def interactive_threshold():
    st.subheader("Interactive Filtering")

    threshold = st.slider(
        "Sales threshold ($)",
        min_value=40000,
        max_value=70000,
        value=50000,
        step=1000,
        key='slider_threshold_05'
    )

    # Store in namespace for interpolation
    filtered_quarters = [q for q, v in sales_data.items() if v >= threshold]
    filter_threshold = threshold


@nb.cell(type='markdown', minimized=False, reactive=True)
def live_filtered_results():
    r'''
    ### Filtered Results

    Quarters with sales ≥ $<<f"{filter_threshold:,}">>:

    <<", ".join(filtered_quarters) if filtered_quarters else "None">>

    (we made this cell reactive, so it updates when you move the slider)
    '''


@nb.cell(type='html', minimized=True)
def html_cell_demo():
    r'''
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px; border-radius: 10px; color: white; margin: 10px 0;">
        <h3 style="margin: 0 0 10px 0;">HTML Cell with Interpolation</h3>
        <p style="margin: 5px 0;">Total Sales: <strong>$<<f"{total_sales:,}">></strong></p>
        <p style="margin: 5px 0;">Best Quarter: <strong><<best_quarter>></strong></p>
        <p style="margin: 5px 0; font-size: 0.9em; opacity: 0.9;">
            You can use full HTML with CSS styling!
        </p>
    </div>
    '''


@nb.cell(type='markdown', minimized=True)
def best_practices():
    r'''
    ## Tips

    ✅ Use **Markdown cells** for formatted text and reports
    ✅ Use **HTML cells** for custom styling and layouts
    ✅ Keep expressions simple for readability
    ✅ Use f-strings for number formatting: `<<f"{value:,}">>`

    ❌ Avoid complex logic in interpolations
    '''


@nb.cell(type='code', reactive=True, minimized=True)
def navigation():
    st.markdown("---")
    from streamlit_notebook.demo_notebooks.helpers import navigation
    navigation()

nb.render()

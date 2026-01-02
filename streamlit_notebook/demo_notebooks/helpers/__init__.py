def navigation():
    from streamlit_notebook.core.utils import root_join
    from streamlit_notebook import get_notebook
    import streamlit as st
    import os

    nb=get_notebook()

    TUTORIALS = sorted([f for f in os.listdir(root_join('demo_notebooks')) if f.endswith('.py')])
    current_name = nb.config.title + '.py'
    idx = TUTORIALS.index(current_name)
    prev_name = TUTORIALS[idx - 1] if idx > 0 else None
    next_name = TUTORIALS[idx + 1] if idx + 1 < len(TUTORIALS) else None

    with st.container(horizontal=True, horizontal_alignment='center', vertical_alignment='center'):
        if st.button("← Previous", key='nav_prev', disabled=prev_name is None, width="stretch"):
            nb.open(root_join('demo_notebooks', prev_name))
        
        with st.container():
            #st.space(size='small')
            st.markdown(f"Tutorial {idx+1} of {len(TUTORIALS)}", text_alignment='center', width="stretch")

        if st.button("Next →", key='nav_next', disabled=next_name is None, width="stretch"):
            nb.open(root_join('demo_notebooks', next_name))
import streamlit as st

st.set_page_config(
    page_title="TCM.io",
    page_icon="🏔️",
    layout="centered"
)

pg = st.navigation([
    st.Page("pages/home.py", title="Home ⌂"),
    st.Page("pages/1_Business_Development.py", title="Business Development ⚒"),
    st.Page("pages/2_Asset_Management.py", title="Asset Management ⚛"),
    st.Page("pages/3_Reporting.py", title="Reporting ⚠"),
    st.Page("pages/4_Research.py", title="Research ⌕"),
    st.Page("pages/5_Extra.py", title="Extra ⋯"),
])

pg.run()

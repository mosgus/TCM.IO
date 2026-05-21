import streamlit as st

#st.title("Home")
st.caption("ver 0.1")

st.divider()

st.markdown("""
### Welcome

TCM.io is an internal toolset for TCM's workflow.
Use the navigation tabs on the left to access each module.

Visit https://tcm-io-tester.streamlit.app/ to see prototype features.

| Module | Status | Description |
|---|---|---|
| **Business Development** | Working on it | Pipeline and deal tracking |
| **Asset Management** | Not started | Portfolio monitoring |
| **Reporting** | Not Started | Report generation and exports |
| **Research** | Live ✅ | Basic AI-powered property x tenant research |
| **Blank** | Placeholder | Additional models and tools. Likely a Cap Raising module |
""")

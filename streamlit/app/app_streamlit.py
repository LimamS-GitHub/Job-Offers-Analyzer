import streamlit as st


if "all_offers" not in st.session_state:
    st.session_state.all_offers = []


pg = st.navigation(
    [
        "Overview.py",
        "Job_collection.py",
        "Analysis.py",
        "access_jobs.py",
    ]
)

pg.run()

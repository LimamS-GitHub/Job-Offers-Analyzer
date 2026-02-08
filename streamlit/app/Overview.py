import streamlit as st

st.title("Welcome to the Job Offers & Skills Analyzer")

st.write(
    """
This application lets you:
1) Collect job offers from HelloWork
2) Extract skills (hard/soft), domains, and minimum experience
3) Analyze and visualize the results
"""
)

# Pipeline status
offers = st.session_state.get("all_offers", [])
st.subheader("Current session status")
if offers:
    st.success(f"{len(offers)} offers collected in this session.")
else:
    st.info("No offers collected yet. Start with the Job collection page.")

st.markdown("---")

st.subheader("How to use")
st.write(
    """
- Go to **Job collection** to scrape and enrich offers
- Then open **Analysis** to explore skills and insights
"""
)

# Optional: reset button
col1, col2 = st.columns(2)
with col1:
    if st.button("Reset session data"):
        st.session_state["all_offers"] = []
        st.success("Session cleared.")

with col2:
    st.caption("Tip: collect first, then analyze.")

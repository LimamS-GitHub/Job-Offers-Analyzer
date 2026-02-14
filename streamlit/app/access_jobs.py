import streamlit as st
import pandas as pd
import re

st.title("Access Jobs")

# --- Security: data available?
if "all_offers" not in st.session_state or not st.session_state.all_offers:
    st.info("No data available. Please run the scraping first.")
    st.stop()

df = pd.DataFrame(st.session_state.all_offers).copy()

# --- Helpers
def parse_years(x):
    if pd.isna(x):
        return None
    m = re.search(r"(\d+)", str(x))
    return int(m.group(1)) if m else None

def safe_to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")

# --- Prepare useful columns
if "date" in df.columns:
    df["date_dt"] = safe_to_datetime(df["date"])
else:
    df["date_dt"] = pd.NaT

if "years_experience_min" in df.columns:
    df["years_num"] = df["years_experience_min"].apply(parse_years)
else:
    df["years_num"] = None

# --- Sidebar filters
st.sidebar.header("Filters")

df_f = df.copy()

# 1) Text search (title / company / location)
q = st.sidebar.text_input("Search (job title, company, location)", value="").strip()
if q:
    cols = [c for c in ["title", "company", "location"] if c in df_f.columns]
    if cols:
        mask = False
        for c in cols:
            mask = mask | df_f[c].fillna("").str.contains(q, case=False, regex=False)
        df_f = df_f[mask]

# 2) Contract type
if "contract_type" in df_f.columns:
    opts = sorted([x for x in df_f["contract_type"].dropna().unique()])
    if opts:
        selected = st.sidebar.multiselect("Contract type", opts, default=opts)
        df_f = df_f[df_f["contract_type"].isin(selected)] if selected else df_f.iloc[0:0]

# 3) Location
if "location" in df_f.columns:
    locs = sorted([x for x in df_f["location"].dropna().unique()])
    if locs:
        selected_locs = st.sidebar.multiselect("Location", locs, default=[])
        if selected_locs:
            df_f = df_f[df_f["location"].isin(selected_locs)]

# 4) Company
if "company" in df_f.columns:
    companies = sorted([x for x in df_f["company"].dropna().unique()])
    if companies:
        selected_companies = st.sidebar.multiselect("Company", companies, default=[])
        if selected_companies:
            df_f = df_f[df_f["company"].isin(selected_companies)]

# 5) Date range
if df_f["date_dt"].notna().any():
    dmin = df_f["date_dt"].min().date()
    dmax = df_f["date_dt"].max().date()
    d1, d2 = st.sidebar.date_input("Date range", value=(dmin, dmax))
    df_f = df_f[
        df_f["date_dt"].between(
            pd.to_datetime(d1),
            pd.to_datetime(d2),
            inclusive="both"
        )
    ]

# 6) Experience (years)
if df_f["years_num"].notna().any():
    mn = int(df_f["years_num"].min())
    mx = int(df_f["years_num"].max())
    if mn == mx:
        st.sidebar.caption(f"Experience: {mn} year(s) (single value)")
    else:
        r = st.sidebar.slider("Experience (years)", mn, mx, (mn, mx), step=1)
        df_f = df_f[df_f["years_num"].between(r[0], r[1])]

# --- Results
st.subheader("Results")

col1, col2 = st.columns(2)
col1.metric("Filtered job offers", len(df_f))
col2.metric("Total job offers", len(df))

display_cols = [
    "title",
    "company",
    "location",
    "contract_type",
    "years_experience_min",
    "date",
    "url",
]

display_cols = [c for c in display_cols if c in df_f.columns]
df_display = df_f[display_cols].copy()

# Rename columns for UI
df_display = df_display.rename(columns={
    "title": "Job title",
    "company": "Company",
    "location": "Location",
    "contract_type": "Contract",
    "years_experience_min": "Min experience (years)",
    "date": "Published date",
    "url": "Link",
})

def render_html_table(df):
    html = "<table style='width:100%; border-collapse:collapse;'>"
    html += "<tr>" + "".join(
        f"<th style='border-bottom:1px solid #ddd; text-align:left; padding:8px;'>{col}</th>"
        for col in df.columns
    ) + "</tr>"

    for _, row in df.iterrows():
        html += "<tr>"
        for col in df.columns:
            val = row[col]
            if col == "Link" and pd.notna(val):
                html += f"<td><a href='{val}' target='_blank'>Open</a></td>"
            else:
                html += f"<td style='padding:6px;'>{val}</td>"
        html += "</tr>"

    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

render_html_table(df_display)

st.download_button(
    "Download results (CSV)",
    df_f.to_csv(index=False).encode("utf-8"),
    file_name="job_offers_filtered.csv",
    mime="text/csv",
)

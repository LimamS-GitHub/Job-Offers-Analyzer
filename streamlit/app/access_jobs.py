import streamlit as st
import pandas as pd
import re

st.title("Access Jobs")

# --- Sécurité : données dispo ?
if "all_offers" not in st.session_state or not st.session_state.all_offers:
    st.info("Aucune donnée disponible. Lance d'abord le scraping.")
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

# --- Préparation colonnes utiles
if "date" in df.columns:
    df["date_dt"] = safe_to_datetime(df["date"])
else:
    df["date_dt"] = pd.NaT

if "years_experience_min" in df.columns:
    df["years_num"] = df["years_experience_min"].apply(parse_years)
else:
    df["years_num"] = None

# --- Sidebar filtres
st.sidebar.header("Filtres")

df_f = df.copy()

# 1) Recherche texte (titre / company / location)
q = st.sidebar.text_input("Recherche (titre, entreprise, lieu)", value="").strip()
if q:
    cols = [c for c in ["title", "company", "location"] if c in df_f.columns]
    if cols:
        mask = False
        for c in cols:
            mask = mask | df_f[c].fillna("").str.contains(q, case=False, regex=False)
        df_f = df_f[mask]

# 2) Contrat
if "contract_type" in df_f.columns:
    opts = sorted([x for x in df_f["contract_type"].dropna().unique()])
    if opts:
        selected = st.sidebar.multiselect("Type de contrat", opts, default=opts)
        df_f = df_f[df_f["contract_type"].isin(selected)] if selected else df_f.iloc[0:0]

# 3) Localisation
if "location" in df_f.columns:
    locs = sorted([x for x in df_f["location"].dropna().unique()])
    if locs:
        selected_locs = st.sidebar.multiselect("Localisation", locs, default=[])
        if selected_locs:
            df_f = df_f[df_f["location"].isin(selected_locs)]

# 4) Entreprise
if "company" in df_f.columns:
    companies = sorted([x for x in df_f["company"].dropna().unique()])
    if companies:
        selected_companies = st.sidebar.multiselect("Entreprise", companies, default=[])
        if selected_companies:
            df_f = df_f[df_f["company"].isin(selected_companies)]

# 5) Période (dates)
if df_f["date_dt"].notna().any():
    dmin = df_f["date_dt"].min().date()
    dmax = df_f["date_dt"].max().date()
    d1, d2 = st.sidebar.date_input("Période", value=(dmin, dmax))
    df_f = df_f[df_f["date_dt"].between(pd.to_datetime(d1), pd.to_datetime(d2), inclusive="both")]

# 6) Expérience (années)
if df_f["years_num"].notna().any():
    mn = int(df_f["years_num"].min())
    mx = int(df_f["years_num"].max())
    if mn == mx:
        st.sidebar.caption(f"Expérience: {mn} an(s) (valeur unique)")
    else:
        r = st.sidebar.slider("Expérience (années)", mn, mx, (mn, mx), step=1)
        df_f = df_f[df_f["years_num"].between(r[0], r[1])]

# --- Résultats
st.subheader("Résultats")

col1, col2 = st.columns(2)
col1.metric("Offres filtrées", len(df_f))
col2.metric("Offres totales", len(df))

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

# Sort by date if exists
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
                html += f"<td><a href='{val}' target='_blank'>Link</a></td>"
            else:
                html += f"<td style='padding:6px;'>{val}</td>"
        html += "</tr>"

    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

render_html_table(df_display)


st.download_button(
    "Télécharger les résultats (CSV)",
    df_f.to_csv(index=False).encode("utf-8"),
    file_name="job_offers_filtered.csv",
    mime="text/csv",
)

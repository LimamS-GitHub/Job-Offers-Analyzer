import streamlit as st
import pandas as pd
import re

st.title("Data Analysis")

# Sécurité : données disponibles ?
if "all_offers" not in st.session_state or not st.session_state.all_offers:
    st.info("Aucune donnée disponible. Lance d'abord le scraping.")
    st.stop()

df = pd.DataFrame(st.session_state.all_offers)

# Aperçu & infos générales
with st.expander("🔍 Aperçu des données", expanded=True):
    st.write(f"Nombre total d'offres : **{len(df)}**")
    st.dataframe(df.head(20), use_container_width=True)
    st.download_button("Télécharger les données (CSV)", df.to_csv(index=False), "job_offers.csv", "text/csv")

# Vérification des colonnes attendues
required_cols = {"hard_skills", "soft_skills"}
missing_cols = required_cols - set(df.columns)
if missing_cols:
    st.warning(f"Colonnes manquantes pour l'analyse : {', '.join(missing_cols)}")
    st.stop()

def to_list(x):
    """Accepte list, string 'a,b;c|d', sinon retourne []"""
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        parts = re.split(r"[;,|]", x)
        return [p.strip() for p in parts if p.strip()]
    return []

def clean_skill(s: str) -> str:
    """Nettoyage léger : trim + lower + espaces multiples"""
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def parse_years(x):
    """Extrait le premier nombre de '6 années', '3 ans', etc."""
    if pd.isna(x):
        return None
    m = re.search(r"(\d+)", str(x))
    return int(m.group(1)) if m else None

# Nettoyage léger (robustesse)
df["hard_skills"] = df["hard_skills"].apply(to_list).apply(lambda lst: [clean_skill(x) for x in lst if str(x).strip()])
df["soft_skills"] = df["soft_skills"].apply(to_list).apply(lambda lst: [clean_skill(x) for x in lst if str(x).strip()])

# Expérience (si dispo)
has_exp = "years_experience_min" in df.columns
if has_exp:
    df["years_num"] = df["years_experience_min"].apply(parse_years)

# Paramètres utilisateur
top_n = st.slider("Nombre de compétences à afficher", 5, 50, 20, 5)

# Onglets pour une lecture claire (+ Expérience + Villes)
tab_hard, tab_soft, tab_exp, tab_city = st.tabs(["🛠 Hard Skills", "🧠 Soft Skills", "📈 Expérience", "🏙️ Villes"])

with tab_hard:
    hard_freq = df["hard_skills"].explode().dropna()
    hard_freq = hard_freq[hard_freq != ""].value_counts().head(top_n)

    if hard_freq.empty:
        st.warning("Aucune hard skill exploitable.")
    else:
        st.subheader("Top Hard Skills")
        st.bar_chart(hard_freq)

        st.dataframe(
            hard_freq.reset_index().rename(columns={"index": "Hard Skill", "count": "Occurrences"}),
            use_container_width=True,
        )

with tab_soft:
    soft_freq = df["soft_skills"].explode().dropna()
    soft_freq = soft_freq[soft_freq != ""].value_counts().head(top_n)

    if soft_freq.empty:
        st.warning("Aucune soft skill exploitable.")
    else:
        st.subheader("Top Soft Skills")
        st.bar_chart(soft_freq)

        st.dataframe(
            soft_freq.reset_index().rename(columns={"index": "Soft Skill", "count": "Occurrences"}),
            use_container_width=True,
        )

with tab_exp:
    if not has_exp:
        st.info("Colonne 'years_experience_min' absente → pas d'analyse expérience.")
        st.stop()

    exp_series = df["years_num"].dropna()
    if exp_series.empty:
        st.warning("Impossible d'extraire un nombre d'années d'expérience.")
        st.stop()

    st.subheader("Distribution des années d'expérience demandées")
    exp_counts = exp_series.value_counts().sort_index()
    st.bar_chart(exp_counts)

    st.dataframe(
        exp_counts.reset_index().rename(columns={"index": "Années", "years_num": "Années", 0: "Années"}),
        use_container_width=True,
    )

    st.divider()

    bins = [0, 2, 4, 6, 9, 50]
    labels = ["0-2", "3-4", "5-6", "7-9", "10+"]

    df_exp = df.dropna(subset=["years_num"]).copy()
    df_exp["exp_bucket"] = pd.cut(df_exp["years_num"], bins=bins, labels=labels, include_lowest=True)

    st.subheader("Hard skills par tranche d'expérience")
    bucket = st.selectbox("Choisis une tranche d'expérience", labels, index=1)

    df_bucket = df_exp[df_exp["exp_bucket"] == bucket]

    if df_bucket.empty:
        st.warning("Aucune offre dans cette tranche.")
    else:
        bucket_freq = df_bucket["hard_skills"].explode().dropna()
        bucket_freq = bucket_freq[bucket_freq != ""].value_counts().head(top_n)

        if bucket_freq.empty:
            st.warning("Aucune hard skill exploitable dans cette tranche.")
        else:
            st.write(f"Top hard skills pour **{bucket} ans** (sur {len(df_bucket)} offres)")
            st.bar_chart(bucket_freq)

            st.dataframe(
                bucket_freq.reset_index().rename(columns={"index": "Hard Skill", "count": "Occurrences"}),
                use_container_width=True,
            )

    st.divider()

    st.subheader("Soft skills par tranche d'expérience")
    bucket = st.selectbox("Choisis une tranche d'expérience", labels, index=1, key="soft_exp_bucket")

    df_bucket = df_exp[df_exp["exp_bucket"] == bucket]

    if df_bucket.empty:
        st.warning("Aucune offre dans cette tranche.")
    else:
        bucket_freq = df_bucket["soft_skills"].explode().dropna()
        bucket_freq = bucket_freq[bucket_freq != ""].value_counts().head(top_n)

        if bucket_freq.empty:
            st.warning("Aucune soft skill exploitable dans cette tranche.")
        else:
            st.write(f"Top soft skills pour **{bucket} ans** (sur {len(df_bucket)} offres)")
            st.bar_chart(bucket_freq)

            st.dataframe(
                bucket_freq.reset_index().rename(columns={"index": "Soft Skill", "count": "Occurrences"}),
                use_container_width=True,
            )

with tab_city:
    st.subheader("Top villes citées")

    if "location" not in df.columns:
        st.info("Colonne 'location' absente → pas d'analyse villes.")
        st.stop()

    def extract_city(loc: str):
        if not isinstance(loc, str) or not loc.strip():
            return None

        loc = loc.strip()

        # Séparateur réel HelloWork : " - "
        if " - " in loc:
            loc = loc.split(" - ")[0].strip()

        # Supprimer les arrondissements / numéros en fin
        loc = re.sub(r"\s+\d+(e|er)?$", "", loc, flags=re.IGNORECASE)

        # Nettoyage final : lettres, accents, espaces, apostrophes, tirets
        m = re.match(r"^[A-Za-zÀ-ÿ'\-\s]+$", loc)
        if not m:
            return None

        return loc.strip() if loc.strip() else None


    df_loc = df[["location"]].copy()
    df_loc["city"] = df_loc["location"].apply(extract_city)

    city_counts = df_loc["city"].dropna()
    city_counts = city_counts[city_counts != ""].value_counts()

    if city_counts.empty:
        st.warning("Aucune localisation exploitable.")
        st.stop()

    nb_cities = len(city_counts)

    if nb_cities <= 1:
        st.info("Pas assez de villes différentes pour afficher un slider.")
        top_cities = nb_cities
    else:
        min_v = 1
        max_v = nb_cities
        default_v = min(20, nb_cities)

        top_cities = st.slider(
            "Nombre de villes à afficher",
            min_value=min_v,
            max_value=max_v,
            value=default_v,
            step=1,
        )

    city_counts = city_counts.head(top_cities)

    st.bar_chart(city_counts)

    st.dataframe(
        city_counts.reset_index().rename(columns={"index": "Ville", "count": "Offres"}),
        use_container_width=True,
    )

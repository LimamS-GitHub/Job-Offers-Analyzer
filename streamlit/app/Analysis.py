import streamlit as st
import pandas as pd
import re

st.title("Data Analysis")

# Security: data available?
if "all_offers" not in st.session_state or not st.session_state.all_offers:
    st.info("No data available. Please run the data collection first.")
    st.stop()

df = pd.DataFrame(st.session_state.all_offers)

# Overview & general info
with st.expander("🔍 Data Overview", expanded=True):
    st.write(f"Total number of job offers: **{len(df)}**")
    st.dataframe(df.head(20), use_container_width=True)
    st.download_button(
        "Download data (CSV)",
        df.to_csv(index=False),
        "job_offers.csv",
        "text/csv"
    )

# Check required columns
required_cols = {"hard_skills", "soft_skills"}
missing_cols = required_cols - set(df.columns)
if missing_cols:
    st.warning(f"Missing columns for analysis: {', '.join(missing_cols)}")
    st.stop()

def to_list(x):
    """Accepts list, string 'a,b;c|d', otherwise returns []"""
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        parts = re.split(r"[;,|]", x)
        return [p.strip() for p in parts if p.strip()]
    return []

def clean_skill(s: str) -> str:
    """Light cleaning: trim + lower + collapse spaces"""
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def parse_years(x):
    """Extracts first number from '6 years', '3 yrs', etc."""
    if pd.isna(x):
        return None
    m = re.search(r"(\d+)", str(x))
    return int(m.group(1)) if m else None

# Light cleaning (robustness)
df["hard_skills"] = df["hard_skills"].apply(to_list).apply(
    lambda lst: [clean_skill(x) for x in lst if str(x).strip()]
)
df["soft_skills"] = df["soft_skills"].apply(to_list).apply(
    lambda lst: [clean_skill(x) for x in lst if str(x).strip()]
)

# Experience (if available)
has_exp = "years_experience_min" in df.columns
if has_exp:
    df["years_num"] = df["years_experience_min"].apply(parse_years)

# User parameters
top_n = st.slider("Number of skills to display", 5, 50, 20, 5)

# Tabs for clear reading (+ Experience + Cities)
tab_hard, tab_soft, tab_exp, tab_city = st.tabs(
    ["🛠 Hard Skills", "🧠 Soft Skills", "📈 Experience", "🏙️ Cities"]
)

with tab_hard:
    hard_freq = df["hard_skills"].explode().dropna()
    hard_freq = hard_freq[hard_freq != ""].value_counts().head(top_n)

    if hard_freq.empty:
        st.warning("No usable hard skills found.")
    else:
        st.subheader("Top Hard Skills")
        st.bar_chart(hard_freq)

        st.dataframe(
            hard_freq.reset_index().rename(
                columns={"index": "Hard Skill", "count": "Occurrences"}
            ),
            use_container_width=True,
        )

with tab_soft:
    soft_freq = df["soft_skills"].explode().dropna()
    soft_freq = soft_freq[soft_freq != ""].value_counts().head(top_n)

    if soft_freq.empty:
        st.warning("No usable soft skills found.")
    else:
        st.subheader("Top Soft Skills")
        st.bar_chart(soft_freq)

        st.dataframe(
            soft_freq.reset_index().rename(
                columns={"index": "Soft Skill", "count": "Occurrences"}
            ),
            use_container_width=True,
        )

with tab_exp:
    if not has_exp:
        st.info("Column 'years_experience_min' not found → no experience analysis.")
        st.stop()

    exp_series = df["years_num"].dropna()
    if exp_series.empty:
        st.warning("Unable to extract years of experience.")
        st.stop()

    st.subheader("Distribution of required years of experience")
    exp_counts = exp_series.value_counts().sort_index()
    st.bar_chart(exp_counts)

    st.dataframe(
        exp_counts.reset_index().rename(
            columns={"index": "Years", "years_num": "Years", 0: "Years"}
        ),
        use_container_width=True,
    )

    st.divider()

    bins = [0, 2, 4, 6, 9, 50]
    labels = ["0-2", "3-4", "5-6", "7-9", "10+"]

    df_exp = df.dropna(subset=["years_num"]).copy()
    df_exp["exp_bucket"] = pd.cut(
        df_exp["years_num"], bins=bins, labels=labels, include_lowest=True
    )

    st.subheader("Hard skills by experience level")
    bucket = st.selectbox("Select an experience range", labels, index=1)

    df_bucket = df_exp[df_exp["exp_bucket"] == bucket]

    if df_bucket.empty:
        st.warning("No job offers in this range.")
    else:
        bucket_freq = df_bucket["hard_skills"].explode().dropna()
        bucket_freq = bucket_freq[bucket_freq != ""].value_counts().head(top_n)

        if bucket_freq.empty:
            st.warning("No usable hard skills in this range.")
        else:
            st.write(
                f"Top hard skills for **{bucket} years** "
                f"(based on {len(df_bucket)} job offers)"
            )
            st.bar_chart(bucket_freq)

            st.dataframe(
                bucket_freq.reset_index().rename(
                    columns={"index": "Hard Skill", "count": "Occurrences"}
                ),
                use_container_width=True,
            )

    st.divider()

    st.subheader("Soft skills by experience level")
    bucket = st.selectbox(
        "Select an experience range",
        labels,
        index=1,
        key="soft_exp_bucket",
    )

    df_bucket = df_exp[df_exp["exp_bucket"] == bucket]

    if df_bucket.empty:
        st.warning("No job offers in this range.")
    else:
        bucket_freq = df_bucket["soft_skills"].explode().dropna()
        bucket_freq = bucket_freq[bucket_freq != ""].value_counts().head(top_n)

        if bucket_freq.empty:
            st.warning("No usable soft skills in this range.")
        else:
            st.write(
                f"Top soft skills for **{bucket} years** "
                f"(based on {len(df_bucket)} job offers)"
            )
            st.bar_chart(bucket_freq)

            st.dataframe(
                bucket_freq.reset_index().rename(
                    columns={"index": "Soft Skill", "count": "Occurrences"}
                ),
                use_container_width=True,
            )

with tab_city:
    st.subheader("Top mentioned cities")

    if "location" not in df.columns:
        st.info("Column 'location' not found → no city analysis.")
        st.stop()

    def extract_city(loc: str):
        if not isinstance(loc, str) or not loc.strip():
            return None

        loc = loc.strip()

        # HelloWork real separator: " - "
        if " - " in loc:
            loc = loc.split(" - ")[0].strip()

        # Remove district numbers / suffixes
        loc = re.sub(r"\s+\d+(e|er)?$", "", loc, flags=re.IGNORECASE)

        # Final cleanup: letters, accents, spaces, apostrophes, hyphens
        m = re.match(r"^[A-Za-zÀ-ÿ'\-\s]+$", loc)
        if not m:
            return None

        return loc.strip() if loc.strip() else None

    df_loc = df[["location"]].copy()
    df_loc["city"] = df_loc["location"].apply(extract_city)

    city_counts = df_loc["city"].dropna()
    city_counts = city_counts[city_counts != ""].value_counts()

    if city_counts.empty:
        st.warning("No usable locations found.")
        st.stop()

    nb_cities = len(city_counts)

    if nb_cities <= 1:
        st.info("Not enough different cities to display a slider.")
        top_cities = nb_cities
    else:
        top_cities = st.slider(
            "Number of cities to display",
            min_value=1,
            max_value=nb_cities,
            value=min(20, nb_cities),
            step=1,
        )

    city_counts = city_counts.head(top_cities)

    st.bar_chart(city_counts)

    st.dataframe(
        city_counts.reset_index().rename(
            columns={"index": "City", "count": "Job Offers"}
        ),
        use_container_width=True,
    )

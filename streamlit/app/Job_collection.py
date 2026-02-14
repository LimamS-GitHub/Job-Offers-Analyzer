import os
import streamlit as st
import time
import httpx
import json
from urllib.parse import urlencode, quote_plus, urljoin
from bs4 import BeautifulSoup
from datetime import date, timedelta
from typing import Optional, Dict, List, Tuple
import re
import google.generativeai as genai
from dotenv import load_dotenv

# Configuration constants
MAX_PAGE_HARDCAP = 500
BASE_URL = "https://www.hellowork.com"
SEARCH_PATH = "/fr-fr/emploi/recherche.html"
load_dotenv()
api_key = os.getenv("GENAI_API_KEY")
if not api_key:
    raise RuntimeError("Missing GEMINI_API_KEY (environment variable).")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}

genai.configure(api_key=api_key)
MODEL = genai.GenerativeModel("gemini-2.5-flash-lite")

def prompt_gemini(job_offer: str) -> str:
    return f"""
    You are an information extractor for job offers.
    Reply ONLY with valid JSON. No markdown. No extra text.

    Constraints:
    - Do not invent anything.
    - If missing: null or [].
    - Deduplicate, trim, normalize (same casing).
    - Follow EXACTLY the keys below.

    Expected JSON:
    {{
    "hard_skills": [],
    "soft_skills": [],
    "years_experience_min": null,
    "domains": []
    }}

    Text:
    \"\"\"{job_offer}\"\"\"
    """.strip()

def build_search_url(job: str, country: str, contract_type: str = "") -> str:
    """
    Builds the HelloWork search URL (encoding parameters).
    """
    job = job.strip()
    country = country.strip()
    contract_type = contract_type.strip()

    query_params = {
        "k": job,
        "k_autocomplete": "",
        "l": country,
        "c": contract_type,
        "l_autocomplete": "http://www.rj.com/commun/localite/commune/75056",
        "st": "relevance",
        "ray": 20,
        "d": "all",
    }

    query = urlencode(query_params, quote_via=quote_plus)
    return f"{BASE_URL}{SEARCH_PATH}?{query}"

def extract_text(
    parent: BeautifulSoup,
    name: str,
    class_name: Optional[str] = None,
    attrs: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Extracts cleaned text from an HTML element.
    Returns None if not found.
    """
    attrs = attrs or {}
    elem = parent.find(name, class_=class_name, attrs=attrs)
    return elem.get_text(strip=True) if elem else None

def parse_relative_date(date_string: str) -> date:
    days = re.findall(r"\d+", date_string)
    return date.today() - timedelta(days=int(days[0])) if days else date.today()

def parse_last_page(soup: BeautifulSoup) -> int:
    """
    Gets the last page number from pagination.
    Returns 1 by default if nothing is found.
    """
    nav = soup.find(
        "nav",
        class_="tw-hidden sm:tw-flex tw-gap-2 tw-typo-m tw-flex-wrap",
    )
    if not nav:
        return 1

    buttons = nav.find_all("button")
    number_buttons = [b for b in buttons if b.text.strip().isdigit()]
    if not number_buttons:
        return 1

    last_button = number_buttons[-1]
    return int(last_button.get_text(strip=True))

def extraction_offers_from_html(html: str) -> Tuple[List[Dict[str, Optional[str]]], int]:
    """
    Extracts the list of offers + total number of pages from a HelloWork HTML page.
    """
    soup = BeautifulSoup(html, "html.parser")
    offers: List[Dict[str, Optional[str]]] = []

    # Total number of pages
    last_page = parse_last_page(soup)

    # Offers list
    offer_ul_list = soup.select('ul[aria-label="liste des offres"]')
    if not offer_ul_list:
        return offers, last_page

    offer_ul = offer_ul_list[0]
    for li in offer_ul.find_all("li", recursive=False):
        offer_link = li.select_one('a[data-cy="offerTitle"]')
        href = offer_link.get("href", "") if offer_link else ""
        url = urljoin(BASE_URL, href) if href else None

        title = extract_text(
            li,
            "p",
            "tw-typo-l sm:small-group:tw-typo-l sm:tw-typo-xl",
        )

        published_date = (
            parse_relative_date(
                extract_text(
                    li,
                    "div",
                    "tw-typo-s tw-text-grey-500 tw-pl-1 tw-pt-1",
                )
            )
            if extract_text(
                li,
                "div",
                "tw-typo-s tw-text-grey-500 tw-pl-1 tw-pt-1",
            )
            else None
        )

        contract_type = extract_text(
            li,
            "div",
            "tw-readonly tw-tag-secondary-s tw-w-fit tw-border-0",
            attrs={"data-cy": "contractCard"},
        )
        location = extract_text(
            li,
            "div",
            "tw-readonly tw-tag-secondary-s tw-w-fit tw-border-0",
            attrs={"data-cy": "localisationCard"},
        )
        company = extract_text(li, "p", "tw-typo-s tw-inline")

        offers.append(
            {
                "title": title,
                "date": published_date,
                "url": url,
                "contract_type": contract_type,
                "location": location,
                "company": company,
            }
        )

    return offers, last_page

def fetch_html(url: str) -> Dict:
    """
    Downloads an HTML page.
    """
    with httpx.Client(
        timeout=20,
        follow_redirects=True,
        headers=DEFAULT_HEADERS,
    ) as client:
        r = client.get(url)
        content = r.content or b""

        return {
            "ok": (r.status_code == 200 and len(content) > 0),
            "status_code": r.status_code,
            "final_url": str(r.url),
            "content_length": len(content),
            "content_type": r.headers.get("content-type"),
            "headers_sample": {
                k: v
                for k, v in r.headers.items()
                if k.lower()
                in ["server", "location", "set-cookie", "cf-ray", "cf-cache-status", "retry-after"]
            },
            "html": content.decode(errors="replace"),
        }

def extract_text_from_job(url: str, client: httpx.Client) -> Dict[str, Optional[str]]:
    try:
        r = client.get(url, timeout=20, headers=DEFAULT_HEADERS)
        if r.status_code != 200 or not r.content:
            return {
                "hard_skills": [],
                "soft_skills": [],
                "years_experience_min": None,
                "domains": [],
            }

        soup = BeautifulSoup(r.text, "html.parser")

        mission_text = extract_text(
            soup,
            "div",
            class_name="tw-leading-relaxed",
            attrs={"data-truncate-text-target": True},
        )

        profil_recherche = extract_text(
            soup,
            "p",
            "tw-typo-long-m tw-break-words",
        )

        ul = soup.select_one("ul.tw-flex.tw-flex-wrap.tw-gap-3")
        experience = ul.find_all("li", recursive=False)[-1].get_text(strip=True) if ul else None
        experience_years = re.findall(r"\d+", experience)[0] if experience and "Exp." in experience else None

        # Build the text to analyze
        if mission_text and profil_recherche:
            job_offer = f"mission: {mission_text}\nprofile: {profil_recherche}"
        elif mission_text:
            job_offer = f"mission: {mission_text}"
        elif profil_recherche:
            job_offer = f"profile: {profil_recherche}"
        else:
            return {
                "hard_skills": None,
                "soft_skills": None,
                "years_experience_min": experience_years,
                "domains": None,
            }

        if metier.lower() not in job_offer.lower():
            return {
                "hard_skills": [],
                "soft_skills": [],
                "years_experience_min": None,
                "domains": [],
            }

        for _ in range(5):
            prompt = prompt_gemini(job_offer)

            # Gemini call
            result = MODEL.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )

            # Parse JSON response
            try:
                data = json.loads(result.text)
                if (
                    "hard_skills" not in data
                    or "soft_skills" not in data
                    or "years_experience_min" not in data
                    or "domains" not in data
                ):
                    st.warning(
                        f"Missing fields in response for offer {url}. Attempt {_+1}/5."
                    )
                    continue

                data["hard_skills"] = sorted(data["hard_skills"], key=str.lower)
                data["soft_skills"] = sorted(data["soft_skills"], key=str.lower)
                data["years_experience_min"] = (
                    int(data["years_experience_min"])
                    if data["years_experience_min"] is not None
                    else experience_years
                )
                return data
            except json.JSONDecodeError:
                continue

        st.warning(f"Extraction failed after 5 attempts for offer {url}.")
        return {
            "hard_skills": [],
            "soft_skills": [],
            "years_experience_min": None,
            "domains": [],
        }

    except Exception as e:
        st.warning(f"Error in extract_text_from_job: {e}")
        return {
            "hard_skills": [],
            "soft_skills": [],
            "years_experience_min": None,
            "domains": [],
        }

def enrich_offers(
    client: httpx.Client,
    offers: List[Dict[str, Optional[str]]],
    max_num_of_offers: int,
    status_box,
    bar,
) -> List[Dict[str, Optional[str]]]:
    results = []

    for i, offer in enumerate(offers):
        url = offer.get("url")
        if not url:
            continue

        data = extract_text_from_job(url, client)
        if data["hard_skills"] == [] and data["soft_skills"] == []:
            continue

        enriched = {**offer, **data}
        results.append(enriched)

        status_box.write(
            f"Processing offer {i + len(st.session_state.all_offers) + 1}/{max_num_of_offers}..."
        )
        bar.progress((i + len(st.session_state.all_offers) + 1) / max_num_of_offers)

    return results


st.title("Job Collection")

metier = st.text_input(
    "Job title or skill:",
    placeholder="e.g., Data Scientist, Python, Marketing...",
)
pays = st.text_input(
    "Location:",
    placeholder="France, Germany, Spain...",
)
contrat_type = st.selectbox(
    "Contract type (optional):",
    options=[
        "",
        "CDI",
        "CDD",
        "Intérim",
        "Stage",
        "Alternance",
        "Freelance",
    ],
)
max_num_of_offers = st.number_input(
    "Maximum number of job offers to fetch:",
    step=1,
    min_value=1,
    max_value=1000,
)

if st.button("Start search"):
    st.session_state.all_offers = []
    time_start = time.time()

    # Build search URL
    search_url = build_search_url(metier, pays, contrat_type)

    # Loop variables
    last_page_global = None

    progress_box = st.empty()
    status_box = st.empty()

    # Loop through HelloWork pages until the end
    pages_processed = 0

    for page in range(1, MAX_PAGE_HARDCAP + 1):
        paginated_url = f"{search_url}&p={page}"

        try:
            result_html = fetch_html(paginated_url)
            if not result_html["ok"]:
                st.warning(
                    f"Page {page} could not be retrieved (status={result_html['status_code']}). Stopping."
                )
                st.json({k: v for k, v in result_html.items() if k != "html"})
                break

            offers, detected_last_page = extraction_offers_from_html(result_html["html"])
            pages_processed += 1

            if last_page_global is None:
                last_page_global = detected_last_page

            if not offers:
                st.warning(f"No offers found.")
                break

            remaining = max_num_of_offers - len(st.session_state.all_offers)
            if remaining <= 0:
                st.success(
                    f"Maximum number of offers reached ({max_num_of_offers})."
                )
                break

            to_take = min(len(offers), remaining)
            batch_size = min(100, to_take)

            with httpx.Client(
                timeout=20,
                follow_redirects=True,
                headers=DEFAULT_HEADERS,
            ) as client:
                for i in range(0, to_take, batch_size):
                    batch_offers = offers[i : i + batch_size]
                    with progress_box.container():
                        st.write("Processing…")
                        bar = st.progress(0)
                        enriched_offers = enrich_offers(
                            client,
                            batch_offers,
                            max_num_of_offers,
                            status_box,
                            bar,
                        )

                    st.session_state.all_offers.extend(enriched_offers)
                    time.sleep(1)

            if page >= last_page_global:
                st.success(
                    f"Last page reached ({last_page_global}). Scraping finished."
                )
                break

        except Exception as e:
            st.error(f"Error while scraping page {page}: {e}")
            break
    else:
        st.warning(f"Safety hard cap reached ({MAX_PAGE_HARDCAP} pages).")

    time_end = time.time()
    st.write(f"Scraping finished in {time_end - time_start:.2f} seconds.")

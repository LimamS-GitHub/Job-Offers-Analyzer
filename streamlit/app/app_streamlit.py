import asyncio
from datetime import date,timedelta
import os
from pyexpat import model
from time import time
import re
from typing import List, Dict, Tuple, Optional
import time as time_module
import json
import google.generativeai as genai
from dotenv import load_dotenv
import httpx
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl
from urllib.parse import urljoin, urlencode, quote_plus

# --------------------
# Constantes
# --------------------
BASE_URL = "https://www.hellowork.com"
SEARCH_PATH = "/fr-fr/emploi/recherche.html"
load_dotenv()
api_key = os.getenv("GENAI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY manquante (variable d'environnement).")
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}
MAX_PAGE_HARDCAP = 100
genai.configure(api_key=api_key)
MODEL = genai.GenerativeModel("gemini-2.5-flash-lite")

# --------------------
# Modèles & helpers
# --------------------
def get_public_ip() -> str:
    """Retourne l'IP publique (debug réseau)."""
    r = requests.get("https://api.ipify.org?format=json", timeout=10)
    r.raise_for_status()
    return r.json()["ip"]

def prompt_gemini(job_offer: str) -> str:
    return f"""
        Tu es un extracteur d'informations d'offres d'emploi.
        Retourne UNIQUEMENT un JSON valide (sans texte, sans ```json).

        Règles :
        - N'invente rien.
        - Si absent → null ou [].
        - Déduplique et normalise les termes.

        Champs à extraire :

        1) hard_skills :
        - Compétences techniques explicitement mentionnées.

        2) soft_skills :
        - Compétences comportementales explicitement mentionnées.

        3) Years of experience :
        - Nombre d’années d’expérience explicitement mentionné (ex: "3 ans").
        - Sinon → null.

        4) Experience domain preference :
        - Domaines explicitement mentionnés dans l’offre (Banque, Santé, Finance, E-commerce, Industrie, Assurance…).
        - Sinon → [].

        Format JSON obligatoire :
        {{
        "hard_skills": [],
        "soft_skills": [],
        "Years of experience": null,
        "Experience domain preference": []
        }}

        Texte de l'offre :
        \"\"\"
        {job_offer}
        \"\"\"
        """

def build_search_url(job: str, country: str, contract_type: str = "") -> str:
    """
    Construit l'URL de recherche HelloWork (en encodant les paramètres).
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
    Extrait le texte d'un élément HTML, nettoyé.
    Retourne None si non trouvé.
    """
    attrs = attrs or {}
    elem = parent.find(name, class_=class_name, attrs=attrs)
    return elem.get_text(strip=True) if elem else None

def return_date(date_string):
    jours = re.findall(r'\d+', date_string)
    return date.today() - timedelta(days=int(jours[0])) if jours else date.today()

# --------------------
# Extracteur d'informations HelloWork
# --------------------
def parse_last_page(soup: BeautifulSoup) -> int:
    """
    Récupère le numéro de la dernière page de la pagination.
    Retourne 1 par défaut si rien n'est trouvé.
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
    Extrait la liste des offres + le nombre total de pages depuis une page HTML HelloWork.
    """
    soup = BeautifulSoup(html, "html.parser")
    offers: List[Dict[str, Optional[str]]] = []

    # Nombre total de pages
    last_page = parse_last_page(soup)

    # Liste des offres
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
        date = return_date( extract_text(
            li,
            "div",
            "tw-typo-s tw-text-grey-500 tw-pl-1 tw-pt-1",
        ))

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
                "date": date,
                "url": url,
                "contract_type": contract_type,
                "location": location,
                "company": company,
            }
        )

    return offers, last_page

# --------------------
# HTTP
# --------------------
async def fetch_html(url: str) -> Dict:
    """
    Télécharge une page HTML (async).
    """
    async with httpx.AsyncClient(
        timeout=20,
        follow_redirects=True,
        headers=DEFAULT_HEADERS,
    ) as client:
        r = await client.get(url)
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

def fetch_html_sync(url: str) -> Dict:
    """Wrapper sync pour Streamlit."""
    return asyncio.run(fetch_html(url))

def extract_text_from_job(url: str, client: httpx.Client) -> Dict[str, Optional[str]]:
    try:
        r = client.get(url,timeout=20, headers=DEFAULT_HEADERS)
        if r.status_code != 200 or not r.content:
            return {"mission_text": None, "profil_recherche": None}

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

        # Construire le texte à analyser
        if mission_text and profil_recherche:
            job_offer = f"mission: {mission_text}\nprofil recherché: {profil_recherche}"
        elif mission_text:
            job_offer = f"mission: {mission_text}"
        elif profil_recherche:
            job_offer = f"profil recherché: {profil_recherche}"
        else:
            return {
                "hard_skills": None,
                "soft_skills": None,
                "experience": {"years": None, "domain_preference": None},
            }

        prompt = prompt_gemini(job_offer)

        # Appel Gemini
        result = MODEL.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        # Parser la réponse JSON
        try:
            data = json.loads(result.text)
            return data
        except Exception as e:
            print("Erreur parsing JSON:", e)
            return {}

    except Exception as e:
        print("Erreur extract_text_from_job:", e)
        return {
            "hard_skills": None,
            "soft_skills": None,
            "experience": {"years": None, "domain_preference": None},
        }

def enrich_offer(offer: Dict[str, Optional[str]], client: httpx.Client) -> Dict[str, Optional[str]]:
    url = offer.get("url")
    if not url:
        return offer

    data = extract_text_from_job(url, client)

    return {**offer, **data}

def enrich_offers(offers: List[Dict[str, Optional[str]]]) -> List[Dict[str, Optional[str]]]:
    results = []

    with httpx.Client(
        timeout=20,
        follow_redirects=True,
        headers=DEFAULT_HEADERS,
    ) as client:
        for start, offer in enumerate(offers):
            st.write(f"Enrichissement offre {start + 1}/{len(offers)} : {offer.get('title')}")
            enriched = enrich_offer(offer, client)
            results.append(enriched)

    return results

# --------------------
# Streamlit UI
# --------------------
st.title("Offers Analytics")

metier = st.text_input(
    "Métier ou compétence :",
    placeholder="Ex : Data Scientist, Python, Marketing...",
)
pays = st.text_input(
    "Pays :",
    placeholder="France, Allemagne, Espagne...",
)
contrat_type = st.selectbox(
    "Type de contrat (optionnel) :",
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


if st.button("Lancer le scraping"):
    time_start = time()
    # Construction de l'URL de recherche
    search_url = build_search_url(metier, pays, contrat_type)

    # Initialisation de la barre de progression
    progress_text = "Operation in progress. Please wait."
    my_bar = st.progress(0, text=progress_text)

    # definition des variables de boucle
    page = 1
    last_page_global = None
    all_offers = []

    # On boucle sur les pages de hellowork jusqu'à la fin 
    while True:
        # Sécurité débordement
        if page > MAX_PAGE_HARDCAP:
            st.warning(
                f"Hard cap de sécurité atteint ({MAX_PAGE_HARDCAP} pages). "
                "La pagination a peut-être un problème."
            )
            break
        
        # Construction de l'URL paginée
        paginated_url = f"{search_url}&p={page}"

        try:
            # Téléchargement de la page
            result_html = fetch_html_sync(paginated_url)

            # Vérification du succès de la requête
            if not result_html["ok"]:
                st.warning(
                    f"Page {page} non récupérée correctement "
                    f"(status={result_html['status_code']}). Arrêt."
                )
                st.json({k: v for k, v in result_html.items() if k != "html"})
                break

            # Extraction des offres
            offers, detected_last_page = extraction_offers_from_html(result_html["html"])

            st.write(f"Nombre total de pages détectées : {detected_last_page}")
            datas_from_job = {}
            batch_size = 200
            for i in range(0, len(offers), batch_size):
                batch_offers = offers[i : i + batch_size]
                enriched_offers = enrich_offers(batch_offers)
                all_offers.extend(enriched_offers)
                time_module.sleep(3)

            
            if last_page_global is None:
                last_page_global = detected_last_page

            if not offers:
                st.warning(f"Aucune offre trouvée à la page {page}. Fin du scraping.")
                break
            percent_complete = int((page / last_page_global) * 100)
            my_bar.progress(percent_complete, text=progress_text)
            # Condition d'arrêt normale : on a atteint la dernière page
            if page >= last_page_global:
                st.success(
                    f"Dernière page atteinte ({last_page_global}). "
                    "Scraping terminé."
                )
                break
            
            page += 1

        except Exception as e:
            st.error(f"Erreur lors du scraping de la page {page} : {e}")
            break

    # Affichage des résultats
    if all_offers:
        df = pd.DataFrame(all_offers)
        st.success(f"{len(df)} offres récupérées au total.")
        st.dataframe(df)
        time_end = time()
        st.write(f"Temps total de scraping par page : {(time_end - time_start)/last_page_global:.2f} secondes.")
    else:
        st.warning("Aucune offre n'a été récupérée.")

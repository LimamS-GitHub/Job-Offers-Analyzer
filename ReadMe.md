# Offers Analytics — Scraper API behind VPN (Gluetun + ProtonVPN WireGuard)

This project provides a secure scraping pipeline powered by FastAPI, where all outbound traffic is routed through a VPN tunnel using Gluetun (WireGuard + ProtonVPN).  
A Streamlit application is included to visualize and analyze extracted job offers.

The architecture ensures that no network traffic can bypass the VPN, thanks to Gluetun’s firewall and kill-switch mechanisms.

---

## 🚀 Features

- ✅ FastAPI scraping API to fetch and process web pages  
- ✅ All outbound traffic forced through ProtonVPN (WireGuard)  
- ✅ Kill-switch & firewall protection via Gluetun  
- ✅ Streamlit web app for job offer analysis and visualization  
- ✅ Dockerized architecture for reproducible deployment  
- ✅ Secure handling of environment variables (.env)  
- ✅ AI-based extraction of skills and job information (Google GenAI)

---

## 🏗️ Architecture

### Services

- **gluetun**  
  VPN gateway (WireGuard → ProtonVPN) with firewall and kill-switch.

- **scraper**  
  FastAPI service that performs web scraping.  
  It shares Gluetun’s network stack using:
  ```yaml
  network_mode: service:gluetun

- **streamlit app** - Web interface to analyze and visualize scraped job offers using NLP and AI.

### Network flow

Client → localhost:8001 (Gluetun) → Target Website (via VPN) → FastAPI Scraper

## Project structure
```
.
├── docker-compose.yml         # Orchestrates gluetun, scraper, and streamlit services
├── .env                       # Environment variables (ProtonVPN credentials, API keys)
├── scraper/                   # FastAPI scraping service
│   ├── Dockerfile             # Container image for scraper
│   ├── requirements.txt       # Python dependencies
│   └── app/
│       └── main.py            # FastAPI application entry point
├── streamlit/                 # Data visualization and analysis app
│   ├── app/
│   │   ├── .env               # Environment variables (ProtonVPN credentials, API keys)
│   │   └── app_streamlit.py   # Streamlit UI application
│   ├── Dockerfile             # Container image for streamlit
│   └── requirements.txt       # Python dependencies
└── README.md                  # This file
```


## Quick start
1. Create a Free protonvpn account ([link](https://protonvpn.com/fr/l/vpn-home-free?url_id=397&utm_campaign=ww-all-2c-vpn-gro_aff-g_acq-partners_program&utm_source=aid-tune-1725&utm_medium=link&utm_term=vpn_home_free_landing&utm_content=26&phfp=false)) then get your ProtonVPN/Wireguard credentials. <img src="Proton_vpn.png" alt="Image" style="max-width: 40%; height: auto;">
2. Create an API key on Google Generative AI.
2. Create `.env` and configure your ProtonVPN/Wireguard credentials.

.env example :
```
# Config de base
TZ=Australia/Brisbane

# Config OpenVPN
OPENVPN_USER=****
OPENVPN_PASSWORD=****

# Config WireGuard
WIREGUARD_PRIVATE_KEY=****

# Google API Key gen ai
GENAI_API_KEY=****
```
4. Start the services

Run the following command in your terminal:

```bash
docker compose up -d
```
5. You can run the web app locally on *http://localhost:8501/*

## Video of the result



Notes:
- This project is for educational and research purposes only.
# FastAPI Scraper behind VPN (Gluetun + ProtonVPN Wireguard)

This project runs a FastAPI scraping API whose outgoing traffic is forced through a VPN using qmcgaw/gluetun (OpenVPN → ProtonVPN). The FastAPI container shares the network namespace of the VPN container, preventing any outbound traffic from bypassing the VPN.

## Highlights

- ✅ FastAPI endpoint that fetches a webpage and returns raw HTML  
- ✅ All outbound HTTP requests routed through the VPN tunnel (OpenVPN)  
- ✅ Kill‑switch and firewall behavior enforced by Gluetun to prevent leaks  
- ✅ Single Docker Compose setup for reproducible local deployment

## Architecture

- **gluetun** — VPN gateway (OpenVPN → ProtonVPN) with built‑in firewall / kill‑switch  
- **scraper** — FastAPI service that shares gluetun’s network stack via `network_mode: service:gluetun`

### Network flow

Client → `localhost:8001` (published by gluetun) → FastAPI (scraper) → outbound HTTP via VPN tunnel

## Project structure

.
├─ docker-compose.yml  
├─ .env.example  
├─ scraper/  
│  ├─ Dockerfile  
│  ├─ requirements.txt  
│  └─ app/  
│     └─ main.py  
└─ data/  # optional: mounted volume for scraped data or logs

## Quick start
1. Create a Free protonvpn account then get your ProtonVPN/OpenVPN credentials.
2. Copy `.env.example` to `.env` and configure your ProtonVPN/OpenVPN credentials.  
3. Start services:
    docker compose up -d
4. Call the scraper endpoint (example in test_scrap.ipynb)

Notes:
- The scraper container uses `network_mode: service:gluetun`, so it has no separate published ports; external access is exposed via the gluetun service.  
- Ensure you keep container images and the Azure/OS environment up to date for security and reliability.

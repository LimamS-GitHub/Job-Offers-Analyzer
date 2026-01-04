# FastAPI Scraper behind VPN (Gluetun + ProtonVPN Wireguard)

This project runs a FastAPI scraping API whose outgoing traffic is forced through a VPN using qmcgaw/gluetun (Wireguard → ProtonVPN). The FastAPI container shares the network namespace of the VPN container, preventing any outbound traffic from bypassing the VPN.

## Highlights

- ✅ FastAPI endpoint that fetches a webpage and returns raw HTML  
- ✅ All outbound HTTP requests routed through the VPN tunnel (Wireguard)  
- ✅ Kill‑switch and firewall behavior enforced by Gluetun to prevent leaks  
- ✅ Single Docker Compose setup for reproducible local deployment

## Architecture

- **gluetun** — VPN gateway (Wireguard → ProtonVPN) with built‑in firewall / kill‑switch  
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
1. Create a Free protonvpn account then get your ProtonVPN/Wireguard credentials.
2. Create `.env` and configure your ProtonVPN/Wireguard credentials.

.env example :
```
# Config de base
TZ=Australia/Brisbane

# Config OpenVPN
OPENVPN_USER=yTUo8aehLIsdpEJi
OPENVPN_PASSWORD=rCf0TVb5xY138sOqTZ0vWTfxy7ColP7r

# Config WireGuard (clé exemple)
WIREGUARD_PRIVATE_KEY=4HWGAPClLkRcnGSJ1DDFUU7lVg1zT3Wl51K/a92j+2c=
```
4. Start services:
    docker compose up -d
5. Call the scraper endpoint (example in test_scrap.ipynb)

Notes:
- The scraper container uses `network_mode: service:gluetun`, so it has no separate published ports; external access is exposed via the gluetun service.  
- Ensure you keep container images and the Azure/OS environment up to date for security and reliability.

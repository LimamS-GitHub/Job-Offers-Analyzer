
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx

# Define FastAPI app
app = FastAPI(title="Simple Scraper API")

# Define class for request body
class ScrapeRequest(BaseModel):
    url: HttpUrl

# Define the /scrape endpoint
@app.post("/scrape")
async def scrape(req: ScrapeRequest):
    try:
        
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate",
            },
        ) as client:
            r = await client.get(str(req.url))
            content = r.content or b""
            data = {
                "status_code": r.status_code,
                "url": str(r.url),
                "content_length": len(content),
                "content_type": r.headers.get("content-type"),
                "html": content,
            }
            if r.status_code == 200 and content:
                return data
            else:
                raise HTTPException(
                    status_code=r.status_code,
                    detail=f"Failed to fetch content",
                )

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{type(e).__name__}: {e}")
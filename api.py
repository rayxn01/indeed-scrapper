from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import subprocess
import json
import os
import glob

app = FastAPI(title="JobHunt Scraper API")

# ── CORS: lets your browser/frontend call this API ────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # change to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve frontend HTML if it exists in a /static folder ─────────────────────
if os.path.exists("static"):
    app.mount("/ui", StaticFiles(directory="static", html=True), name="static")


# ── Request model ─────────────────────────────────────────────────────────────
class ScrapeRequest(BaseModel):
    keywords: List[str]                      # ["Amazon marketplace", "Ecommerce manager"]
    location: str = "Remote"
    results_per_keyword: int = 25
    marketplaces: List[str] = ["amazon"]     # ["amazon", "shopify", ...]
    strict_filter: bool = True


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
def home():
    return {"message": "JobHunt API is running ✅"}


@app.post("/scrape")
def scrape(req: ScrapeRequest):

    if not req.keywords:
        raise HTTPException(status_code=400, detail="Add at least one keyword.")

    # ── 1. Write runtime config so scraper.py can read it ─────────────────────
    runtime_config = {
        "keywords":            req.keywords,
        "location":            req.location,
        "results_per_keyword": req.results_per_keyword,
        "require_amazon":      "amazon"      in [m.lower() for m in req.marketplaces],
        "require_marketplace": "marketplace" in [m.lower() for m in req.marketplaces],
        "headless":            True,
    }

    with open("runtime_config.json", "w") as f:
        json.dump(runtime_config, f)

    # ── 2. Clean up old results ────────────────────────────────────────────────
    for old in glob.glob("indeed_jobs*.json"):
        os.remove(old)

    # ── 3. Run the scraper ─────────────────────────────────────────────────────
    try:
        result = subprocess.run(
            ["python", "scraper.py"],
            capture_output=True,
            text=True,
            timeout=600,       # 10 minutes max
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Scraper error: {result.stderr[-800:] if result.stderr else 'Unknown'}"
            )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Scraper timed out after 10 minutes.")

    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="scraper.py not found. Run api.py from the same folder.")

    finally:
        # Always clean up the runtime config
        if os.path.exists("runtime_config.json"):
            os.remove("runtime_config.json")

    # ── 4. Find the results file ───────────────────────────────────────────────
    # save_to_json() in save_results.py creates a timestamped file like:
    # indeed_jobs_2024-01-15_10-30-00.json  OR  indeed_jobs.json
    result_files = sorted(glob.glob("indeed_jobs*.json"), key=os.path.getmtime, reverse=True)

    if not result_files:
        raise HTTPException(status_code=404, detail="Scraper ran but saved no results. Check your keywords or filters.")

    with open(result_files[0]) as f:
        raw = json.load(f)

    # ── 5. Normalise to frontend format ───────────────────────────────────────
    # Handles both: a raw list  OR  {"jobs": [...]}
    raw_jobs = raw if isinstance(raw, list) else raw.get("jobs", [])

    jobs = []
    for j in raw_jobs:
        jobs.append({
            "title":       j.get("title", "Unknown Title"),
            "company":     j.get("company", "Unknown Company"),
            "location":    j.get("location", ""),
            "salary":      j.get("salary", "N/A"),
            "category":    j.get("category", "General"),
            "date_posted": j.get("posted_date") or j.get("date_posted", ""),
            "url":         j.get("url", "#"),
        })

    return {
        "jobs":  jobs,
        "total": len(jobs),
    }
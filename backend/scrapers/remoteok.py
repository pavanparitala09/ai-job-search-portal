"""
RemoteOK Scraper
RemoteOK provides a free public JSON API — no key needed.
API: https://remoteok.com/api
"""
import requests
import logging
import time

logger = logging.getLogger(__name__)

REMOTEOK_API = "https://remoteok.com/api"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://remoteok.com",
}

# Map RemoteOK tags to our categories
TAG_CATEGORY_MAP = {
    "python": "Software",
    "javascript": "Software",
    "react": "Web Development",
    "node": "Web Development",
    "java": "Software",
    "golang": "Software",
    "rust": "Software",
    "devops": "DevOps",
    "data": "Data Science",
    "machine-learning": "AI/ML",
    "ai": "AI/ML",
    "design": "Design",
    "marketing": "Marketing",
    "finance": "Finance",
    "backend": "Software",
    "frontend": "Web Development",
    "fullstack": "Web Development",
    "mobile": "Mobile",
    "android": "Mobile",
    "ios": "Mobile",
    "cloud": "DevOps",
    "aws": "DevOps",
}


def scrape_remoteok(max_jobs: int = 60) -> list[dict]:
    """Fetch remote job listings from RemoteOK's public API."""
    try:
        logger.info("Scraping RemoteOK API...")
        time.sleep(1)  # polite delay before request
        import time as t
        from database import log_external_api
        start = t.time()
        resp = requests.get(REMOTEOK_API, headers=HEADERS, timeout=20)
        dur = (t.time() - start) * 1000
        log_external_api("remoteok.com/api", "GET", resp.status_code, dur)

        if resp.status_code != 200:
            logger.warning(f"RemoteOK API returned {resp.status_code}")
            return []

        data = resp.json()
        # First item is metadata/legal note, skip it
        jobs_raw = [item for item in data if isinstance(item, dict) and "slug" in item]
        jobs_raw = jobs_raw[:max_jobs]

        jobs = []
        for item in jobs_raw:
            try:
                job = _parse_remoteok_job(item)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.error(f"Error parsing RemoteOK job: {e}")
                continue

        logger.info(f"RemoteOK: Collected {len(jobs)} jobs")
        return jobs

    except Exception as e:
        logger.error(f"RemoteOK scraping failed: {e}")
        return []


def _parse_remoteok_job(item: dict) -> dict | None:
    """Parse a single RemoteOK API job item."""
    try:
        tags = item.get("tags", []) or []
        category = _map_category(tags)

        # Parse salary
        salary_min_str = item.get("salary_min", "") or ""
        salary_max_str = item.get("salary_max", "") or ""
        try:
            salary_min = float(salary_min_str) if salary_min_str else None
        except ValueError:
            salary_min = None
        try:
            salary_max = float(salary_max_str) if salary_max_str else None
        except ValueError:
            salary_max = None

        # Clean description (strip HTML tags)
        import re
        description = item.get("description", "") or ""
        description = re.sub(r"<[^>]+>", " ", description).strip()
        description = re.sub(r"\s+", " ", description)[:1000]

        slug = item.get("slug", "")
        source_id = f"remoteok_{slug}"
        apply_link = item.get("url", "") or f"https://remoteok.com/remote-jobs/{slug}"

        return {
            "title": item.get("position", "N/A"),
            "company": item.get("company", "N/A"),
            "location": item.get("location", "Remote") or "Remote",
            "job_type": "Remote",
            "category": category,
            "description": description,
            "requirements": "",
            "skills": ", ".join(tags[:10]),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": "USD",
            "experience_required": "",
            "apply_link": apply_link,
            "source": "remoteok",
            "source_id": source_id,
            "logo_url": item.get("company_logo", ""),
            "posted_date": item.get("date", ""),
            "deadline": "",
        }
    except Exception as e:
        logger.error(f"Error parsing RemoteOK item: {e}")
        return None


def _map_category(tags: list[str]) -> str:
    """Map RemoteOK tags to our internal category."""
    for tag in [t.lower() for t in tags]:
        if tag in TAG_CATEGORY_MAP:
            return TAG_CATEGORY_MAP[tag]
        for key, cat in TAG_CATEGORY_MAP.items():
            if key in tag:
                return cat
    return "General"

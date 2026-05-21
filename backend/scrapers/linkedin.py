"""
LinkedIn Guest Job Scraper
Scrapes LinkedIn's public job search — no authentication required.
Uses the guest jobs API endpoint which is publicly accessible.
"""
import requests
from bs4 import BeautifulSoup
import logging
import time
import re
import hashlib

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Guest API for LinkedIn job listings (public endpoint)
LINKEDIN_GUEST_API = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    "?keywords={keywords}&location={location}&start={start}"
)

SEARCH_QUERIES = [
    ("software engineer", "India", "Software"),
    ("python developer", "India", "Software"),
    ("data scientist", "India", "Data Science"),
    ("react developer", "India", "Web Development"),
    ("machine learning", "India", "AI/ML"),
    ("ui ux designer", "India", "Design"),
    ("devops engineer", "India", "DevOps"),
    ("android developer", "India", "Mobile"),
    ("digital marketing", "India", "Marketing"),
    ("business analyst", "India", "Business"),
]


def scrape_linkedin(max_per_query: int = 5) -> list[dict]:
    """Scrape job listings from LinkedIn's guest jobs API."""
    all_jobs = []
    seen_ids = set()

    for keywords, location, category in SEARCH_QUERIES:
        try:
            url = LINKEDIN_GUEST_API.format(
                keywords=keywords.replace(" ", "%20"),
                location=location,
                start=0,
            )
            logger.info(f"Scraping LinkedIn guest API: {keywords}")
            resp = requests.get(url, headers=HEADERS, timeout=15)

            if resp.status_code != 200:
                logger.warning(f"LinkedIn returned {resp.status_code} for {keywords}")
                time.sleep(2)
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select("li")[:max_per_query]

            for card in cards:
                try:
                    job = _parse_linkedin_card(card, category)
                    if job and job["source_id"] not in seen_ids:
                        seen_ids.add(job["source_id"])
                        all_jobs.append(job)
                except Exception as e:
                    logger.error(f"Error parsing LinkedIn card: {e}")
                    continue

            time.sleep(2)  # LinkedIn is strict, longer delay

        except Exception as e:
            logger.error(f"Error scraping LinkedIn [{keywords}]: {e}")
            continue

    logger.info(f"LinkedIn: Collected {len(all_jobs)} jobs")
    return all_jobs


def _parse_linkedin_card(card, category: str) -> dict | None:
    """Parse a single LinkedIn job card."""
    try:
        # Title
        title_el = card.select_one(".base-search-card__title")
        title = title_el.get_text(strip=True) if title_el else None
        if not title:
            return None

        # Company
        company_el = card.select_one(".base-search-card__subtitle")
        company = company_el.get_text(strip=True) if company_el else "N/A"

        # Location
        location_el = card.select_one(".job-search-card__location")
        location = location_el.get_text(strip=True) if location_el else "India"

        # Apply link
        link_el = card.select_one("a.base-card__full-link") or card.select_one("a")
        apply_link = link_el.get("href", "") if link_el else ""
        # Remove tracking params after ?
        apply_link = apply_link.split("?")[0] if apply_link else ""

        # Job ID from URL
        job_id_match = re.search(r"/jobs/view/(\d+)", apply_link)
        job_id = job_id_match.group(1) if job_id_match else hashlib.md5((title + company).encode()).hexdigest()[:12]
        source_id = f"linkedin_{job_id}"

        # Posted date
        date_el = card.select_one("time")
        posted_date = date_el.get("datetime", "") if date_el else ""

        # Job type (listed_at can indicate recent)
        listed_at_el = card.select_one(".job-search-card__listdate") or card.select_one("time")
        listed_text = listed_at_el.get_text(strip=True) if listed_at_el else ""

        # Logo
        logo_el = card.select_one("img.artdeco-entity-image")
        logo_url = logo_el.get("data-delayed-url", "") or logo_el.get("src", "") if logo_el else ""

        return {
            "title": title,
            "company": company,
            "location": location,
            "job_type": _detect_type(title, location),
            "category": category,
            "description": f"{title} position at {company} in {location}.",
            "requirements": "",
            "skills": "",
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "INR",
            "experience_required": "",
            "apply_link": apply_link if apply_link else "https://linkedin.com/jobs",
            "source": "linkedin",
            "source_id": source_id,
            "logo_url": logo_url,
            "posted_date": posted_date,
            "deadline": "",
        }
    except Exception as e:
        logger.error(f"LinkedIn card parse error: {e}")
        return None


def _detect_type(title: str, location: str) -> str:
    title_lower = title.lower()
    if "intern" in title_lower:
        return "Internship"
    loc_lower = location.lower()
    if "remote" in loc_lower or title_lower:
        if "remote" in title_lower:
            return "Remote"
    return "Full-time"

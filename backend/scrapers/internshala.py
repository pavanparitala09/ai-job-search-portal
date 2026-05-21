"""
Internshala Scraper
Scrapes internship and job listings from internshala.com
"""
import requests
from bs4 import BeautifulSoup
import time
import logging
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://internshala.com",
}

CATEGORIES = [
    ("software-development", "Software"),
    ("web-development", "Web Development"),
    ("data-science", "Data Science"),
    ("machine-learning", "AI/ML"),
    ("python", "Software"),
    ("java", "Software"),
    ("marketing", "Marketing"),
    ("content-writing", "Content"),
    ("graphic-design", "Design"),
    ("finance", "Finance"),
]


def scrape_internshala(max_per_category: int = 10) -> list[dict]:
    """Scrape internship listings from Internshala."""
    all_jobs = []
    seen_ids = set()

    for slug, category in CATEGORIES:
        try:
            url = f"https://internshala.com/internships/{slug}-internship/"
            logger.info(f"Scraping Internshala: {url}")
            
            import time
            from database import log_external_api
            start = time.time()
            resp = requests.get(url, headers=HEADERS, timeout=15)
            dur = (time.time() - start) * 1000
            log_external_api("internshala.com", "GET", resp.status_code, dur)
            
            if resp.status_code != 200:
                logger.warning(f"Internshala returned {resp.status_code} for {slug}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select(".individual_internship")[:max_per_category]

            for card in cards:
                try:
                    job = _parse_internshala_card(card, category)
                    if job and job["source_id"] not in seen_ids:
                        seen_ids.add(job["source_id"])
                        all_jobs.append(job)
                except Exception as e:
                    logger.error(f"Error parsing card: {e}")
                    continue

            time.sleep(1.5)  # polite delay

        except Exception as e:
            logger.error(f"Error scraping Internshala [{slug}]: {e}")
            continue

    logger.info(f"Internshala: Collected {len(all_jobs)} jobs")
    return all_jobs


def _parse_internshala_card(card, category: str) -> dict | None:
    """Parse a single Internshala job card."""
    try:
        # Title
        title_el = card.select_one(".job-internship-name a") or card.select_one(".profile a")
        title = title_el.get_text(strip=True) if title_el else "N/A"

        # Company
        company_el = card.select_one(".company_and_premium .company-name") or card.select_one(".company_name")
        company = company_el.get_text(strip=True) if company_el else "N/A"

        # Location
        location_el = card.select_one(".location_link") or card.select_one(".locations a")
        location = location_el.get_text(strip=True) if location_el else "Remote"

        # Stipend
        stipend_el = card.select_one(".stipend") or card.select_one(".stipend_container .stipend")
        stipend_text = stipend_el.get_text(strip=True) if stipend_el else ""
        salary_min, salary_max = _parse_stipend(stipend_text)

        # Duration
        duration_el = card.select_one(".row-1-item span") or card.select_one(".item_body")
        duration = duration_el.get_text(strip=True) if duration_el else ""

        # Apply link
        link_el = card.select_one(".view_detail_button") or card.select_one("a.job-title-href")
        apply_link = ""
        if link_el:
            href = link_el.get("href", "")
            apply_link = f"https://internshala.com{href}" if href.startswith("/") else href

        # Skills
        skills_els = card.select(".round_tabs .round_tab_badge") or card.select(".skills_container .round_tab")
        skills = ", ".join([s.get_text(strip=True) for s in skills_els]) if skills_els else ""

        # Posted date
        posted_el = card.select_one(".status-inactive span") or card.select_one(".posted_by_container")
        posted_date = posted_el.get_text(strip=True) if posted_el else ""

        # Source ID
        card_id = card.get("internshipid") or card.get("id") or ""
        source_id = f"internshala_{card_id}" if card_id else f"internshala_{hashlib.md5((title+company).encode()).hexdigest()}"

        return {
            "title": title,
            "company": company,
            "location": location,
            "job_type": "Internship",
            "category": category,
            "description": f"{title} internship at {company}. Duration: {duration}.",
            "requirements": "",
            "skills": skills,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": "INR",
            "experience_required": "Fresher",
            "apply_link": apply_link,
            "source": "internshala",
            "source_id": source_id,
            "logo_url": "",
            "posted_date": posted_date,
            "deadline": "",
        }
    except Exception as e:
        logger.error(f"Error parsing card: {e}")
        return None


def _parse_stipend(text: str) -> tuple[float | None, float | None]:
    """Parse stipend string like '₹ 5,000 - 10,000 /month' → (5000, 10000)."""
    import re
    text = text.replace(",", "").replace("₹", "").replace("$", "").strip()
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    if len(nums) >= 2:
        return float(nums[0]), float(nums[1])
    elif len(nums) == 1:
        return float(nums[0]), float(nums[0])
    return None, None

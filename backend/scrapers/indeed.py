"""
Indeed India Scraper
Uses Indeed's RSS feed which is public and doesn't require authentication.
RSS feeds are less likely to be blocked vs HTML scraping.
"""
import feedparser
import logging
import time
import re
import hashlib

logger = logging.getLogger(__name__)

INDEED_RSS_QUERIES = [
    ("software developer", "Software"),
    ("python developer", "Software"),
    ("java developer", "Software"),
    ("react developer", "Web Development"),
    ("data scientist", "Data Science"),
    ("machine learning engineer", "AI/ML"),
    ("ui ux designer", "Design"),
    ("digital marketing", "Marketing"),
    ("data analyst", "Data Science"),
    ("devops engineer", "DevOps"),
    ("android developer", "Mobile"),
    ("ios developer", "Mobile"),
    ("business analyst", "Business"),
    ("fresher software", "Software"),
    ("internship it", "Software"),
]

INDEED_BASE_RSS = "https://in.indeed.com/rss?q={query}&l=India&sort=date&fromage=7"


def scrape_indeed(max_per_query: int = 5) -> list[dict]:
    """Scrape job listings from Indeed India via RSS feeds."""
    all_jobs = []
    seen_ids = set()

    for query, category in INDEED_RSS_QUERIES:
        try:
            encoded = query.replace(" ", "+")
            url = INDEED_BASE_RSS.format(query=encoded)
            logger.info(f"Fetching Indeed RSS: {query}")

            feed = feedparser.parse(url)
            entries = feed.entries[:max_per_query]

            for entry in entries:
                try:
                    job = _parse_indeed_entry(entry, category)
                    if job and job["source_id"] not in seen_ids:
                        seen_ids.add(job["source_id"])
                        all_jobs.append(job)
                except Exception as e:
                    logger.error(f"Error parsing Indeed entry: {e}")
                    continue

            time.sleep(1)  # polite delay

        except Exception as e:
            logger.error(f"Error scraping Indeed [{query}]: {e}")
            continue

    logger.info(f"Indeed: Collected {len(all_jobs)} jobs")
    return all_jobs


def _parse_indeed_entry(entry: dict, category: str) -> dict | None:
    """Parse a single Indeed RSS entry."""
    try:
        title = entry.get("title", "N/A")
        link = entry.get("link", "")
        summary = entry.get("summary", "") or ""

        # Clean HTML from summary
        summary_clean = re.sub(r"<[^>]+>", " ", summary)
        summary_clean = re.sub(r"\s+", " ", summary_clean).strip()[:800]

        # Extract company and location from title (Indeed format: "Job Title - Company - Location")
        parts = title.split(" - ")
        job_title = parts[0].strip() if len(parts) >= 1 else title
        company = parts[1].strip() if len(parts) >= 2 else "N/A"
        location = parts[2].strip() if len(parts) >= 3 else "India"

        # Source ID from link
        source_id = f"indeed_{hashlib.md5(link.encode()).hexdigest()[:16]}"

        # Published date
        published = entry.get("published", "") or ""

        # Extract salary if mentioned in summary
        salary_min, salary_max = _extract_salary_from_text(summary_clean)

        # Detect job type
        job_type = _detect_job_type(summary_clean + " " + title)

        return {
            "title": job_title,
            "company": company,
            "location": location,
            "job_type": job_type,
            "category": category,
            "description": summary_clean,
            "requirements": "",
            "skills": _extract_skills(summary_clean),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": "INR",
            "experience_required": _extract_experience(summary_clean),
            "apply_link": link,
            "source": "indeed",
            "source_id": source_id,
            "logo_url": "",
            "posted_date": published,
            "deadline": "",
        }
    except Exception as e:
        logger.error(f"Error parsing Indeed entry: {e}")
        return None


def _extract_salary_from_text(text: str) -> tuple:
    """Extract salary range from job description text."""
    # Match patterns like "₹5,00,000 - ₹8,00,000" or "5 LPA - 8 LPA"
    pattern = r"(?:₹|INR|Rs\.?)\s?(\d[\d,]*)\s?(?:to|-)\s?(?:₹|INR|Rs\.?)?\s?(\d[\d,]*)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        try:
            lo = float(match.group(1).replace(",", ""))
            hi = float(match.group(2).replace(",", ""))
            return lo, hi
        except Exception:
            pass

    lpa_pattern = r"(\d+(?:\.\d+)?)\s?(?:to|-)\s?(\d+(?:\.\d+)?)\s?LPA"
    match2 = re.search(lpa_pattern, text, re.IGNORECASE)
    if match2:
        try:
            lo = float(match2.group(1)) * 100000
            hi = float(match2.group(2)) * 100000
            return lo, hi
        except Exception:
            pass

    return None, None


def _extract_experience(text: str) -> str:
    """Extract experience requirement."""
    match = re.search(r"(\d+)\+?\s?(?:to\s?\d+)?\s?years?", text, re.IGNORECASE)
    if match:
        return f"{match.group(1)}+ years"
    if re.search(r"fresher|entry.level|0.year|no.exp", text, re.IGNORECASE):
        return "Fresher"
    return ""


def _detect_job_type(text: str) -> str:
    text_lower = text.lower()
    if "internship" in text_lower:
        return "Internship"
    if "remote" in text_lower or "work from home" in text_lower:
        return "Remote"
    if "part.time" in text_lower or "part time" in text_lower:
        return "Part-time"
    return "Full-time"


COMMON_SKILLS = [
    "Python", "Java", "JavaScript", "React", "Node.js", "SQL", "MySQL",
    "PostgreSQL", "MongoDB", "AWS", "Docker", "Kubernetes", "Git",
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch",
    "Data Analysis", "Excel", "Power BI", "Tableau", "Figma",
    "HTML", "CSS", "TypeScript", "Django", "Flask", "FastAPI",
    "Spring Boot", "REST API", "Agile", "Scrum", "Linux", "C++", "C#"
]


def _extract_skills(text: str) -> str:
    """Find mentioned skills in text."""
    found = []
    for skill in COMMON_SKILLS:
        if skill.lower() in text.lower():
            found.append(skill)
    return ", ".join(found[:8])

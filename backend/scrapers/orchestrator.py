"""
Master scraper orchestrator.
Runs all scrapers and persists jobs to the database.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from scrapers.internshala import scrape_internshala
from scrapers.remoteok import scrape_remoteok
from scrapers.indeed import scrape_indeed
from scrapers.linkedin import scrape_linkedin
from models import Job, ScrapeLog
from database import SessionLocal

logger = logging.getLogger(__name__)


def _save_jobs(db: Session, jobs: list[dict], source: str) -> tuple[int, int]:
    """
    Save jobs to DB. Skip duplicates by source_id.
    Returns (total_scraped, new_added).
    """
    new_added = 0
    for job_data in jobs:
        try:
            source_id = job_data.get("source_id")
            if not source_id:
                continue
            existing = db.query(Job).filter(Job.source_id == source_id).first()
            if existing:
                continue  # Skip duplicate

            job = Job(**job_data)
            db.add(job)
            new_added += 1
        except Exception as e:
            logger.error(f"Error saving job [{source_id}]: {e}")
            db.rollback()
            continue

    try:
        db.commit()
    except Exception as e:
        logger.error(f"Commit error: {e}")
        db.rollback()

    return len(jobs), new_added


def _log_scrape(db: Session, source: str, status: str, scraped: int, added: int, error: str = None):
    log = ScrapeLog(
        source=source,
        status=status,
        jobs_scraped=scraped,
        jobs_added=added,
        error_message=error,
        finished_at=datetime.utcnow(),
    )
    db.add(log)
    try:
        db.commit()
    except Exception:
        db.rollback()


def run_all_scrapers(sources: list[str] = None):
    """
    Run all enabled scrapers and persist jobs to database.
    sources: list of source names to run, or None for all.
    """
    all_sources = {
        "remoteok": _run_remoteok,
        "indeed": _run_indeed,
        "internshala": _run_internshala,
        "linkedin": _run_linkedin,
    }

    if sources:
        to_run = {k: v for k, v in all_sources.items() if k in sources}
    else:
        to_run = all_sources

    db = SessionLocal()
    try:
        total_new = 0
        for source_name, runner in to_run.items():
            added = runner(db)
            total_new += added
            logger.info(f"Scraper [{source_name}] added {added} new jobs")
        logger.info(f"All scrapers done. Total new jobs: {total_new}")
        return total_new
    finally:
        db.close()


def _run_remoteok(db: Session) -> int:
    source = "remoteok"
    try:
        jobs = scrape_remoteok(max_jobs=50)
        scraped, added = _save_jobs(db, jobs, source)
        _log_scrape(db, source, "success", scraped, added)
        return added
    except Exception as e:
        logger.error(f"RemoteOK scraper error: {e}")
        _log_scrape(db, source, "failed", 0, 0, str(e))
        return 0


def _run_indeed(db: Session) -> int:
    source = "indeed"
    try:
        jobs = scrape_indeed(max_per_query=5)
        scraped, added = _save_jobs(db, jobs, source)
        _log_scrape(db, source, "success", scraped, added)
        return added
    except Exception as e:
        logger.error(f"Indeed scraper error: {e}")
        _log_scrape(db, source, "failed", 0, 0, str(e))
        return 0


def _run_internshala(db: Session) -> int:
    source = "internshala"
    try:
        jobs = scrape_internshala(max_per_category=8)
        scraped, added = _save_jobs(db, jobs, source)
        _log_scrape(db, source, "success", scraped, added)
        return added
    except Exception as e:
        logger.error(f"Internshala scraper error: {e}")
        _log_scrape(db, source, "failed", 0, 0, str(e))
        return 0


def _run_linkedin(db: Session) -> int:
    source = "linkedin"
    try:
        jobs = scrape_linkedin(max_per_query=5)
        scraped, added = _save_jobs(db, jobs, source)
        _log_scrape(db, source, "success", scraped, added)
        return added
    except Exception as e:
        logger.error(f"LinkedIn scraper error: {e}")
        _log_scrape(db, source, "failed", 0, 0, str(e))
        return 0

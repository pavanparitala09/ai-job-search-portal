"""
APScheduler configuration for daily automatic job scraping.
Schedule: Every day at midnight (00:00).
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="Asia/Kolkata")


def _scrape_job():
    """The scheduled task that runs all scrapers."""
    logger.info("⏰ Scheduled scrape started...")
    try:
        from scrapers.orchestrator import run_all_scrapers
        added = run_all_scrapers()
        logger.info(f"✅ Scheduled scrape complete. Added {added} new jobs.")
    except Exception as e:
        logger.error(f"❌ Scheduled scrape failed: {e}")


def _on_job_executed(event):
    logger.info(f"Job {event.job_id} executed successfully.")


def _on_job_error(event):
    logger.error(f"Job {event.job_id} raised an exception: {event.exception}")


def start_scheduler():
    """Start the APScheduler with daily scraping at midnight IST."""
    if scheduler.running:
        logger.info("Scheduler already running.")
        return

    scheduler.add_listener(_on_job_executed, EVENT_JOB_EXECUTED)
    scheduler.add_listener(_on_job_error, EVENT_JOB_ERROR)

    # Daily at midnight IST
    scheduler.add_job(
        _scrape_job,
        trigger=CronTrigger(hour=0, minute=0),
        id="daily_scrape",
        name="Daily Job Scraper",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    scheduler.start()
    logger.info("✅ Scheduler started — daily scrape at 00:00 IST")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


def get_scheduler_status() -> dict:
    """Get current scheduler info for the API."""
    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": next_run.isoformat() if next_run else None,
        })
    return {
        "running": scheduler.running,
        "jobs": jobs,
    }

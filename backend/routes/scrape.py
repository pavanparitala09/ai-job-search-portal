from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from scrapers.orchestrator import run_all_scrapers
from scheduler import get_scheduler_status
from database import SessionLocal
from models import ScrapeLog
from schemas import ScrapeLogResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class ScrapeRequest(BaseModel):
    sources: Optional[List[str]] = None  # None = all


class ScrapeResponse(BaseModel):
    message: str
    task_id: Optional[str] = None


@router.post("/trigger", response_model=ScrapeResponse)
def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Manually trigger a scrape. Runs in background."""
    def _run():
        added = run_all_scrapers(sources=request.sources)
        logger.info(f"Manual scrape complete. Added {added} jobs.")

    background_tasks.add_task(_run)
    return ScrapeResponse(message="Scraping started in background. Check /scrape/logs for status.")


@router.get("/status")
def get_scrape_status():
    """Get scheduler status and next run time."""
    return get_scheduler_status()


@router.get("/logs", response_model=List[ScrapeLogResponse])
def get_scrape_logs(limit: int = 20):
    """Get recent scrape logs."""
    db = SessionLocal()
    try:
        logs = (
            db.query(ScrapeLog)
            .order_by(ScrapeLog.started_at.desc())
            .limit(limit)
            .all()
        )
        return logs
    finally:
        db.close()

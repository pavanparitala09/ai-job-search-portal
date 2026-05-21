from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional
from database import get_db
from models import Job
from schemas import JobResponse, JobListResponse

router = APIRouter()


@router.get("", response_model=JobListResponse)
def get_jobs(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search in title, company, skills"),
    category: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    salary_min: Optional[float] = Query(None),
    salary_max: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get all jobs with optional search and filters."""
    query = db.query(Job).filter(Job.is_active == True)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Job.title.ilike(search_pattern),
                Job.company.ilike(search_pattern),
                Job.skills.ilike(search_pattern),
                Job.description.ilike(search_pattern),
                Job.location.ilike(search_pattern),
            )
        )

    if category and category.lower() != "all":
        query = query.filter(Job.category.ilike(f"%{category}%"))

    if job_type and job_type.lower() != "all":
        query = query.filter(Job.job_type.ilike(f"%{job_type}%"))

    if location and location.lower() not in ("all", ""):
        query = query.filter(Job.location.ilike(f"%{location}%"))

    if source and source.lower() != "all":
        query = query.filter(Job.source == source.lower())

    if salary_min is not None:
        query = query.filter(or_(Job.salary_min >= salary_min, Job.salary_min == None))

    if salary_max is not None:
        query = query.filter(or_(Job.salary_max <= salary_max, Job.salary_max == None))

    total = query.count()
    offset = (page - 1) * page_size
    jobs = query.order_by(Job.scraped_at.desc()).offset(offset).limit(page_size).all()

    return JobListResponse(total=total, page=page, page_size=page_size, jobs=jobs)


@router.get("/stats")
def get_job_stats(db: Session = Depends(get_db)):
    """Quick stats for the hero section."""
    total = db.query(Job).filter(Job.is_active == True).count()
    from sqlalchemy import func
    companies = db.query(func.count(Job.company.distinct())).scalar()
    sources = db.query(Job.source).distinct().count()
    return {
        "total_jobs": total,
        "total_companies": companies,
        "total_sources": sources,
    }


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get a single job by ID."""
    job = db.query(Job).filter(Job.id == job_id, Job.is_active == True).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

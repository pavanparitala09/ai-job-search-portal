from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import get_db
from models import Job, ScrapeLog
import collections

router = APIRouter()


@router.get("")
def get_analytics(db: Session = Depends(get_db)):
    """Return market analytics: categories, sources, skills, locations, salary."""

    jobs = db.query(Job).filter(Job.is_active == True).all()
    total_jobs = len(jobs)

    if total_jobs == 0:
        return {
            "total_jobs": 0,
            "jobs_by_category": {},
            "jobs_by_source": {},
            "jobs_by_type": {},
            "top_skills": [],
            "top_locations": [],
            "avg_salary_by_category": {},
            "recent_scrape_logs": [],
            "salary_distribution": [],
        }

    # Jobs by category
    category_counter = collections.Counter(j.category or "Other" for j in jobs)
    jobs_by_category = dict(category_counter.most_common(10))

    # Jobs by source
    source_counter = collections.Counter(j.source or "unknown" for j in jobs)
    jobs_by_source = dict(source_counter.most_common())

    # Jobs by type
    type_counter = collections.Counter(j.job_type or "Not specified" for j in jobs)
    jobs_by_type = dict(type_counter.most_common())

    # Top skills
    skill_counter = collections.Counter()
    for job in jobs:
        if job.skills:
            for skill in job.skills.split(","):
                s = skill.strip()
                if s:
                    skill_counter[s] += 1
    top_skills = [{"skill": k, "count": v} for k, v in skill_counter.most_common(20)]

    # Top locations
    location_counter = collections.Counter()
    for job in jobs:
        if job.location:
            locs = [l.strip() for l in job.location.replace(";", ",").split(",")]
            for loc in locs:
                if loc and loc.lower() not in ("remote", "n/a", ""):
                    location_counter[loc] += 1
    top_locations = [{"location": k, "count": v} for k, v in location_counter.most_common(10)]

    # Avg salary by category (where available)
    salary_data = collections.defaultdict(list)
    for job in jobs:
        if job.salary_min and job.salary_max and job.category:
            avg = (job.salary_min + job.salary_max) / 2
            salary_data[job.category].append(avg)

    avg_salary_by_category = {
        cat: round(sum(vals) / len(vals), 0)
        for cat, vals in salary_data.items()
        if vals
    }

    # Salary distribution buckets
    all_salaries = [
        (j.salary_min + j.salary_max) / 2
        for j in jobs
        if j.salary_min and j.salary_max
    ]
    buckets = {
        "0-3 LPA": 0, "3-6 LPA": 0, "6-10 LPA": 0,
        "10-20 LPA": 0, "20+ LPA": 0
    }
    for s in all_salaries:
        lpa = s / 100000
        if lpa < 3:
            buckets["0-3 LPA"] += 1
        elif lpa < 6:
            buckets["3-6 LPA"] += 1
        elif lpa < 10:
            buckets["6-10 LPA"] += 1
        elif lpa < 20:
            buckets["10-20 LPA"] += 1
        else:
            buckets["20+ LPA"] += 1
    salary_distribution = [{"range": k, "count": v} for k, v in buckets.items()]

    # Recent scrape logs
    logs = (
        db.query(ScrapeLog)
        .order_by(ScrapeLog.started_at.desc())
        .limit(10)
        .all()
    )
    recent_logs = [
        {
            "source": l.source,
            "status": l.status,
            "jobs_scraped": l.jobs_scraped,
            "jobs_added": l.jobs_added,
            "started_at": l.started_at.isoformat() if l.started_at else None,
        }
        for l in logs
    ]

    return {
        "total_jobs": total_jobs,
        "jobs_by_category": jobs_by_category,
        "jobs_by_source": jobs_by_source,
        "jobs_by_type": jobs_by_type,
        "top_skills": top_skills,
        "top_locations": top_locations,
        "avg_salary_by_category": avg_salary_by_category,
        "salary_distribution": salary_distribution,
        "recent_scrape_logs": recent_logs,
    }

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class JobBase(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    job_type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    skills: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = "INR"
    experience_required: Optional[str] = None
    apply_link: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[str] = None
    logo_url: Optional[str] = None
    posted_date: Optional[str] = None
    deadline: Optional[str] = None


class JobCreate(JobBase):
    pass


class JobResponse(JobBase):
    id: int
    is_active: bool
    scraped_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    jobs: List[JobResponse]


class ResumeMatchRequest(BaseModel):
    resume_text: str
    job_id: Optional[int] = None


class ResumeMatchResponse(BaseModel):
    job_id: int
    job_title: str
    company: str
    match_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    suggestions: List[str]


class ScrapeLogResponse(BaseModel):
    id: int
    source: str
    status: str
    jobs_scraped: int
    jobs_added: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AnalyticsResponse(BaseModel):
    total_jobs: int
    jobs_by_category: dict
    jobs_by_source: dict
    jobs_by_type: dict
    top_skills: List[dict]
    top_locations: List[dict]
    avg_salary_by_category: dict
    recent_scrape_logs: List[ScrapeLogResponse]

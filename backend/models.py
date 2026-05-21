from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.sql import func
from database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=True)
    job_type = Column(String(100), nullable=True)          # Full-time, Part-time, Internship, Remote
    category = Column(String(100), nullable=True, index=True)  # Software, Data, Design, etc.
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)                   # comma-separated skills
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String(20), default="INR")
    experience_required = Column(String(100), nullable=True)
    apply_link = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)            # internshala / remoteok / indeed / linkedin
    source_id = Column(String(255), nullable=True, unique=True)
    logo_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    posted_date = Column(String(100), nullable=True)
    deadline = Column(String(100), nullable=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)       # success / failed
    jobs_scraped = Column(Integer, default=0)
    jobs_added = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)


class APILog(Base):
    __tablename__ = "api_logs"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(255), index=True)
    method = Column(String(10))
    status_code = Column(Integer)
    ip_address = Column(String(50))
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    duration_ms = Column(Float, default=0.0)


class VisitorLog(Base):
    __tablename__ = "visitor_logs"

    id = Column(Integer, primary_key=True, index=True)
    ip_hash = Column(String(255), unique=True, index=True)
    user_agent = Column(Text, nullable=True)
    first_visit = Column(DateTime(timezone=True), server_default=func.now())
    last_visit = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    visit_count = Column(Integer, default=1)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True, index=True)
    value = Column(String(255), nullable=False)

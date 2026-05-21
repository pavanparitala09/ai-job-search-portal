import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from sqlalchemy import func
from typing import List, Dict, Any

from database import SessionLocal
from models import Admin, APILog, VisitorLog, ScrapeLog
from scheduler import scheduler

# Replace this in production with environment variable
SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-admin-key-job-portal")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class ScheduleRequest(BaseModel):
    hour: int
    minute: int
    interval_days: int = 1  # 1 to 30

class SettingsRequest(BaseModel):
    resume_analyzer_limit: int

# ── Dependencies ──────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    admin = db.query(Admin).filter(Admin.username == username).first()
    if admin is None:
        raise credentials_exception
    return admin


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ── Routes ────────────────────────────────────────────────────────────────────
from fastapi.security import OAuth2PasswordRequestForm

@router.post("/login", response_model=Token)
def login_for_access_token(req: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == req.username).first()
    if not admin or not verify_password(req.password, admin.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": admin.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/change-password")
def change_password(req: ChangePasswordRequest, current_admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    if not verify_password(req.current_password, current_admin.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    current_admin.password_hash = get_password_hash(req.new_password)
    db.commit()
    return {"message": "Password updated successfully"}


@router.get("/analytics")
def get_admin_analytics(db: Session = Depends(get_current_admin)):
    """Return API calls and unique visitors aggregated by timeframes."""
    db_session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Determine start of week (Monday)
        days_to_subtract = today.weekday()
        this_week = today - timedelta(days=days_to_subtract)
        
        this_month = today.replace(day=1)
        this_year = today.replace(month=1, day=1)
        
        def get_api_count(start_date, category=None):
            query = db_session.query(func.count(APILog.id)).filter(APILog.timestamp >= start_date)
            if category == 'gemini':
                query = query.filter(APILog.endpoint.like('%gemini%'))
            elif category == 'scrapers':
                query = query.filter(~APILog.endpoint.like('%gemini%'))
            return query.scalar() or 0
            
        def get_visitor_count(start_date):
            return db_session.query(func.count(VisitorLog.id)).filter(VisitorLog.last_visit >= start_date).scalar() or 0

        def get_stats_for(category):
            return {
                "today": get_api_count(today, category),
                "week": get_api_count(this_week, category),
                "month": get_api_count(this_month, category),
                "total": db_session.query(func.count(APILog.id)).filter(
                    APILog.endpoint.like('%gemini%') if category == 'gemini' else ~APILog.endpoint.like('%gemini%') if category == 'scrapers' else True
                ).scalar() or 0,
            }

        api_stats = {
            "gemini": get_stats_for('gemini'),
            "scrapers": get_stats_for('scrapers'),
            "total": get_stats_for(None)
        }
        
        visitor_stats = {
            "today": get_visitor_count(today),
            "week": get_visitor_count(this_week),
            "month": get_visitor_count(this_month),
            "total": db_session.query(func.count(VisitorLog.id)).scalar() or 0,
        }
        
        return {
            "api_calls": api_stats,
            "visitors": visitor_stats
        }
    finally:
        db_session.close()

from models import SystemSetting

@router.get("/settings")
def get_settings(db: Session = Depends(get_current_admin)):
    db_session = SessionLocal()
    try:
        setting = db_session.query(SystemSetting).filter(SystemSetting.key == "resume_analyzer_limit").first()
        limit = int(setting.value) if setting else 100 # default
        return {"resume_analyzer_limit": limit}
    finally:
        db_session.close()

@router.post("/settings")
def update_settings(req: SettingsRequest, db: Session = Depends(get_current_admin)):
    db_session = SessionLocal()
    try:
        setting = db_session.query(SystemSetting).filter(SystemSetting.key == "resume_analyzer_limit").first()
        if not setting:
            setting = SystemSetting(key="resume_analyzer_limit", value=str(req.resume_analyzer_limit))
            db_session.add(setting)
        else:
            setting.value = str(req.resume_analyzer_limit)
        db_session.commit()
        return {"message": "Settings updated"}
    finally:
        db_session.close()


@router.post("/scrape")
def trigger_manual_scrape(background_tasks: BackgroundTasks, current_admin: Admin = Depends(get_current_admin)):
    """Trigger the scraper to run immediately in the background."""
    from scrapers.orchestrator import run_all_scrapers
    
    def scrape_job():
        try:
            run_all_scrapers()
        except Exception as e:
            print(f"Manual scrape error: {e}")
            
    background_tasks.add_task(scrape_job)
    return {"message": "Scraping started in the background."}


@router.get("/scrape-status")
def get_scrape_status(db: Session = Depends(get_current_admin)):
    """Get the most recent scrape logs to show progress/status."""
    db_session = SessionLocal()
    try:
        logs = db_session.query(ScrapeLog).order_by(ScrapeLog.id.desc()).limit(10).all()
        return [{"source": l.source, "status": l.status, "jobs_added": l.jobs_added, "started_at": l.started_at, "finished_at": l.finished_at} for l in logs]
    finally:
        db_session.close()


@router.get("/scrape-stream")
async def scrape_stream(token: str = None):
    """Real-time SSE stream for scraping progress."""
    from fastapi.responses import StreamingResponse
    import asyncio
    
    # We do a basic token check since EventSource doesn't send headers easily
    db_session = SessionLocal()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("sub"): raise Exception()
    except Exception:
        raise HTTPException(status_code=401)
    finally:
        db_session.close()

    async def event_generator():
        # Stream recent logs every 2 seconds
        db = SessionLocal()
        last_id = 0
        try:
            while True:
                # Get the most recent scrape session
                logs = db.query(ScrapeLog).filter(ScrapeLog.id > last_id).order_by(ScrapeLog.id.asc()).all()
                for l in logs:
                    last_id = l.id
                    yield f"data: {{\"source\": \"{l.source}\", \"status\": \"{l.status}\", \"jobs_added\": {l.jobs_added}}}\n\n"
                await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            pass
        finally:
            db.close()
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/schedule")
def update_schedule(req: ScheduleRequest, current_admin: Admin = Depends(get_current_admin)):
    """Update the APScheduler scrape time."""
    if not (0 <= req.hour <= 23 and 0 <= req.minute <= 59):
        raise HTTPException(status_code=400, detail="Invalid hour or minute")
    if not (1 <= req.interval_days <= 30):
        raise HTTPException(status_code=400, detail="Interval must be between 1 and 30 days")
        
    job_id = "daily_scrape"
    job = scheduler.get_job(job_id)
    if job:
        from apscheduler.triggers.cron import CronTrigger
        # day="*/N" means every Nth day of the month
        trigger = CronTrigger(hour=req.hour, minute=req.minute, day=f"*/{req.interval_days}" if req.interval_days > 1 else "*")
            
        job.modify(trigger=trigger)
        return {"message": f"Scrape schedule updated to run every {req.interval_days} day(s) at {req.hour:02d}:{req.minute:02d}"}
    else:
        raise HTTPException(status_code=404, detail="Scheduled job not found")


@router.get("/schedule")
def get_schedule(current_admin: Admin = Depends(get_current_admin)):
    job_id = "daily_scrape"
    job = scheduler.get_job(job_id)
    if job and hasattr(job.trigger, 'fields'):
        fields = job.trigger.fields
        day_field = str(fields[2])
        hour = str(fields[5])
        minute = str(fields[6])
        
        interval = 1
        if day_field.startswith("*/"):
            interval = int(day_field.split("*/")[1])
            
        return {"hour": hour, "minute": minute, "interval_days": interval}
    return {"hour": "0", "minute": "0", "interval_days": 1}

"""
FastAPI Main Application
AI-Powered Job Aggregator Platform
"""
import logging
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import time
import hashlib
from fastapi import Request
from routes import jobs, resume, analytics, scrape, admin
from scheduler import start_scheduler
from models import Admin, APILog, VisitorLog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Create all DB tables on startup
Base.metadata.create_all(bind=engine)


def _init_default_admin():
    from database import SessionLocal
    from routes.admin import get_password_hash
    db = SessionLocal()
    try:
        if not db.query(Admin).filter(Admin.username == "admin").first():
            new_admin = Admin(username="admin", password_hash=get_password_hash("admin123"))
            db.add(new_admin)
            db.commit()
            logger.info("Created default admin (admin / admin123)")
    finally:
        db.close()

def _initial_scrape():
    """Run the first scrape in a background thread so startup is non-blocking."""
    from scrapers.orchestrator import run_all_scrapers
    from database import SessionLocal
    db = SessionLocal()
    try:
        total = db.query(__import__("models").Job).count()
        db.close()
    except Exception:
        total = 0

    if total == 0:
        logger.info("Database is empty — running initial scrape...")
        run_all_scrapers()
    else:
        logger.info(f"Database already has {total} jobs — skipping initial scrape.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Job Portal API...")
    _init_default_admin()
    start_scheduler()
    thread = threading.Thread(target=_initial_scrape, daemon=True)
    thread.start()
    yield
    # Shutdown
    from scheduler import stop_scheduler
    stop_scheduler()
    logger.info("🛑 Job Portal API shut down.")


app = FastAPI(
    title="AI Job Portal API",
    description="Real-time job aggregator with AI resume matching and market analytics.",
    version="1.0.0",
    lifespan=lifespan,
)

@app.middleware("http")
async def track_analytics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)

    # Only log Visitors for typical GET/navigation requests
    if request.method != "OPTIONS":
        from database import SessionLocal
        db = SessionLocal()
        try:
            # VisitorLog
            ip_address = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")
            raw_hash = f"{ip_address}-{user_agent}"
            ip_hash = hashlib.sha256(raw_hash.encode()).hexdigest()
            
            visitor = db.query(VisitorLog).filter(VisitorLog.ip_hash == ip_hash).first()
            if visitor:
                visitor.visit_count += 1
            else:
                new_visitor = VisitorLog(ip_hash=ip_hash, user_agent=user_agent)
                db.add(new_visitor)
                
            db.commit()
        except Exception as e:
            logger.error(f"Failed to save analytics: {e}")
        finally:
            db.close()

    return response

# CORS — allow all origins in development (frontend may run on any port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(jobs.router,      prefix="/api/jobs",      tags=["Jobs"])
app.include_router(resume.router,    prefix="/api/resume",    tags=["Resume AI"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(scrape.router,    prefix="/api/scrape",    tags=["Scraper"])
app.include_router(admin.router,     prefix="/api/admin",     tags=["Admin"])


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "running",
        "message": "AI Job Portal API is live 🚀",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

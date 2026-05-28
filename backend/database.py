from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jobs.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def log_external_api(endpoint: str, method: str, status_code: int, duration_ms: float, client_ip: str = "external"):
    from models import APILog
    db = SessionLocal()
    try:
        db.add(APILog(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            ip_address=client_ip,
            duration_ms=duration_ms
        ))
        db.commit()
    except Exception as e:
        pass
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""
AI Resume Analyzer — Google Gemini powered.
Robust implementation with comprehensive error handling,
debug endpoint, and TF-IDF fallback.
"""
import os
import re
import json
import logging
import io
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

# Load .env explicitly from the backend directory
from dotenv import load_dotenv
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

from database import SessionLocal
from models import Job

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Gemini lazy init (avoids undefined _gemini_model bug) ─────────────────────
_gemini_model = None
_gemini_ready = False
_gemini_error = ""

def _init_gemini():
    """Initialize Gemini. Called lazily on first use."""
    global _gemini_model, _gemini_ready, _gemini_error

    if _gemini_ready:
        return True

    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "your_gemini_api_key_here":
        _gemini_error = "GEMINI_API_KEY not set in backend/.env"
        return False

    if not key.startswith("AIza"):
        _gemini_error = (
            f"Invalid API key format (starts with '{key[:8]}...'). "
            "Gemini keys must start with 'AIza'. "
            "Get a valid key at https://aistudio.google.com/app/apikey"
        )
        logger.error(f"❌ {_gemini_error}")
        return False

    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        # Use gemini-2.5-flash — latest stable model supported by this key
        _gemini_model = genai.GenerativeModel("gemini-2.5-flash")
        _gemini_ready = True
        _gemini_error = ""
        logger.info("✅ Gemini initialized with model: gemini-2.5-flash")
        return True
    except Exception as e:
        _gemini_error = str(e)
        logger.error(f"❌ Gemini init error: {e}")
        return False


# ── Schemas ───────────────────────────────────────────────────────────────────
class ResumeTextRequest(BaseModel):
    resume_text: str
    top_n: int = 10


class JobMatchResult(BaseModel):
    job_id: int
    title: str
    company: str
    location: Optional[str] = None
    job_type: Optional[str] = None
    source: Optional[str] = None
    apply_link: Optional[str] = None
    match_score: float
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    suggestions: List[str] = []


class ResumeImprovement(BaseModel):
    category: str        # e.g., "Formatting", "Content", "Impact", "Skills"
    issue: str           # e.g., "Missing action verbs"
    suggestion: str      # e.g., "Change 'did XYZ' to 'Engineered XYZ...'"


class ResumeAnalysisResponse(BaseModel):
    top_matches: List[JobMatchResult]
    overall_score: float
    detected_skills: List[str]
    improvement_tips: List[str]  # Kept for backward compatibility
    improvements: List[ResumeImprovement] = []
    gemini_summary: Optional[str] = None
    powered_by: str = "TF-IDF"


# ── PDF extraction ────────────────────────────────────────────────────────────
def _extract_pdf_text(content: bytes) -> str:
    """Try multiple PDF libraries to extract text."""
    # Method 1: pdfplumber (best quality)
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")

    # Method 2: PyPDF2
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"PyPDF2 failed: {e}")

    # Method 3: pymupdf (fitz)
    try:
        import fitz  # pymupdf
        doc = fitz.open(stream=content, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"PyMuPDF failed: {e}")

    # Method 4: raw byte extraction (crude fallback)
    try:
        raw = content.decode("latin-1", errors="ignore")
        # Extract readable ASCII
        text = re.sub(r"[^\x20-\x7e\n\t]", " ", raw)
        text = re.sub(r" {4,}", " ", text)
        return text
    except Exception:
        return ""


def _extract_file_text(content: bytes, filename: str) -> str:
    fn = filename.lower()
    if fn.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")
    elif fn.endswith(".pdf"):
        return _extract_pdf_text(content)
    else:
        return content.decode("utf-8", errors="ignore")


# ── TF-IDF fallback ───────────────────────────────────────────────────────────
COMMON_SKILLS = [
    "Python", "Java", "JavaScript", "TypeScript", "React", "Angular", "Vue",
    "Node.js", "Express", "Django", "Flask", "FastAPI", "Spring Boot",
    "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "CI/CD", "Git",
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Scikit-learn",
    "Data Analysis", "Pandas", "NumPy", "Tableau", "Power BI",
    "Figma", "Adobe XD", "UI/UX", "HTML", "CSS", "SASS", "REST API",
    "GraphQL", "Microservices", "Agile", "Scrum", "Linux", "C++", "C#",
    "Go", "Rust", "Kotlin", "Swift", "Excel", "NLP", "Computer Vision",
    "Statistics", "R", "Hadoop", "Spark", "Kafka", "Jenkins", "Terraform",
]


def _detect_skills(text: str) -> List[str]:
    """Match skills using word boundaries to avoid false positives.
    Only used as fallback when Gemini is unavailable."""
    found = []
    for skill in COMMON_SKILLS:
        # Escape special regex chars in skill name, then match whole word/phrase
        pattern = r'(?i)(?<![\w.])' + re.escape(skill) + r'(?![\w.])'
        if re.search(pattern, text):
            found.append(skill)
    return found


def _tfidf_analysis(resume_text: str, jobs: list, top_n: int) -> ResumeAnalysisResponse:
    """TF-IDF cosine similarity matching."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    detected_skills = _detect_skills(resume_text)

    if not jobs:
        return ResumeAnalysisResponse(
            top_matches=[], overall_score=0,
            detected_skills=detected_skills,
            improvement_tips=["No jobs in database yet. Jobs are scraped automatically every day."],
            gemini_summary="No jobs available to match against.",
            powered_by="TF-IDF",
        )

    job_texts = [
        " ".join(filter(None, [j.title or "", j.company or "", j.skills or "", j.description or ""]))
        for j in jobs
    ]
    corpus = [resume_text] + job_texts

    try:
        vec = TfidfVectorizer(stop_words="english", max_features=5000, ngram_range=(1, 2))
        mat = vec.fit_transform(corpus)
        sims = cosine_similarity(mat[0], mat[1:])[0]
    except Exception as e:
        logger.error(f"TF-IDF error: {e}")
        sims = [0.0] * len(jobs)

    ranked = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:top_n]
    resume_skills_set = set(s.lower() for s in detected_skills)

    matches = []
    for idx in ranked:
        job = jobs[idx]
        score = min(round(float(sims[idx]) * 100 * 2.5, 1), 95)  # Scale up for display
        job_skills_raw = [s.strip() for s in (job.skills or "").split(",") if s.strip()]
        job_skills_lower = set(s.lower() for s in job_skills_raw)
        matched = [s for s in job_skills_raw if s.lower() in resume_skills_set]
        missing = [s for s in job_skills_raw if s.lower() not in resume_skills_set]
        matches.append(JobMatchResult(
            job_id=job.id, title=job.title, company=job.company,
            location=job.location, job_type=job.job_type,
            source=job.source, apply_link=job.apply_link,
            match_score=score,
            matched_skills=matched[:6],
            missing_skills=missing[:6],
            suggestions=["Tailor your resume to include more keywords from this job description."],
        ))

    overall = round(sum(m.match_score for m in matches) / len(matches), 1) if matches else 0

    return ResumeAnalysisResponse(
        top_matches=matches,
        overall_score=overall,
        detected_skills=detected_skills,
        improvement_tips=[],  # Only Gemini provides real tips
        gemini_summary=None,
        powered_by="TF-IDF",
    )


# ── Gemini analysis ───────────────────────────────────────────────────────────
def _gemini_analysis(resume_text: str, jobs: list, top_n: int) -> ResumeAnalysisResponse:
    """Full Gemini-powered analysis."""

    # Build compact job list — include index so Gemini can reference by index (more reliable than ID)
    job_entries = []
    sample_jobs = jobs[:40]  # Limit to 40 for token budget
    for i, job in enumerate(sample_jobs):
        job_entries.append(
            f"[{i}] {job.title} @ {job.company} | Skills: {(job.skills or 'not listed')[:80]} | Type: {job.job_type or 'N/A'}"
        )
    jobs_block = "\n".join(job_entries)

    prompt = f"""You are an expert ATS system, career coach, and strict proofreader. Analyze the resume below and match it to the job list. You MUST identify mistakes, areas for improvement, formatting errors, and typos.

=== RESUME ===
{resume_text[:2800]}

=== AVAILABLE JOBS (use the index number [N] to reference them) ===
{jobs_block}

=== TASK ===
Return ONLY a valid JSON object. No explanation, no markdown, no code blocks.

{{
  "detected_skills": ["Python", "React", ...],
  "overall_score": 72,
  "summary": "Brief 2-3 sentence professional assessment of this candidate.",
  "improvements": [
    {{
      "category": "Mistake / Formatting / Content / Grammar",
      "issue": "Specific mistake or vague text found in the resume",
      "suggestion": "Actionable fix for the mistake"
    }}
  ],
  "top_matches": [
    {{
      "job_index": 0,
      "match_score": 88,
      "matched_skills": ["Python", "SQL"],
      "missing_skills": ["Docker"],
      "suggestion": "Strong match — highlight your backend API experience."
    }}
  ]
}}

Rules:
- overall_score: 0-100 integer (quality of resume + fit for these jobs)
- top_matches: up to {min(top_n, 8)} best matching jobs, sorted by match_score desc
- job_index: use the [N] number from the job list above
- match_score: 0-100
- improvements: 4-6 specific identified issues and actionable suggestions based on THIS specific resume. You MUST look for and include mistakes such as grammar issues, spelling errors, poor formatting, missing sections, and vague achievements. Be highly critical.
- category: Use one of "Grammar/Spelling", "Formatting", "Impact", "Content", "Missing Section".

IMPORTANT: Return only raw JSON. Do not wrap in ```json``` or add any text outside the JSON."""

    try:
        import time
        from datetime import datetime, timezone
        from database import SessionLocal, log_external_api
        from models import APILog, SystemSetting
        
        # Check daily limit
        db = SessionLocal()
        try:
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            calls_today = db.query(APILog).filter(
                APILog.endpoint.like('%gemini%'), 
                APILog.timestamp >= today_start
            ).count()
            
            setting = db.query(SystemSetting).filter(SystemSetting.key == "resume_analyzer_limit").first()
            limit = int(setting.value) if setting else 100
            
            if calls_today >= limit:
                logger.warning(f"Gemini API limit reached ({calls_today}/{limit}). Falling back to TF-IDF.")
                return _tf_idf_fallback(resume_text, jobs, top_n)
        finally:
            db.close()

        start_time = time.time()
        
        response = _gemini_model.generate_content(prompt)
        
        duration = (time.time() - start_time) * 1000
        log_external_api("gemini.googleapis.com/v1beta/models/gemini-2.5-flash", "POST", 200, duration)
            
        raw = response.text.strip()

        # Strip markdown fences if present
        raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
        raw = re.sub(r'\n?```\s*$', '', raw)
        raw = raw.strip()

        # Find JSON object in response
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            raw = json_match.group()

        data = json.loads(raw)

        detected_skills = data.get("detected_skills", [])
        overall_score = float(data.get("overall_score", 0))
        summary = data.get("summary", "")
        # Handle both old and new formats gracefully
        raw_improvements = data.get("improvements", [])
        improvement_tips = data.get("improvement_tips", [])
        if not improvement_tips and raw_improvements:
            improvement_tips = [imp.get("suggestion", "") for imp in raw_improvements]
        
        raw_matches = data.get("top_matches", [])

        top_matches: List[JobMatchResult] = []
        for m in raw_matches:
            # Use job_index to look up in our sample_jobs list
            job_idx = m.get("job_index")
            if job_idx is None or not isinstance(job_idx, int) or job_idx >= len(sample_jobs):
                continue
            job = sample_jobs[job_idx]
            top_matches.append(JobMatchResult(
                job_id=job.id,
                title=job.title,
                company=job.company,
                location=job.location,
                job_type=job.job_type,
                source=job.source,
                apply_link=job.apply_link,
                match_score=float(m.get("match_score", 0)),
                matched_skills=m.get("matched_skills", []),
                missing_skills=m.get("missing_skills", []),
                suggestions=[m.get("suggestion", "")] if m.get("suggestion") else [],
            ))

        # If Gemini returned no valid matches, supplement with TF-IDF
        if not top_matches:
            logger.warning("Gemini returned no valid job matches, using TF-IDF for matches.")
            fb = _tfidf_analysis(resume_text, jobs, top_n)
            top_matches = fb.top_matches

        return ResumeAnalysisResponse(
            top_matches=top_matches,
            overall_score=overall_score,
            detected_skills=detected_skills,
            improvement_tips=improvement_tips[:4],  # Legacy field
            improvements=raw_improvements[:5],      # New structured field
            gemini_summary=summary,
            powered_by="Gemini AI",
        )

    except json.JSONDecodeError as e:
        logger.error(f"Gemini JSON parse error: {e}")
        logger.error(f"Raw response (first 600 chars): {raw[:600] if 'raw' in dir() else 'N/A'}")
        # Fallback to TF-IDF but keep any extracted summary
        result = _tfidf_analysis(resume_text, jobs, top_n)
        result.gemini_summary = "⚠️ Gemini response could not be parsed. Showing TF-IDF results."
        return result

    except Exception as e:
        logger.error(f"Gemini analysis exception: {e}")
        result = _tfidf_analysis(resume_text, jobs, top_n)
        result.gemini_summary = f"⚠️ Gemini error: {str(e)[:100]}"
        return result


# ── Core entry point ──────────────────────────────────────────────────────────
def _run_analysis(resume_text: str, top_n: int) -> ResumeAnalysisResponse:
    db = SessionLocal()
    try:
        jobs = db.query(Job).filter(Job.is_active == True).order_by(Job.id.desc()).limit(300).all()

        if not jobs:
            return ResumeAnalysisResponse(
                top_matches=[],
                overall_score=0,
                detected_skills=_detect_skills(resume_text),
                improvement_tips=["No jobs in database yet. The backend scrapes jobs automatically every day at midnight."],
                gemini_summary="Please wait for the job scraper to complete its first run.",
                powered_by="N/A",
            )

        # Try Gemini (lazy init)
        if _init_gemini():
            try:
                return _gemini_analysis(resume_text, jobs, top_n)
            except Exception as e:
                logger.error(f"Gemini analysis failed, using TF-IDF fallback: {e}")

        # TF-IDF fallback
        result = _tfidf_analysis(resume_text, jobs, top_n)
        if _gemini_error:
            result.gemini_summary = f"⚠️ Gemini unavailable: {_gemini_error}"
        return result

    finally:
        db.close()


# ── Routes ────────────────────────────────────────────────────────────────────
@router.get("/status")
def resume_ai_status():
    """Check Gemini status. Also triggers lazy init so you see real errors."""
    ready = _init_gemini()
    db = SessionLocal()
    try:
        job_count = db.query(Job).filter(Job.is_active == True).count()
    finally:
        db.close()

    return {
        "gemini_ready": ready,
        "gemini_error": _gemini_error if not ready else None,
        "model": "gemini-2.5-flash" if ready else None,
        "jobs_in_database": job_count,
        "message": (
            f"✅ Gemini AI active — {job_count} jobs ready to match"
            if ready
            else f"⚠️ {_gemini_error or 'Gemini not configured'} — Using TF-IDF fallback ({job_count} jobs)"
        ),
    }


@router.get("/debug")
def resume_debug():
    """Debug endpoint: shows env, Gemini status, DB job count."""
    key = os.getenv("GEMINI_API_KEY", "")
    db = SessionLocal()
    try:
        jobs = db.query(Job).filter(Job.is_active == True).all()
    finally:
        db.close()

    return {
        "env_file_path": str(_env_path),
        "env_file_exists": _env_path.exists(),
        "api_key_set": bool(key),
        "api_key_prefix": key[:8] + "..." if key else "NOT SET",
        "api_key_valid_format": key.startswith("AIza") if key else False,
        "gemini_ready": _gemini_ready,
        "gemini_error": _gemini_error,
        "total_jobs": len(jobs),
        "jobs_with_skills": sum(1 for j in jobs if j.skills),
        "sources": list(set(j.source for j in jobs)),
    }


@router.post("/analyze-text", response_model=ResumeAnalysisResponse)
def analyze_resume_text(request: ResumeTextRequest):
    """Analyze pasted resume text."""
    text = request.resume_text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Resume text cannot be empty.")
    if len(text) < 30:
        raise HTTPException(status_code=400, detail="Resume text is too short. Please paste your full resume.")
    return _run_analysis(text, request.top_n)


@router.post("/analyze-file", response_model=ResumeAnalysisResponse)
async def analyze_resume_file(file: UploadFile = File(...), top_n: int = 10):
    """Upload a resume file (PDF or TXT) for AI analysis."""
    fname = (file.filename or "").lower()
    if not (fname.endswith(".pdf") or fname.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Only .pdf and .txt files are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 5MB limit.")

    text = _extract_file_text(content, file.filename)
    if not text or len(text.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not extract readable text from this PDF. "
                "Try saving it as a text file, or copy-paste the content using 'Paste Text' mode."
            )
        )
    return _run_analysis(text.strip(), top_n)

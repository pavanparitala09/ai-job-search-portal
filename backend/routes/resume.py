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

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from pydantic import BaseModel

# Load .env explicitly from the backend directory
from dotenv import load_dotenv
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

from database import SessionLocal
from models import Job

logger = logging.getLogger(__name__)
router = APIRouter()

def _get_client_id(request: Request) -> str:
    """Generate a unique privacy-safe SHA-256 hash for each user based on IP and User-Agent."""
    import hashlib
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    raw_hash = f"{ip_address}-{user_agent}"
    return hashlib.sha256(raw_hash.encode()).hexdigest()


# ── Groq lazy init (avoids undefined _groq_client bug) ─────────────────────────
_groq_client = None
_groq_ready = False
_groq_error = ""

def _init_groq():
    """Initialize Groq. Called lazily on first use."""
    global _groq_client, _groq_ready, _groq_error

    if _groq_ready:
        return True

    # Reload env to pick up any runtime changes to .env file
    load_dotenv(dotenv_path=_env_path, override=True)
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key or key == "your_groq_api_key_here":
        _groq_error = "GROQ_API_KEY not set in backend/.env"
        return False

    try:
        from groq import Groq
        client = Groq(api_key=key)
        # Validate key with a simple generation call to fail early if invalid
        client.chat.completions.create(
            messages=[{"role": "user", "content": "ping"}],
            model="llama-3.3-70b-versatile",
            max_tokens=5,
        )
        _groq_client = client
        _groq_ready = True
        _groq_error = ""
        logger.info("✅ Groq initialized and validated with model: llama-3.3-70b-versatile")
        return True
    except Exception as e:
        _groq_ready = False
        _groq_error = str(e)
        logger.error(f"❌ Groq init/validation error: {e}")
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
    resume_text: Optional[str] = None  # Return extracted resume text


class CoverLetterRequest(BaseModel):
    resume_text: str
    job_id: int


class CoverLetterResponse(BaseModel):
    cover_letter: str
    job_title: str
    company: str


# ── PDF extraction ────────────────────────────────────────────────────────────
def _extract_pdf_text(content: bytes) -> str:
    """Try multiple PDF libraries to extract text."""
    extracted = ""

    # Method 1: pdfplumber (best quality)
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            extracted = "\n".join(p.extract_text() or "" for p in pdf.pages)
        if extracted.strip():
            logger.info("PDF extracted via pdfplumber")
            return extracted
    except ImportError:
        logger.warning("pdfplumber not installed — trying PyPDF2")
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")

    # Method 2: PyPDF2
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        extracted = "\n".join(p.extract_text() or "" for p in reader.pages)
        if extracted.strip():
            logger.info("PDF extracted via PyPDF2")
            return extracted
    except ImportError:
        logger.warning("PyPDF2 not installed — trying pymupdf")
    except Exception as e:
        logger.warning(f"PyPDF2 failed: {e}")

    # Method 3: pymupdf (fitz)
    try:
        import fitz  # pymupdf
        doc = fitz.open(stream=content, filetype="pdf")
        extracted = "\n".join(page.get_text() for page in doc)
        if extracted.strip():
            logger.info("PDF extracted via PyMuPDF")
            return extracted
    except ImportError:
        logger.warning("PyMuPDF not installed — trying raw byte fallback")
    except Exception as e:
        logger.warning(f"PyMuPDF failed: {e}")

    # Method 4: raw byte extraction (crude fallback — strips binary noise)
    try:
        raw = content.decode("latin-1", errors="ignore")
        # Keep only printable ASCII + newlines/tabs
        text = re.sub(r"[^\x20-\x7e\n\t]", " ", raw)
        # Collapse excessive whitespace runs
        text = re.sub(r"[ \t]{4,}", " ", text)
        text = re.sub(r"\n{4,}", "\n\n", text)
        logger.warning("PDF extracted via raw byte fallback — quality may be low")
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


# ── Groq analysis ─────────────────────────────────────────────────────────────
def _groq_analysis(resume_text: str, jobs: list, top_n: int, client_ip: str) -> ResumeAnalysisResponse:
    """Full Groq-powered analysis."""

    # Build compact job list — include index so Groq can reference by index (more reliable than ID)
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
      "category": "Grammar/Spelling",
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
"""

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
                APILog.endpoint.like('%groq%'), 
                APILog.ip_address == client_ip,
                APILog.timestamp >= today_start
            ).count()
            
            setting = db.query(SystemSetting).filter(SystemSetting.key == "resume_analyzer_limit").first()
            limit = int(setting.value) if setting else 100
            
            if calls_today >= limit:
                logger.warning(f"Groq API limit reached ({calls_today}/{limit}) for user {client_ip}. Falling back to TF-IDF.")
                result = _tfidf_analysis(resume_text, jobs, top_n)
                result.gemini_summary = "⚠️ limit_exceeded"
                return result
        finally:
            db.close()

        start_time = time.time()
        
        response = _groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        
        duration = (time.time() - start_time) * 1000
        log_external_api("api.groq.com/openai/v1/chat/completions", "POST", 200, duration, client_ip=client_ip)
            
        raw = response.choices[0].message.content.strip()

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

        if not top_matches:
            logger.warning("Groq returned no valid job matches, using TF-IDF for matches.")
            fb = _tfidf_analysis(resume_text, jobs, top_n)
            top_matches = fb.top_matches

        return ResumeAnalysisResponse(
            top_matches=top_matches,
            overall_score=overall_score,
            detected_skills=detected_skills,
            improvement_tips=improvement_tips[:4],
            improvements=raw_improvements[:5],
            gemini_summary=summary,
            powered_by="Groq AI",
        )

    except json.JSONDecodeError as e:
        logger.error(f"Groq JSON parse error: {e}")
        logger.error(f"Raw response (first 600 chars): {raw if 'raw' in locals() else 'N/A'}")
        result = _tfidf_analysis(resume_text, jobs, top_n)
        result.gemini_summary = "⚠️ Groq response could not be parsed. Showing TF-IDF results."
        return result

    except Exception as e:
        logger.error(f"Groq analysis exception: {e}")
        global _groq_ready, _groq_error
        _groq_ready = False
        _groq_error = str(e)
        result = _tfidf_analysis(resume_text, jobs, top_n)
        result.gemini_summary = f"⚠️ Groq error: {str(e)[:100]}"
        return result


# ── Core entry point ──────────────────────────────────────────────────────────
def _run_analysis(resume_text: str, top_n: int, client_ip: str) -> ResumeAnalysisResponse:
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
                resume_text=resume_text,
            )

        # Try Groq (lazy init)
        if _init_groq():
            try:
                res = _groq_analysis(resume_text, jobs, top_n, client_ip)
                res.resume_text = resume_text
                return res
            except Exception as e:
                logger.error(f"Groq analysis failed, using TF-IDF fallback: {e}")
                global _groq_ready, _groq_error
                _groq_ready = False
                _groq_error = str(e)

        # TF-IDF fallback
        result = _tfidf_analysis(resume_text, jobs, top_n)
        result.resume_text = resume_text
        if _groq_error:
            result.gemini_summary = f"⚠️ Groq unavailable: {_groq_error}"
        return result

    finally:
        db.close()


# ── Routes ────────────────────────────────────────────────────────────────────
@router.get("/status")
def resume_ai_status(request: Request):
    """Check Groq status. Also triggers lazy init so you see real errors."""
    ready = _init_groq()
    db = SessionLocal()
    try:
        job_count = db.query(Job).filter(Job.is_active == True).count()
        
        # Check daily limit status
        from datetime import datetime, timezone
        from models import APILog, SystemSetting
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        client_ip = _get_client_id(request)
        calls_today = db.query(APILog).filter(
            APILog.endpoint.like('%groq%'), 
            APILog.ip_address == client_ip,
            APILog.timestamp >= today_start
        ).count()
        
        setting = db.query(SystemSetting).filter(SystemSetting.key == "resume_analyzer_limit").first()
        limit = int(setting.value) if setting else 100
        
        limit_exceeded = calls_today >= limit
    finally:
        db.close()

    if limit_exceeded:
        return {
            "gemini_ready": False,
            "gemini_error": f"Daily limit exceeded ({calls_today}/{limit})",
            "model": "llama-3.3-70b-versatile",
            "jobs_in_database": job_count,
            "message": f"⚠️ Daily analysis limit reached ({calls_today}/{limit}). Please come back tomorrow when reset.",
        }

    return {
        "gemini_ready": ready,
        "gemini_error": _groq_error if not ready else None,
        "model": "llama-3.3-70b-versatile" if ready else None,
        "jobs_in_database": job_count,
        "message": (
            f"✅ Groq AI active — {job_count} jobs ready to match"
            if ready
            else f"⚠️ {_groq_error or 'Groq not configured'} — Using TF-IDF fallback ({job_count} jobs)"
        ),
    }


@router.get("/debug")
def resume_debug():
    """Debug endpoint: shows env, Groq status, DB job count."""
    key = os.getenv("GROQ_API_KEY", "")
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
        "api_key_valid_format": True if key else False,
        "gemini_ready": _groq_ready,
        "gemini_error": _groq_error,
        "total_jobs": len(jobs),
        "jobs_with_skills": sum(1 for j in jobs if j.skills),
        "sources": list(set(j.source for j in jobs)),
    }


@router.post("/analyze-text", response_model=ResumeAnalysisResponse)
def analyze_resume_text(request: Request, request_data: ResumeTextRequest):
    """Analyze pasted resume text."""
    text = request_data.resume_text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Resume text cannot be empty.")
    if len(text) < 30:
        raise HTTPException(status_code=400, detail="Resume text is too short. Please paste your full resume.")
    client_ip = _get_client_id(request)
    return _run_analysis(text, request_data.top_n, client_ip)


@router.post("/analyze-file", response_model=ResumeAnalysisResponse)
async def analyze_resume_file(request: Request, file: UploadFile = File(...), top_n: int = 10):
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
    if not text or len(text.strip()) < 10:
        raise HTTPException(
            status_code=422,
            detail=(
                "Could not extract readable text from your PDF. "
                "This usually happens with scanned/image-based PDFs. "
                "Please switch to '📝 Paste Text' mode and paste your resume content directly — it works just as well!"
            )
        )
    client_ip = _get_client_id(request)
    return _run_analysis(text.strip(), top_n, client_ip)


@router.post("/generate-cover-letter", response_model=CoverLetterResponse)
def generate_cover_letter(request: Request, request_data: CoverLetterRequest):
    """Generate a cover letter for a specific job based on the resume text."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == request_data.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")

        if not _init_groq():
            raise HTTPException(
                status_code=503,
                detail=f"Groq AI is currently unavailable: {_groq_error or 'Not configured'}"
            )

        client_ip = _get_client_id(request)

        # Check daily limit for this user
        from datetime import datetime, timezone
        from models import APILog, SystemSetting
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        calls_today = db.query(APILog).filter(
            APILog.endpoint.like('%groq%'), 
            APILog.ip_address == client_ip,
            APILog.timestamp >= today_start
        ).count()
        
        setting = db.query(SystemSetting).filter(SystemSetting.key == "resume_analyzer_limit").first()
        limit = int(setting.value) if setting else 100
        
        if calls_today >= limit:
            raise HTTPException(
                status_code=429,
                detail="Daily AI analysis limit reached. Please come back tomorrow when reset."
            )

        prompt = f"""You are an expert career coach and professional writer. Write a highly tailored, compelling, and professional cover letter for the candidate based on their resume and the target job description. 

=== CANDIDATE RESUME ===
{request_data.resume_text[:2800]}

=== TARGET JOB ===
Title: {job.title}
Company: {job.company}
Description: {job.description or 'not listed'}
Requirements: {job.requirements or 'not listed'}
Skills: {job.skills or 'not listed'}

=== INSTRUCTIONS ===
- The cover letter should be professional, polite, and persuasive.
- Explicitly connect the candidate's matching skills/experience from the resume to the requirements of the job.
- Address any obvious gaps diplomatically, focusing on eagerness to learn and adaptability.
- Do NOT make up false information or achievements not present in the resume.
- Keep it concise (around 250-350 words, maximum 3-4 paragraphs).
- Use standard business letter format (without specific placeholder dates or addresses, start directly with "Dear Hiring Team at {job.company}," and end with "Sincerely, [Candidate Name]").

Return ONLY the plain text of the cover letter. No explanations, no markdown formatting (except newlines), no headers, no conversational intro/outro from you. Start directly with the greeting."""

        try:
            import time
            from database import log_external_api

            start_time = time.time()
            response = _groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
            )
            duration = (time.time() - start_time) * 1000
            log_external_api("api.groq.com/openai/v1/chat/completions", "POST", 200, duration, client_ip=client_ip)

            cover_letter_text = response.choices[0].message.content.strip()

            return CoverLetterResponse(
                cover_letter=cover_letter_text,
                job_title=job.title,
                company=job.company
            )

        except Exception as e:
            logger.error(f"Failed to generate cover letter: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate cover letter: {str(e)}")

    finally:
        db.close()


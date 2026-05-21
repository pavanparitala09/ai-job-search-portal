# JobPortal AI - Backend

This is the core logic and API server for the JobPortal AI platform. Built with Python and FastAPI, it handles everything from data persistence, JWT authentication, background job scraping, and real-time AI resume analysis via Google Gemini.

## Technology Stack
- **Framework:** FastAPI (High-performance, async-ready Python web framework)
- **Database:** SQLite & SQLAlchemy (ORM for relational data management)
- **Authentication:** JWT (JSON Web Tokens) with Passlib & Bcrypt (Password hashing)
- **AI Integration:** Google Generative AI (`gemini-2.5-flash`) for NLP and resume parsing.
- **Web Scraping:** BeautifulSoup4, Requests, and lxml (for parsing job boards like Internshala, RemoteOK, etc.)
- **Task Scheduling:** APScheduler (for automated, background cron jobs)
- **PDF Parsing:** PyPDF2 (for extracting text from uploaded resumes)

## Project Architecture
```
backend/
├── database.py       # SQLAlchemy engine and session management
├── main.py           # FastAPI application entry point, CORS, and middleware
├── models.py         # Database schema definitions (Jobs, Admin, Logs, Settings)
├── requirements.txt  # Python package dependencies
├── scheduler.py      # APScheduler configuration for daily/interval scraping
├── schemas.py        # Pydantic models for API request/response validation
├── routes/
│   ├── admin.py      # Secure endpoints for auth, analytics, and config
│   ├── jobs.py       # Public endpoints for fetching/searching jobs
│   └── resume.py     # Endpoints handling PDF upload and Gemini AI processing
└── scrapers/
    ├── orchestrator.py # Manages concurrent execution of multiple scrapers
    ├── internshala.py  # Scraper module
    ├── remoteok.py     # Scraper module
    ├── linkedin.py     # Scraper module
    └── indeed.py       # Scraper module
```

## Core Features

### 1. The Scraper Engine
Located in the `scrapers/` folder, this engine programmatically crawls external job boards. It can be triggered manually via the Admin Dashboard or left to run on an automated interval managed by `APScheduler`. Real-time progress is streamed back to the frontend using **Server-Sent Events (SSE)**.

### 2. AI Resume Analyzer
The `/api/resume/analyze` endpoint accepts a PDF file and the IDs of the jobs the user wants to apply to. It extracts the text via `PyPDF2` and constructs a prompt for `Google Gemini`. The AI acts as a strict recruiter, calculating match percentages and providing specific actionable feedback on grammar, formatting, and content. It gracefully falls back to a basic TF-IDF mathematical matching algorithm if the Gemini API daily limit is exceeded.

### 3. Analytics & Admin Controls
A robust admin panel tracks unique site visitors (via hashed IP addresses for privacy) and external API usage. Administrators can configure how often the scraper runs (1-30 days) and set hard daily limits on Gemini API calls to control costs.

## Getting Started

1. Ensure Python 3.10+ is installed.
2. Navigate to the `backend` directory: `cd backend`
3. Create a virtual environment: `python -m venv .venv`
4. Activate the virtual environment:
   - Windows: `.\.venv\Scripts\activate`
   - Mac/Linux: `source .venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Create a `.env` file in the `backend` directory:
   ```env
   GEMINI_API_KEY=your_google_ai_studio_key
   JWT_SECRET=your_super_secret_jwt_string
   ```
7. Run the server: `uvicorn main:app --reload`

The API will be available at `http://localhost:8000`. You can view the automatic Swagger documentation by visiting `http://localhost:8000/docs`.

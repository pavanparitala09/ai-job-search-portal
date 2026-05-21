# JobPortal AI 🚀

JobPortal AI is an intelligent, automated job aggregation and matching platform. It continuously scrapes fresh job listings from top remote and tech job boards (like Internshala, RemoteOK, Indeed, etc.) and leverages **Google Gemini 2.5 AI** to parse candidate resumes, extract skills, and match them against the latest opportunities in real-time.

This project is structured as a full-stack monolith repository containing both the React frontend and the FastAPI backend.

## 🌟 Key Features
- **AI Resume Analyzer:** Upload a PDF resume, and the AI extracts skills, calculates a match score against current jobs, and gives actionable improvement suggestions.
- **Automated Web Scraping:** Runs background cron jobs using `APScheduler` to keep the database fresh with new opportunities.
- **Admin Management Dashboard:** A secure control panel protected by JWT authentication to manually trigger scrapers, schedule automation limits, and view live analytics.
- **API Analytics:** Tracks how often external APIs (Gemini & Web Scrapers) are being called to monitor usage and costs.
- **Beautiful UI:** A premium, dark-mode glassmorphism design with responsive gradients.

## 📁 Repository Structure
```
job_search_portal/
├── backend/          # Python FastAPI backend (SQLite, SQLAlchemy, APScheduler, Gemini AI)
├── frontend/         # React SPA (Vite, React Router, Lucide Icons)
├── start_backend.bat # Windows script to launch backend server
└── start_frontend.bat# Windows script to launch frontend dev server
```

## 🚀 Quick Start
To run this project locally, you need two terminals.

**1. Start the Backend:**
Open a terminal in the root directory and run:
```bash
.\start_backend.bat
```
*(Alternatively, `cd backend`, activate your `.venv`, and run `uvicorn main:app --reload`)*

**2. Start the Frontend:**
Open a second terminal in the root directory and run:
```bash
.\start_frontend.bat
```
*(Alternatively, `cd frontend` and run `npm run dev`)*

## 🔐 Environment Variables
To get the project working, you will need to add a `.env` file in the `/backend/` directory with the following keys:
- `GEMINI_API_KEY=your_gemini_api_key` (Required for resume parsing)
- `JWT_SECRET=your_jwt_secret_key` (Required for the Admin Dashboard)

For more detailed information on each layer, refer to the respective documentation:
- [Frontend Documentation](./frontend/README.md)
- [Backend Documentation](./backend/README.md)

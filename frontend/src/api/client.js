import axios from 'axios';

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
});

// Jobs
export const fetchJobs = (params) => API.get('/api/jobs', { params });
export const fetchJob = (id) => API.get(`/api/jobs/${id}`);
export const fetchJobStats = () => API.get('/api/jobs/stats');

// Resume AI
export const analyzeResumeText = (data) => API.post('/api/resume/analyze-text', data);
export const analyzeResumeFile = (formData) =>
  API.post('/api/resume/analyze-file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

// Analytics
export const fetchAnalytics = () => API.get('/api/analytics');

// Scraper
export const triggerScrape = (sources = null) =>
  API.post('/api/scrape/trigger', { sources });
export const fetchScrapeStatus = () => API.get('/api/scrape/status');
export const fetchScrapeLogs = () => API.get('/api/scrape/logs');

export default API;

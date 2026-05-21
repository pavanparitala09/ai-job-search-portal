import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { fetchJobs } from '../api/client';
import JobCard from '../components/JobCard';
import { Search, Filter, ChevronLeft, ChevronRight } from 'lucide-react';

const CATEGORIES = ['All', 'Software', 'Web Development', 'Data Science', 'AI/ML', 'DevOps', 'Design', 'Marketing', 'Mobile', 'Finance', 'Business', 'Content', 'General'];
const JOB_TYPES = ['All', 'Full-time', 'Internship', 'Remote', 'Part-time'];
const SOURCES = ['All', 'internshala', 'remoteok', 'indeed', 'linkedin'];

export default function Jobs() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [jobs, setJobs] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 24;

  const [filters, setFilters] = useState({
    search: searchParams.get('search') || '',
    category: 'All',
    job_type: 'All',
    source: 'All',
    location: '',
  });

  const debounceRef = useRef(null);

  const loadJobs = useCallback(async (f, p) => {
    setLoading(true);
    try {
      const params = {
        page: p || page,
        page_size: PAGE_SIZE,
      };
      if (f.search) params.search = f.search;
      if (f.category !== 'All') params.category = f.category;
      if (f.job_type !== 'All') params.job_type = f.job_type;
      if (f.source !== 'All') params.source = f.source;
      if (f.location) params.location = f.location;

      const res = await fetchJobs(params);
      setJobs(res.data.jobs || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [page]);

  // Load on mount and filter change
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => loadJobs(filters, 1), 300);
  }, [filters]);

  useEffect(() => {
    loadJobs(filters, page);
  }, [page]);

  const handleFilter = (key, val) => {
    setPage(1);
    setFilters(prev => ({ ...prev, [key]: val }));
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="page">
      <div className="container">
        {/* Header */}
        <div className="page-header">
          <h1>All Jobs <span style={{ color: 'var(--purple-light)' }}>({total.toLocaleString()})</span></h1>
          <p>Real-time listings scraped from Internshala, RemoteOK, Indeed & LinkedIn</p>
        </div>

        {/* Filters */}
        <div className="filters-bar">
          <div className="filter-group" style={{ flex: 2, minWidth: 200 }}>
            <label className="filter-label">Search</label>
            <div style={{ position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                className="filter-input"
                style={{ paddingLeft: '2rem' }}
                placeholder="Title, company, skill…"
                value={filters.search}
                onChange={e => handleFilter('search', e.target.value)}
              />
            </div>
          </div>

          <div className="filter-group">
            <label className="filter-label">Category</label>
            <select className="filter-select" value={filters.category} onChange={e => handleFilter('category', e.target.value)}>
              {CATEGORIES.map(c => <option key={c}>{c}</option>)}
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label">Type</label>
            <select className="filter-select" value={filters.job_type} onChange={e => handleFilter('job_type', e.target.value)}>
              {JOB_TYPES.map(t => <option key={t}>{t}</option>)}
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label">Source</label>
            <select className="filter-select" value={filters.source} onChange={e => handleFilter('source', e.target.value)}>
              {SOURCES.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label">Location</label>
            <input
              className="filter-input"
              placeholder="e.g. Bangalore"
              value={filters.location}
              onChange={e => handleFilter('location', e.target.value)}
            />
          </div>
        </div>

        {/* Results */}
        {loading ? (
          <div className="loader"><div className="spinner" /></div>
        ) : jobs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <h3>No jobs found</h3>
            <p>Try adjusting your filters or click "Scrape Now" in the navbar.</p>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: '1rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total} jobs
            </div>
            <div className="jobs-grid">
              {jobs.map(job => <JobCard key={job.id} job={job} />)}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="pagination">
                <button
                  className="page-btn"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft size={16} />
                </button>

                {Array.from({ length: Math.min(7, totalPages) }, (_, i) => {
                  let p;
                  if (totalPages <= 7) {
                    p = i + 1;
                  } else if (page <= 4) {
                    p = i + 1;
                  } else if (page >= totalPages - 3) {
                    p = totalPages - 6 + i;
                  } else {
                    p = page - 3 + i;
                  }
                  return (
                    <button
                      key={p}
                      className={`page-btn ${p === page ? 'active' : ''}`}
                      onClick={() => setPage(p)}
                    >
                      {p}
                    </button>
                  );
                })}

                <button
                  className="page-btn"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

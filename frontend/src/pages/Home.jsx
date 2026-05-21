import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchJobs, fetchJobStats } from '../api/client';
import JobCard from '../components/JobCard';
import { Search } from 'lucide-react';

export default function Home() {
  const navigate = useNavigate();
  const [stats, setStats] = useState({ total_jobs: 0, total_companies: 0, total_sources: 0 });
  const [featuredJobs, setFeaturedJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const [statsRes, jobsRes] = await Promise.all([
          fetchJobStats(),
          fetchJobs({ page: 1, page_size: 6 }),
        ]);
        setStats(statsRes.data);
        setFeaturedJobs(jobsRes.data.jobs || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    navigate(`/jobs?search=${encodeURIComponent(search)}`);
  };

  return (
    <div className="page">
      {/* Hero */}
      <section className="hero container">
        <div className="hero-badge">
          <span className="hero-badge-dot" />
          Live jobs from Internshala · RemoteOK · Indeed · LinkedIn
        </div>

        <h1>
          Find Your Dream Job with<br />
          <span className="gradient-text">AI-Powered Matching</span>
        </h1>

        <p className="hero-sub">
          Real-time job aggregation from top platforms. Upload your resume and get personalized AI recommendations, skill gap analysis, and market insights.
        </p>

        <form className="hero-search" onSubmit={handleSearch}>
          <Search size={18} style={{ color: 'var(--text-muted)', alignSelf: 'center', marginLeft: 8, flexShrink: 0 }} />
          <input
            type="text"
            placeholder="Search jobs, skills, companies…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <button type="submit" className="btn-search">Find Jobs</button>
        </form>

        {/* Stats */}
        <div className="hero-stats">
          <div className="hero-stat">
            <div className="hero-stat-number">{loading ? '…' : stats.total_jobs.toLocaleString()}</div>
            <div className="hero-stat-label">Live Jobs</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-number">{loading ? '…' : stats.total_companies.toLocaleString()}</div>
            <div className="hero-stat-label">Companies</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-number">4</div>
            <div className="hero-stat-label">Job Sources</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-number">AI</div>
            <div className="hero-stat-label">Resume Match</div>
          </div>
        </div>
      </section>

      {/* Source badges */}
      <section className="source-strip container">
        <div className="source-strip-label">Aggregating from</div>
        <div className="source-badges">
          <span className="source-badge internshala">🎓 Internshala</span>
          <span className="source-badge remoteok">🌍 RemoteOK</span>
          <span className="source-badge indeed">🔍 Indeed India</span>
          <span className="source-badge linkedin">💼 LinkedIn</span>
        </div>
      </section>

      {/* Featured Jobs */}
      <section className="container" style={{ paddingBottom: '4rem' }}>
        <div className="section-header">
          <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>Latest Jobs</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              Auto-refreshed daily from top job platforms
            </p>
          </div>
          <button className="page-btn" onClick={() => navigate('/jobs')}>
            View All →
          </button>
        </div>

        {loading ? (
          <div className="loader"><div className="spinner" /></div>
        ) : featuredJobs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <h3>No jobs yet</h3>
            <p>Jobs are scraped automatically every day. Check back soon!</p>
          </div>
        ) : (
          <div className="jobs-grid">
            {featuredJobs.map(job => <JobCard key={job.id} job={job} />)}
          </div>
        )}
      </section>

      {/* How it works */}
      <section className="container" style={{ paddingBottom: '5rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: '2rem', textAlign: 'center' }}>
          How It Works
        </h2>
        <div className="how-it-works-grid">
          {[
            { icon: '🔄', title: 'Daily Auto Scraping', desc: 'Automatically scrapes fresh jobs from Internshala, RemoteOK, Indeed & LinkedIn every day at midnight.' },
            { icon: '🤖', title: 'AI Resume Matching', desc: 'Upload your resume and our NLP engine computes a match score for every job using TF-IDF similarity.' },
            { icon: '🎯', title: 'Skill Gap Analysis', desc: 'See exactly which skills you have vs which the job requires — and what to learn next.' },
            { icon: '📊', title: 'Market Analytics', desc: 'Real insights on top categories, in-demand skills, salary ranges, and hiring trends.' },
          ].map(item => (
            <div key={item.title} className="card how-card">
              <div style={{ fontSize: '2rem' }}>{item.icon}</div>
              <div style={{ fontWeight: 700, fontSize: '1rem' }}>{item.title}</div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{item.desc}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

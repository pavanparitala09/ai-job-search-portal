import { MapPin, Clock, ExternalLink, Calendar, CalendarX } from 'lucide-react';

const SOURCE_COLORS = {
  internshala: 'internshala',
  remoteok: 'remoteok',
  indeed: 'indeed',
  linkedin: 'linkedin',
};

const TYPE_CLASSES = {
  'Full-time': 'full-time',
  'Internship': 'internship',
  'Remote': 'remote',
  'Part-time': 'part-time',
};

function formatSalary(min, max, currency) {
  if (!min && !max) return null;
  const fmt = (n) => {
    if (currency === 'INR') {
      if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
      return `₹${n.toLocaleString()}`;
    }
    return `$${(n / 1000).toFixed(0)}k`;
  };
  if (min && max) return `${fmt(min)} – ${fmt(max)}`;
  if (min) return `${fmt(min)}+`;
  return null;
}

function formatDate(raw) {
  if (!raw || raw.trim() === '') return null;

  // Already a friendly string like "Just now", "2 days ago", "Posted 3 days ago"
  if (/ago|today|just|posted|recently/i.test(raw)) {
    return raw.replace(/^(posted|just)\s*/i, '').trim();
  }

  // Try to parse as actual date
  try {
    const d = new Date(raw);
    if (!isNaN(d.getTime())) {
      const now = new Date();
      const diffMs = now - d;
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      if (diffDays === 0) return 'Today';
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 7) return `${diffDays} days ago`;
      if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
      return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
    }
  } catch {}

  // Return as-is (truncated) if none of the above worked
  return raw.length > 20 ? raw.slice(0, 20) : raw;
}

function isDeadlineSoon(deadline) {
  if (!deadline) return false;
  try {
    const d = new Date(deadline);
    if (isNaN(d.getTime())) return false;
    const diffDays = Math.ceil((d - new Date()) / (1000 * 60 * 60 * 24));
    return diffDays <= 3 && diffDays >= 0;
  } catch { return false; }
}

function isDeadlinePassed(deadline) {
  if (!deadline) return false;
  try {
    const d = new Date(deadline);
    if (isNaN(d.getTime())) return false;
    return d < new Date();
  } catch { return false; }
}

export default function JobCard({ job }) {
  const logoLetter = job.company?.[0]?.toUpperCase() || 'J';
  const salary = formatSalary(job.salary_min, job.salary_max, job.salary_currency);
  const skills = job.skills?.split(',').map(s => s.trim()).filter(Boolean).slice(0, 4) || [];
  const sourceClass = SOURCE_COLORS[job.source?.toLowerCase()] || 'linkedin';
  const typeClass = TYPE_CLASSES[job.job_type] || 'full-time';

  const postedStr = formatDate(job.posted_date);
  const deadlineStr = formatDate(job.deadline);
  const deadlineSoon = isDeadlineSoon(job.deadline);
  const deadlinePassed = isDeadlinePassed(job.deadline);

  return (
    <div className="card job-card">
      {/* Header */}
      <div className="job-card-header">
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start', flex: 1 }}>
          <div className="job-card-logo">
            {job.logo_url ? (
              <img src={job.logo_url} alt={job.company} onError={e => { e.target.style.display = 'none'; }} />
            ) : logoLetter}
          </div>
          <div style={{ flex: 1 }}>
            <div className="job-title">{job.title}</div>
            <div className="job-company">{job.company}</div>
          </div>
        </div>
        <span className={`job-card-source ${sourceClass}`}>
          {job.source || 'unknown'}
        </span>
      </div>

      {/* Meta row */}
      <div className="job-meta">
        {job.location && (
          <span className="job-meta-item">
            <MapPin size={12} /> {job.location.length > 22 ? job.location.slice(0, 22) + '…' : job.location}
          </span>
        )}
        {job.job_type && (
          <span className={`job-type-badge ${typeClass}`}>{job.job_type}</span>
        )}
        {job.category && (
          <span className="job-meta-item" style={{ color: 'var(--text-muted)' }}>
            {job.category}
          </span>
        )}
      </div>

      {/* Salary */}
      {salary && <div className="job-salary">💰 {salary}</div>}

      {/* Skills */}
      {skills.length > 0 && (
        <div className="job-skills">
          {skills.map(s => (
            <span key={s} className="skill-chip">{s}</span>
          ))}
        </div>
      )}

      {/* ── Dates row ── */}
      <div className="job-dates-row">
        {/* Posted date */}
        {postedStr && (
          <span className="job-date-item posted">
            <Calendar size={11} />
            <span>Posted: {postedStr}</span>
          </span>
        )}

        {/* Deadline */}
        {deadlineStr && (
          <span
            className="job-date-item deadline"
            style={{
              color: deadlinePassed
                ? '#ef4444'
                : deadlineSoon
                ? 'var(--orange)'
                : 'var(--text-muted)',
              borderColor: deadlinePassed
                ? 'rgba(239,68,68,0.25)'
                : deadlineSoon
                ? 'rgba(245,158,11,0.25)'
                : 'transparent',
              background: deadlinePassed
                ? 'rgba(239,68,68,0.08)'
                : deadlineSoon
                ? 'rgba(245,158,11,0.08)'
                : 'transparent',
            }}
          >
            <CalendarX size={11} />
            <span>
              {deadlinePassed ? '❌ Closed' : deadlineSoon ? '⚡ Closes: ' : 'Apply by: '}
              {!deadlinePassed && deadlineStr}
            </span>
          </span>
        )}
      </div>

      {/* Apply button */}
      <a
        href={job.apply_link || '#'}
        target="_blank"
        rel="noopener noreferrer"
        className="btn-apply"
        onClick={e => { if (!job.apply_link) e.preventDefault(); }}
        style={deadlinePassed ? { opacity: 0.5, cursor: 'not-allowed', pointerEvents: 'none' } : {}}
      >
        {deadlinePassed ? 'Applications Closed' : <>Apply Now <ExternalLink size={12} style={{ display: 'inline', marginLeft: 4 }} /></>}
      </a>
    </div>
  );
}

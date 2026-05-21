import { useState, useEffect } from 'react';
import { fetchAnalytics } from '../api/client';
import {
  BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Legend, CartesianGrid
} from 'recharts';
import { RefreshCw, TrendingUp, Briefcase, Globe, Star } from 'lucide-react';

const COLORS = ['#7c3aed', '#a855f7', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#6366f1', '#14b8a6', '#f97316', '#8b5cf6'];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div style={{
        background: 'rgba(13,13,37,0.95)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 8,
        padding: '0.6rem 1rem',
        fontSize: '0.8rem',
        backdropFilter: 'blur(10px)',
      }}>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 2 }}>{label}</p>
        <p style={{ color: '#a855f7', fontWeight: 700 }}>{payload[0].value} jobs</p>
      </div>
    );
  }
  return null;
};

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetchAnalytics();
      setData(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return (
    <div className="page">
      <div className="loader"><div className="spinner" /></div>
    </div>
  );

  if (!data) return (
    <div className="page">
      <div className="container">
        <div className="empty-state">
          <div className="empty-state-icon">📊</div>
          <h3>No data yet</h3>
          <p>Trigger a scrape to populate the analytics.</p>
        </div>
      </div>
    </div>
  );

  // Prepare chart data
  const categoryData = Object.entries(data.jobs_by_category || {})
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  const sourceData = Object.entries(data.jobs_by_source || {})
    .map(([name, value]) => ({ name, value }));

  const typeData = Object.entries(data.jobs_by_type || {})
    .map(([name, value]) => ({ name, value }));

  const topSkills = (data.top_skills || []).slice(0, 15);
  const maxSkill = topSkills[0]?.count || 1;

  const salaryDist = (data.salary_distribution || []).filter(s => s.count > 0);

  return (
    <div className="page">
      <div className="container">
        {/* Header */}
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>📊 Market <span className="gradient-text">Analytics</span></h1>
            <p>Real-time job market insights from aggregated listings</p>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button className="page-btn" onClick={load}><RefreshCw size={14} /></button>
          </div>
        </div>

        {/* KPI Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
          {[
            { label: 'Total Jobs', value: data.total_jobs?.toLocaleString(), icon: <Briefcase size={18} />, color: 'var(--purple-light)' },
            { label: 'Job Sources', value: Object.keys(data.jobs_by_source || {}).length, icon: <Globe size={18} />, color: 'var(--cyan)' },
            { label: 'Categories', value: Object.keys(data.jobs_by_category || {}).length, icon: <Star size={18} />, color: 'var(--orange)' },
            { label: 'Top Skill', value: topSkills[0]?.skill || 'N/A', icon: <TrendingUp size={18} />, color: 'var(--green)' },
          ].map(kpi => (
            <div key={kpi.label} className="analytics-card" style={{ textAlign: 'center' }}>
              <div style={{ color: kpi.color, marginBottom: '0.5rem' }}>{kpi.icon}</div>
              <div className="stat-number" style={{ fontSize: '1.75rem' }}>{kpi.value}</div>
              <div className="stat-label">{kpi.label}</div>
            </div>
          ))}
        </div>

        <div className="analytics-grid">
          {/* Category Bar Chart */}
          <div className="analytics-card" style={{ gridColumn: 'span 2' }}>
            <h3>📂 Jobs by Category</h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={categoryData} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {categoryData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Source Pie Chart */}
          <div className="analytics-card">
            <h3>🌍 Jobs by Source</h3>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={sourceData}
                  cx="50%" cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {sourceData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(val, name) => [`${val} jobs`, name]} contentStyle={{ background: 'rgba(13,13,37,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: '0.8rem' }} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '0.78rem', color: '#94a3b8' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Job Type Pie */}
          <div className="analytics-card">
            <h3>💼 Job Types</h3>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={typeData}
                  cx="50%" cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {typeData.map((_, i) => (
                    <Cell key={i} fill={COLORS[(i + 4) % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(val, name) => [`${val} jobs`, name]} contentStyle={{ background: 'rgba(13,13,37,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: '0.8rem' }} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '0.78rem', color: '#94a3b8' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Top Skills Bar */}
          <div className="analytics-card" style={{ gridColumn: 'span 2' }}>
            <h3>🔧 Top In-Demand Skills</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              {topSkills.slice(0, 12).map((s, i) => (
                <div key={s.skill} className="bar-item">
                  <div className="bar-label">
                    <span style={{ color: 'var(--text-primary)' }}>{s.skill}</span>
                    <span>{s.count} jobs</span>
                  </div>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${(s.count / maxSkill) * 100}%`, background: COLORS[i % COLORS.length] }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Locations */}
          {data.top_locations?.length > 0 && (
            <div className="analytics-card">
              <h3>📍 Top Locations</h3>
              {data.top_locations.slice(0, 8).map((loc, i) => (
                <div key={loc.location} className="bar-item">
                  <div className="bar-label">
                    <span>{loc.location}</span>
                    <span>{loc.count}</span>
                  </div>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${(loc.count / data.top_locations[0].count) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Salary Distribution */}
          {salaryDist.length > 0 && (
            <div className="analytics-card">
              <h3>💰 Salary Distribution</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={salaryDist} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="range" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="count" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Scrape Logs */}
          <div className="analytics-card" style={{ gridColumn: '1 / -1' }}>
            <h3>📋 Recent Scrape Logs</h3>
            {(data.recent_scrape_logs || []).length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No scrape logs yet. Click "Scrape Now" to start.</p>
            ) : (
              data.recent_scrape_logs.map((log, i) => (
                <div key={i} className="log-row">
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)', width: 100 }}>{log.source}</span>
                  <span className={`log-status ${log.status}`}>{log.status}</span>
                  <span style={{ color: 'var(--text-muted)' }}>{log.jobs_scraped} scraped</span>
                  <span style={{ color: 'var(--green)' }}>+{log.jobs_added} new</span>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                    {log.started_at ? new Date(log.started_at).toLocaleString() : ''}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

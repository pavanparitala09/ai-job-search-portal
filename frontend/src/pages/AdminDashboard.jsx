import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Users, Settings, Play, LogOut, Clock, KeyRound, Shield, RefreshCw } from 'lucide-react';
import api from '../api/client';

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [analytics, setAnalytics] = useState(null);
  const [schedule, setSchedule] = useState({ hour: 0, minute: 0, interval_days: 1 });
  const [aiLimit, setAiLimit] = useState(100);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [logs, setLogs] = useState([]);
  
  const [pwForm, setPwForm] = useState({ current: '', new: '' });
  const [pwMsg, setPwMsg] = useState('');
  
  const eventSourceRef = useRef(null);
  const token = localStorage.getItem('admin_token');

  useEffect(() => {
    if (!token) {
      navigate('/admin/login');
      return;
    }
    fetchDashboardData();
    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, [navigate, token]);

  const fetchDashboardData = async () => {
    try {
      const authConfig = { headers: { Authorization: `Bearer ${token}` } };
      const [analyticsRes, scheduleRes, settingsRes] = await Promise.all([
        api.get('/api/admin/analytics', authConfig),
        api.get('/api/admin/schedule', authConfig),
        api.get('/api/admin/settings', authConfig)
      ]);
      setAnalytics(analyticsRes.data);
      setSchedule(scheduleRes.data);
      setAiLimit(settingsRes.data.resume_analyzer_limit || 100);
    } catch (err) {
      if (err.response?.status === 401) {
        localStorage.removeItem('admin_token');
        navigate('/admin/login');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleScheduleUpdate = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/admin/schedule', { 
        hour: parseInt(schedule.hour), 
        minute: parseInt(schedule.minute),
        interval_days: parseInt(schedule.interval_days)
      }, { headers: { Authorization: `Bearer ${token}` } });
      alert('Schedule updated successfully!');
    } catch (err) {
      alert('Failed to update schedule');
    }
  };

  const handleAiLimitUpdate = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/admin/settings', { 
        resume_analyzer_limit: parseInt(aiLimit)
      }, { headers: { Authorization: `Bearer ${token}` } });
      alert('AI Limit updated successfully!');
    } catch (err) {
      alert('Failed to update AI limit');
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/admin/change-password', {
        current_password: pwForm.current,
        new_password: pwForm.new
      }, { headers: { Authorization: `Bearer ${token}` } });
      setPwMsg('Password changed successfully.');
      setPwForm({ current: '', new: '' });
    } catch (err) {
      setPwMsg(err.response?.data?.detail || 'Failed to change password.');
    }
  };

  const handleScrapeNow = async () => {
    try {
      setScraping(true);
      setLogs([]);
      await api.post('/api/admin/scrape', {}, { headers: { Authorization: `Bearer ${token}` } });
      
      if (eventSourceRef.current) eventSourceRef.current.close();
      const sseUrl = `http://localhost:8000/api/admin/scrape-stream?token=${token}`;
      const source = new EventSource(sseUrl);
      
      source.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setLogs(prev => [...prev, data]);
        if (data.status === 'finished' || data.status === 'failed') setScraping(false);
      };
      source.onerror = () => {
        setScraping(false);
        source.close();
      };
      eventSourceRef.current = source;
    } catch (err) {
      alert('Failed to start scraper');
      setScraping(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    navigate('/admin/login');
  };

  if (loading) return <div className="page" style={{ display: 'flex', justifyContent: 'center', paddingTop: '8rem' }}><div className="spinner"></div></div>;

  return (
    <div className="page" style={{ padding: '6rem 5% 2rem 5%', background: 'radial-gradient(ellipse at top right, rgba(124,58,237,0.08) 0%, transparent 60%)' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: 44, height: 44, borderRadius: '12px', background: 'linear-gradient(135deg, rgba(124,58,237,0.2), rgba(6,182,212,0.2))', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(124,58,237,0.3)' }}>
            <Shield size={24} color="var(--purple-light)" />
          </div>
          <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0, letterSpacing: '-0.5px' }}>Admin Dashboard</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: 0 }}>System Management & Analytics</p>
          </div>
        </div>
        
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button onClick={fetchDashboardData} className="btn-secondary" style={{ padding: '0.6rem', borderRadius: '10px' }} title="Refresh">
            <RefreshCw size={18} />
          </button>
          <button onClick={handleLogout} className="btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem', borderRadius: '10px' }}>
            <LogOut size={16} /> Logout
          </button>
        </div>
      </div>

      <div className="analytics-grid" style={{ marginBottom: '2rem' }}>
        {/* API Calls Card */}
        <div className="analytics-card" style={{ background: 'linear-gradient(145deg, rgba(20,20,30,0.8), rgba(10,10,15,0.9))', border: '1px solid rgba(6,182,212,0.15)', boxShadow: '0 10px 30px -10px rgba(0,0,0,0.5)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem', color: 'var(--cyan)' }}>
            <div style={{ padding: '0.5rem', background: 'rgba(6,182,212,0.1)', borderRadius: '8px' }}><Activity size={20} /></div>
            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>External API Calls</h3>
          </div>
          
          <div style={{ marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '1rem' }}>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>AI (Gemini) Usage</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
              <div><span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Today</span><div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{analytics?.api_calls?.gemini?.today || 0}</div></div>
              <div><span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Week</span><div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{analytics?.api_calls?.gemini?.week || 0}</div></div>
              <div><span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Month</span><div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{analytics?.api_calls?.gemini?.month || 0}</div></div>
              <div><span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--purple-light)' }}>Total</span><div style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--purple-light)' }}>{analytics?.api_calls?.gemini?.total || 0}</div></div>
            </div>
          </div>
          
          <div style={{ marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '1rem' }}>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>Web Scrapers Usage</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
              <div><span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Today</span><div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{analytics?.api_calls?.scrapers?.today || 0}</div></div>
              <div><span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Week</span><div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{analytics?.api_calls?.scrapers?.week || 0}</div></div>
              <div><span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Month</span><div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{analytics?.api_calls?.scrapers?.month || 0}</div></div>
              <div><span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--orange)' }}>Total</span><div style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--orange)' }}>{analytics?.api_calls?.scrapers?.total || 0}</div></div>
            </div>
          </div>
          
          <div>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>Combined Total API Calls</h4>
            <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--cyan)', textShadow: '0 0 20px rgba(6,182,212,0.4)' }}>{analytics?.api_calls?.total?.total || 0}</div>
          </div>
        </div>

        {/* Visitors Card */}
        <div className="analytics-card" style={{ background: 'linear-gradient(145deg, rgba(20,20,30,0.8), rgba(10,10,15,0.9))', border: '1px solid rgba(249,115,22,0.15)', boxShadow: '0 10px 30px -10px rgba(0,0,0,0.5)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem', color: 'var(--orange)' }}>
            <div style={{ padding: '0.5rem', background: 'rgba(249,115,22,0.1)', borderRadius: '8px' }}><Users size={20} /></div>
            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Unique Visitors</h3>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
            <div><span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-muted)' }}>Today</span><div style={{ fontSize: '1.75rem', fontWeight: 600 }}>{analytics?.visitors?.today || 0}</div></div>
            <div><span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-muted)' }}>This Week</span><div style={{ fontSize: '1.75rem', fontWeight: 600 }}>{analytics?.visitors?.week || 0}</div></div>
            <div><span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-muted)' }}>This Month</span><div style={{ fontSize: '1.75rem', fontWeight: 600 }}>{analytics?.visitors?.month || 0}</div></div>
            <div><span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-muted)' }}>Total</span><div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--orange)', textShadow: '0 0 20px rgba(249,115,22,0.4)' }}>{analytics?.visitors?.total || 0}</div></div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '2rem' }}>
        
        {/* Controls */}
        <div className="analytics-card" style={{ background: 'rgba(25,25,35,0.95)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 8px 30px rgba(0,0,0,0.6)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem', color: 'var(--text-primary)' }}>
            <div style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}><Settings size={20} color="#fff" /></div>
            <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#fff' }}>Automation Controls</h3>
          </div>
          
          <div style={{ marginBottom: '2.5rem' }}>
            <h4 style={{ fontSize: '0.95rem', marginBottom: '0.5rem', fontWeight: 600 }}>Manual Scrape</h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>Run all job scrapers immediately across all sources.</p>
            
            <button 
              onClick={handleScrapeNow} 
              disabled={scraping} 
              style={{ 
                width: '100%', padding: '0.85rem', borderRadius: '10px', border: 'none',
                background: scraping ? 'var(--bg-lighter)' : 'linear-gradient(135deg, var(--purple), var(--purple-light))',
                color: 'white', fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
                cursor: scraping ? 'not-allowed' : 'pointer', transition: 'all 0.2s',
                boxShadow: scraping ? 'none' : '0 10px 20px -10px rgba(124,58,237,0.6)'
              }}
            >
              {scraping ? <><div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> Extracting Jobs...</> : <><Play size={18} fill="currentColor" /> Start Scraper Now</>}
            </button>
            
            {logs.length > 0 && (
              <div style={{ 
                marginTop: '1rem', background: 'rgba(0,0,0,0.5)', borderRadius: '8px', padding: '1rem', 
                maxHeight: '180px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.8rem', 
                color: 'var(--green)', border: '1px solid rgba(255,255,255,0.05)' 
              }}>
                {logs.map((log, i) => (
                  <div key={i} style={{ marginBottom: '0.25rem', opacity: 0.9 }}>
                    <span style={{ color: 'var(--text-muted)' }}>[{new Date().toLocaleTimeString()}]</span> {log.source}: {log.status} <span style={{ color: 'white' }}>({log.jobs_added} jobs)</span>
                  </div>
                ))}
                {scraping && <div style={{ opacity: 0.5, marginTop: '0.5rem' }}>Listening for live updates...</div>}
              </div>
            )}
          </div>

          <div style={{ paddingTop: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
            <h4 style={{ fontSize: '0.95rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, color: '#fff' }}>
              <Clock size={16} color="var(--purple-light)" /> Scheduled Task Settings
            </h4>
            <form onSubmit={handleScheduleUpdate} style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Run every (Days)</label>
                <input 
                  type="number" min="1" max="30"
                  className="search-input" 
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', color: '#fff' }}
                  value={schedule.interval_days} 
                  onChange={e => setSchedule({...schedule, interval_days: e.target.value})}
                />
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Hour (24h)</label>
                  <input 
                    type="number" min="0" max="23" 
                    value={schedule.hour} 
                    onChange={e => setSchedule({...schedule, hour: e.target.value})}
                    className="search-input" style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', color: '#fff' }}
                  />
                </div>
                <div style={{ paddingBottom: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>:</div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Minute</label>
                  <input 
                    type="number" min="0" max="59" 
                    value={schedule.minute} 
                    onChange={e => setSchedule({...schedule, minute: e.target.value})}
                    className="search-input" style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', color: '#fff' }}
                  />
                </div>
              </div>
              <button type="submit" className="btn-secondary" style={{ width: '100%', padding: '0.85rem', borderRadius: '8px', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', fontWeight: 600 }}>Save Schedule</button>
            </form>
          </div>
        </div>

        {/* System Settings & Account */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          {/* AI Settings */}
          <div className="analytics-card" style={{ background: 'rgba(25,25,35,0.95)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 8px 30px rgba(0,0,0,0.6)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem', color: 'var(--purple-light)' }}>
              <div style={{ padding: '0.5rem', background: 'rgba(124,58,237,0.1)', borderRadius: '8px' }}><Activity size={20} color="var(--purple-light)" /></div>
              <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#fff' }}>AI API Limit</h3>
            </div>
            
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>Limit the number of daily resume analysis requests to prevent unexpected Gemini API costs.</p>
            <form onSubmit={handleAiLimitUpdate} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Daily Gemini Calls Limit</label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input 
                    type="number" required min="0" className="search-input" 
                    style={{ flex: 1, padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', color: '#fff' }}
                    value={aiLimit} onChange={e => setAiLimit(e.target.value)}
                  />
                  <button type="submit" className="btn-secondary" style={{ padding: '0.8rem 1rem', borderRadius: '8px', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', fontWeight: 600 }}>Save</button>
                </div>
              </div>
            </form>
          </div>

          {/* Change Password */}
          <div className="analytics-card" style={{ background: 'rgba(25,25,35,0.95)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 8px 30px rgba(0,0,0,0.6)', height: 'fit-content' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem', color: 'var(--text-primary)' }}>
            <div style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}><KeyRound size={20} color="#fff" /></div>
            <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#fff' }}>Account Security</h3>
          </div>
          
          <form onSubmit={handlePasswordChange} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Current Password</label>
              <input 
                type="password" required className="search-input" 
                style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', color: '#fff' }}
                value={pwForm.current} onChange={e => setPwForm({...pwForm, current: e.target.value})}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>New Password</label>
              <input 
                type="password" required minLength={6} className="search-input" 
                style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', color: '#fff' }}
                value={pwForm.new} onChange={e => setPwForm({...pwForm, new: e.target.value})}
              />
            </div>
            <button type="submit" className="btn-secondary" style={{ padding: '0.85rem', borderRadius: '8px', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', fontWeight: 600 }}>Update Password</button>
            {pwMsg && (
              <div style={{ 
                padding: '0.75rem', borderRadius: '8px', fontSize: '0.85rem', textAlign: 'center',
                background: pwMsg.includes('success') ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                color: pwMsg.includes('success') ? 'var(--green)' : '#ff6b6b' 
              }}>
                {pwMsg}
              </div>
            )}
          </form>
        </div>

        </div>
      </div>
    </div>
  );
}

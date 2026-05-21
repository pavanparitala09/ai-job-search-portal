import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, KeyRound, ArrowRight, User } from 'lucide-react';
import api from '../api/client';

export default function AdminLogin() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const res = await api.post('/api/admin/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      localStorage.setItem('admin_token', res.data.access_token);
      navigate('/admin/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page" style={{ 
      display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '80vh',
      background: 'radial-gradient(circle at center, rgba(124,58,237,0.05) 0%, transparent 70%)'
    }}>
      <div style={{
        maxWidth: '420px', width: '100%',
        background: 'rgba(20, 20, 30, 0.7)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '24px',
        padding: '3rem 2.5rem',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5), inset 0 0 0 1px rgba(255,255,255,0.05)',
        position: 'relative',
        overflow: 'hidden'
      }}>
        {/* Glow effect */}
        <div style={{ position: 'absolute', top: '-50%', left: '-50%', width: '200%', height: '200%', background: 'conic-gradient(from 0deg, transparent 0 340deg, rgba(124,58,237,0.1) 360deg)', animation: 'spin 10s linear infinite', zIndex: -1, pointerEvents: 'none' }} />

        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <div style={{ 
            width: 64, height: 64, borderRadius: '50%', 
            background: 'linear-gradient(135deg, rgba(124,58,237,0.2), rgba(6,182,212,0.2))', 
            border: '1px solid rgba(255,255,255,0.1)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', 
            margin: '0 auto 1.5rem',
            boxShadow: '0 0 20px rgba(124,58,237,0.2)'
          }}>
            <Shield size={32} color="var(--purple-light)" />
          </div>
          <h2 style={{ fontSize: '1.75rem', fontWeight: '700', marginBottom: '0.5rem', letterSpacing: '-0.5px' }}>Admin Portal</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Authenticate to access the control center</p>
        </div>

        {error && (
          <div style={{ 
            background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', 
            color: '#ff6b6b', padding: '0.85rem', borderRadius: '12px', 
            fontSize: '0.85rem', marginBottom: '1.5rem', textAlign: 'center',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem'
          }}>
            <span style={{ fontSize: '1.1rem' }}>⚠️</span> {error}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Username</label>
            <div style={{ position: 'relative' }}>
              <input 
                type="text" 
                placeholder="Enter username"
                value={username} 
                onChange={(e) => setUsername(e.target.value)} 
                required
                style={{ 
                  width: '100%', padding: '0.85rem 1rem 0.85rem 2.75rem',
                  background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '12px', color: 'white', fontSize: '0.95rem',
                  transition: 'all 0.2s', outline: 'none'
                }}
                onFocus={e => e.target.style.borderColor = 'var(--purple-light)'}
                onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
              />
              <User size={18} color="var(--text-muted)" style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)' }} />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Password</label>
            <div style={{ position: 'relative' }}>
              <input 
                type="password" 
                placeholder="••••••••"
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                required
                style={{ 
                  width: '100%', padding: '0.85rem 1rem 0.85rem 2.75rem',
                  background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '12px', color: 'white', fontSize: '0.95rem',
                  transition: 'all 0.2s', outline: 'none'
                }}
                onFocus={e => e.target.style.borderColor = 'var(--purple-light)'}
                onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
              />
              <KeyRound size={18} color="var(--text-muted)" style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)' }} />
            </div>
          </div>

          <button 
            type="submit" 
            disabled={loading} 
            style={{ 
              marginTop: '1rem', width: '100%', padding: '0.9rem',
              background: 'linear-gradient(135deg, var(--purple), var(--purple-light))',
              color: 'white', border: 'none', borderRadius: '12px',
              fontWeight: 600, fontSize: '1rem', cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
              boxShadow: '0 10px 20px -10px rgba(124,58,237,0.5)',
              transition: 'transform 0.2s, filter 0.2s',
              opacity: loading ? 0.7 : 1
            }}
            onMouseOver={e => !loading && (e.currentTarget.style.filter = 'brightness(1.1)')}
            onMouseOut={e => !loading && (e.currentTarget.style.filter = 'brightness(1)')}
            onMouseDown={e => !loading && (e.currentTarget.style.transform = 'scale(0.98)')}
            onMouseUp={e => !loading && (e.currentTarget.style.transform = 'scale(1)')}
          >
            {loading ? <div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} /> : <>Login to Dashboard <ArrowRight size={18} /></>}
          </button>
        </form>
      </div>
      <style>{`
        @keyframes spin {
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

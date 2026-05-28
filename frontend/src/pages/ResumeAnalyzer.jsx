import { useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { analyzeResumeText, analyzeResumeFile } from '../api/client';
import API from '../api/client';
import { FileText, Zap, CheckCircle, Lightbulb, Sparkles, AlertCircle } from 'lucide-react';

function ScoreRing({ score }) {
  const cls = score >= 60 ? 'high' : score >= 30 ? 'mid' : 'low';
  return (
    <div className={`match-score-ring ${cls}`}>
      {score}%
    </div>
  );
}

function ScoreMeter({ score }) {
  const color = score >= 60 ? 'var(--green)' : score >= 30 ? 'var(--orange)' : '#ef4444';
  const label = score >= 70 ? 'Excellent' : score >= 50 ? 'Good' : score >= 30 ? 'Fair' : 'Needs Work';
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{
        fontSize: '4.5rem', fontWeight: 900,
        background: 'linear-gradient(135deg, var(--purple-light), var(--cyan))',
        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        lineHeight: 1,
      }}>
        {score}
      </div>
      <div style={{ fontSize: '1rem', color, fontWeight: 700, marginTop: '0.25rem' }}>{label}</div>
      {/* Progress bar */}
      <div style={{ height: 6, background: 'rgba(255,255,255,0.06)', borderRadius: 100, margin: '0.75rem auto', maxWidth: 200 }}>
        <div style={{ height: '100%', width: `${score}%`, background: color, borderRadius: 100, transition: 'width 1s ease' }} />
      </div>
    </div>
  );
}

export default function ResumeAnalyzer() {
  const [mode, setMode] = useState('file');
  const [resumeText, setResumeText] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [aiStatus, setAiStatus] = useState(null);

  const [letterLoading, setLetterLoading] = useState(false);
  const [activeLetter, setActiveLetter] = useState(null); // { text, jobTitle, company }
  const [letterError, setLetterError] = useState('');

  // Check Gemini status on mount
  useEffect(() => {
    API.get('/api/resume/status')
      .then(r => setAiStatus(r.data))
      .catch(() => {});
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'text/plain': ['.txt'], 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    onDrop: (files) => { if (files[0]) setFile(files[0]); },
  });

  const handleAnalyze = async () => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      let res;
      if (mode === 'text') {
        if (!resumeText.trim()) { setError('Please paste your resume text.'); setLoading(false); return; }
        res = await analyzeResumeText({ resume_text: resumeText, top_n: 10 });
      } else {
        if (!file) { setError('Please upload a PDF or TXT file.'); setLoading(false); return; }
        const form = new FormData();
        form.append('file', file);
        form.append('top_n', '10');
        res = await analyzeResumeFile(form);
      }
      setResult(res.data);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Analysis failed. Make sure the backend is running and has job data.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateCoverLetter = async (jobId, jobTitle, company) => {
    setLetterLoading(true);
    setLetterError('');
    setActiveLetter(null);
    try {
      const res = await API.post('/api/resume/generate-cover-letter', {
        resume_text: result?.resume_text || resumeText,
        job_id: jobId
      });
      setActiveLetter({
        text: res.data.cover_letter,
        jobTitle: res.data.job_title,
        company: res.data.company
      });
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to generate cover letter. Make sure your Groq API key is valid.';
      setLetterError(msg);
    } finally {
      setLetterLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="container">

        {/* Header */}
        <div className="page-header">
          <h1>🤖 Resume <span className="gradient-text">AI Analyzer</span></h1>
          <p>Upload your resume — Groq AI will match it against real scraped jobs, detect skills, and give personalized tips.</p>
        </div>

        {/* AI Status badge */}
        {aiStatus && (
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.35rem 0.9rem', borderRadius: 100,
            background: aiStatus.gemini_ready ? 'rgba(16,185,129,0.12)' : 'rgba(245,158,11,0.12)',
            border: `1px solid ${aiStatus.gemini_ready ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`,
            fontSize: '0.78rem', fontWeight: 600,
            color: aiStatus.gemini_ready ? 'var(--green)' : 'var(--orange)',
            marginBottom: '1.5rem',
          }}>
            {aiStatus.gemini_ready ? <Sparkles size={12} /> : <AlertCircle size={12} />}
            {aiStatus.message}
          </div>
        )}

        {/* Mode toggle */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
          {['file', 'text'].map(m => (
            <button key={m} className={`page-btn ${mode === m ? 'active' : ''}`} onClick={() => setMode(m)}>
              {m === 'file' ? '📎 Upload File' : '📝 Paste Text'}
            </button>
          ))}
        </div>

        <div className="resume-analyzer-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', alignItems: 'start' }}>

          {/* ── Left: Input ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="analytics-card">
              <h3><FileText size={14} /> Your Resume</h3>

              {mode === 'file' ? (
                <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
                  <input {...getInputProps()} />
                  <div className="dropzone-icon">{file ? '✅' : '📄'}</div>
                  <h3>{file ? file.name : 'Drop your resume here'}</h3>
                  <p>
                    {file
                      ? `${(file.size / 1024).toFixed(1)} KB • Click to change`
                      : 'Supports .pdf and .txt • Max 5MB'}
                  </p>
                </div>
              ) : (
                <textarea
                  className="resume-textarea"
                  placeholder={`Paste your full resume here…\n\nExample:\nJohn Doe | john@email.com\n\nSkills: Python, React, MySQL, Docker\n\nExperience:\n- Software Engineer at XYZ (2022-2024)\n  Built REST APIs using Django and FastAPI\n  Deployed services on AWS EC2\n\nEducation: B.Tech CS, 2022`}
                  value={resumeText}
                  onChange={e => setResumeText(e.target.value)}
                  style={{ minHeight: '260px' }}
                />
              )}

              {error && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                  color: '#ef4444', fontSize: '0.85rem', marginTop: '0.5rem',
                  padding: '0.6rem 0.75rem', background: 'rgba(239,68,68,0.08)',
                  borderRadius: 'var(--radius-sm)', border: '1px solid rgba(239,68,68,0.2)',
                }}>
                  <AlertCircle size={14} /> {error}
                </div>
              )}

              <button className="btn-apply" style={{ marginTop: '0.75rem' }} onClick={handleAnalyze} disabled={loading}>
                {loading ? (
                  <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                    <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                    Groq is analyzing…
                  </span>
                ) : (
                  <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                    <Sparkles size={15} /> Analyze with AI
                  </span>
                )}
              </button>
            </div>

            {/* Improvement Tips */}
            {(result?.improvements?.length > 0 || result?.improvement_tips?.length > 0) && (
              <div className="analytics-card">
                <h3><Lightbulb size={14} /> AI Improvement Areas</h3>
                
                {result.improvements?.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', marginTop: '0.5rem' }}>
                    {result.improvements.map((imp, i) => (
                      <div key={i} style={{ padding: '0.75rem', background: 'rgba(255,255,255,0.03)', borderRadius: 'var(--radius-sm)', borderLeft: '2px solid var(--purple-light)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
                          <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--cyan)', fontWeight: 600 }}>{imp.category}</span>
                        </div>
                        <div style={{ fontSize: '0.84rem', color: '#ffb3b3', marginBottom: '0.3rem', fontWeight: 500 }}>
                          <span style={{opacity: 0.8, fontSize: '0.75rem', marginRight: '4px'}}>⚠️ Issue:</span> {imp.issue}
                        </div>
                        <div style={{ fontSize: '0.84rem', color: 'var(--green)', lineHeight: 1.4 }}>
                          <span style={{opacity: 0.8, fontSize: '0.75rem', marginRight: '4px'}}>💡 Fix:</span> {imp.suggestion}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                    {result.improvement_tips.map((tip, i) => (
                      <li key={i} style={{ display: 'flex', gap: '0.5rem', fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                        <span style={{ color: 'var(--purple-light)', flexShrink: 0, marginTop: 2 }}>→</span>
                        {tip}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          {/* ── Right: Results ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {result ? (
              <>
                {/* Fallback warning banner */}
                {result.powered_by === 'TF-IDF' && (
                  <div style={{
                    padding: '1rem',
                    background: 'rgba(245,158,11,0.08)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid rgba(245,158,11,0.3)',
                    color: 'var(--orange)',
                    fontSize: '0.86rem',
                    lineHeight: 1.5,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, marginBottom: '0.4rem' }}>
                      <AlertCircle size={16} /> Running in TF-IDF Fallback Mode
                    </div>
                    {result.gemini_summary === '⚠️ limit_exceeded' ? (
                      <>
                        The daily AI analysis limit set by the administrator has been reached. 
                        As a result, detailed mistakes, improvement suggestions, and professional career summaries are temporarily unavailable. 
                        Please come back tomorrow when the daily limit resets.
                      </>
                    ) : (
                      <>
                        Groq AI was unavailable (check the status badge above for details). 
                        As a result, detailed mistakes, improvement suggestions, and professional career summaries are not available. 
                        The score shown is estimated using basic text-similarity matching against jobs in the database. 
                        Please set a valid <strong>GROQ_API_KEY</strong> in <code>backend/.env</code> to enable full AI capabilities.
                      </>
                    )}
                  </div>
                )}

                {result.gemini_summary !== '⚠️ limit_exceeded' && (
                  <>
                    {/* Score card */}
                <div className="analytics-card" style={{ textAlign: 'center', padding: '1.75rem' }}>
                  <h3 style={{ justifyContent: 'center', marginBottom: '1rem' }}>Resume Score</h3>
                  <ScoreMeter score={result.overall_score} />
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: '0.5rem' }}>
                    Matched against {result.top_matches.length} jobs
                  </p>
                </div>

                {/* Groq summary */}
                {result.gemini_summary && !result.gemini_summary.startsWith('⚠️') && (
                  <div className="analytics-card" style={{ borderColor: 'rgba(124,58,237,0.3)', background: 'rgba(124,58,237,0.06)' }}>
                    <h3><Sparkles size={14} /> Groq Assessment</h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: 1.6 }}>
                      {result.gemini_summary}
                    </p>
                  </div>
                )}

                {/* Detected skills — only if AI returned some */}
                {result.detected_skills?.length > 0 && (
                <div className="analytics-card">
                  <h3><CheckCircle size={14} /> Detected Skills ({result.detected_skills.length})</h3>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                    {result.detected_skills.map(s => <span key={s} className="skill-detected">{s}</span>)}
                  </div>
                </div>
                )}

                {/* Top job matches */}
                <div className="analytics-card">
                  <h3>🎯 Best Job Matches</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '500px', overflowY: 'auto' }}>
                    {result.top_matches.length === 0 ? (
                      <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        No job matches found. Make sure jobs have been scraped first.
                      </p>
                    ) : result.top_matches.map(match => (
                      <div key={match.job_id} className="match-card">
                        <ScoreRing score={match.match_score} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '0.15rem' }}>{match.title}</div>
                          <div style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', marginBottom: '0.4rem' }}>
                            {match.company} {match.location ? `· ${match.location}` : ''}
                          </div>

                          {/* Matched skills */}
                          {match.matched_skills.length > 0 && (
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem', marginBottom: '0.3rem' }}>
                              {match.matched_skills.slice(0, 4).map(s => (
                                <span key={s} className="skill-detected" style={{ fontSize: '0.62rem', padding: '0.1rem 0.4rem' }}>✓ {s}</span>
                              ))}
                            </div>
                          )}

                          {/* Missing skills */}
                          {match.missing_skills.length > 0 && (
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem', marginBottom: '0.3rem' }}>
                              {match.missing_skills.slice(0, 3).map(s => (
                                <span key={s} className="skill-missing" style={{ fontSize: '0.62rem', padding: '0.1rem 0.4rem' }}>✗ {s}</span>
                              ))}
                            </div>
                          )}

                          {/* AI suggestion */}
                          {match.suggestions?.[0] && (
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic', marginBottom: '0.3rem' }}>
                              💡 {match.suggestions[0]}
                            </p>
                          )}

                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '0.5rem' }}>
                            <a href={match.apply_link || '#'} target="_blank" rel="noopener noreferrer"
                              style={{ fontSize: '0.75rem', color: 'var(--purple-light)', textDecoration: 'none', fontWeight: 600 }}>
                              Apply on {match.source} →
                            </a>
                            <button 
                              onClick={() => handleGenerateCoverLetter(match.job_id, match.title, match.company)}
                              style={{
                                display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
                                padding: '0.3rem 0.7rem', borderRadius: 4,
                                background: 'rgba(168,85,247,0.12)', border: '1px solid rgba(168,85,247,0.3)',
                                color: 'var(--purple-light)', fontSize: '0.72rem', fontWeight: 600,
                                cursor: 'pointer', transition: 'all 0.2s ease',
                              }}
                            >
                              📄 Cover Letter
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                  </>
                )}
              </>
            ) : (
              <div className="analytics-card" style={{ textAlign: 'center', padding: '3rem 2rem' }}>
                <div style={{ fontSize: '3.5rem', marginBottom: '1rem' }}>🤖</div>
                <h3 style={{ marginBottom: '0.5rem' }}>Ready to Analyze</h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', lineHeight: 1.6 }}>
                  {aiStatus?.gemini_ready
                    ? 'Groq AI is ready. Upload your resume or paste the text, then click "Analyze with AI".'
                    : 'Upload your resume to get started. Add your Groq API key in backend/.env for better results.'}
                </p>
              </div>
            )}
          </div>
        </div>
        {/* Cover Letter Modal */}
        {(letterLoading || activeLetter || letterError) && (
          <div className="modal-overlay" style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center',
            justifyContent: 'center', zIndex: 1000, padding: '1rem',
          }}>
            <div className="analytics-card" style={{
              maxWidth: '650px', width: '100%', maxHeight: '90vh',
              display: 'flex', flexDirection: 'column', gap: '1rem',
              boxShadow: '0 20px 25px -5px rgba(0,0,0,0.5)',
              border: '1px solid rgba(255,255,255,0.1)',
              background: '#121214',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '0.75rem' }}>
                <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  📄 AI Cover Letter Generator
                </h3>
                <button 
                  onClick={() => { setActiveLetter(null); setLetterLoading(false); setLetterError(''); }}
                  style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '1.2rem', cursor: 'pointer' }}
                >
                  ✕
                </button>
              </div>

              {letterLoading && (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', padding: '3rem 0' }}>
                  <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3 }} />
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Groq AI is writing your cover letter...</p>
                </div>
              )}

              {letterError && (
                <div style={{ padding: '2rem 1rem', textAlign: 'center' }}>
                  <p style={{ color: '#ef4444', marginBottom: '1rem', fontSize: '0.9rem' }}>⚠️ {letterError}</p>
                  <button 
                    className="page-btn" 
                    onClick={() => { setActiveLetter(null); setLetterLoading(false); setLetterError(''); }}
                  >
                    Close
                  </button>
                </div>
              )}

              {activeLetter && (
                <>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Tailored for <strong>{activeLetter.jobTitle}</strong> at <strong>{activeLetter.company}</strong>
                  </div>
                  <textarea
                    style={{
                      width: '100%', minHeight: '320px', flex: 1,
                      background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)',
                      borderRadius: 'var(--radius-sm)', padding: '0.75rem', color: 'var(--text-primary)',
                      fontSize: '0.86rem', lineHeight: 1.6, fontFamily: 'monospace',
                      resize: 'none',
                    }}
                    value={activeLetter.text}
                    onChange={(e) => setActiveLetter({ ...activeLetter, text: e.target.value })}
                  />
                  <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'end', marginTop: '0.5rem' }}>
                    <button 
                      className="page-btn"
                      onClick={() => {
                        navigator.clipboard.writeText(activeLetter.text);
                        alert("Cover letter copied to clipboard!");
                      }}
                    >
                      📋 Copy
                    </button>
                    <button 
                      className="page-btn"
                      onClick={() => {
                        const element = document.createElement("a");
                        const file = new Blob([activeLetter.text], { type: 'text/plain' });
                        element.href = URL.createObjectURL(file);
                        element.download = `Cover_Letter_${activeLetter.company.replace(/\s+/g, '_')}.txt`;
                        document.body.appendChild(element);
                        element.click();
                        document.body.removeChild(element);
                      }}
                      style={{ background: 'var(--purple-gradient)', color: 'white', border: 'none' }}
                    >
                      📥 Download .txt
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

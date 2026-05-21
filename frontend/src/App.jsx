import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import Jobs from './pages/Jobs';
import ResumeAnalyzer from './pages/ResumeAnalyzer';
import Analytics from './pages/Analytics';

import AdminLogin from './pages/AdminLogin';
import AdminDashboard from './pages/AdminDashboard';

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/resume" element={<ResumeAnalyzer />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin/dashboard" element={<AdminDashboard />} />
        <Route path="*" element={
          <div className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div className="empty-state">
              <div className="empty-state-icon">🔍</div>
              <h3>404 — Page Not Found</h3>
            </div>
          </div>
        } />
      </Routes>
    </BrowserRouter>
  );
}

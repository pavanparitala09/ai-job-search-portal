import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Menu, X } from 'lucide-react';

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);

  const closeMenu = () => setMenuOpen(false);

  return (
    <nav className="navbar">
      <NavLink to="/" className="navbar-logo" onClick={closeMenu}>
        ⚡ JobPortal AI
      </NavLink>

      {/* Desktop links */}
      <div className="navbar-links desktop-links">
        <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>Home</NavLink>
        <NavLink to="/jobs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>Jobs</NavLink>
        <NavLink to="/resume" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>Resume AI</NavLink>
        <NavLink to="/analytics" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>Analytics</NavLink>
      </div>

      {/* Mobile hamburger */}
      <button
        className="hamburger-btn"
        onClick={() => setMenuOpen(prev => !prev)}
        aria-label="Toggle menu"
      >
        {menuOpen ? <X size={22} /> : <Menu size={22} />}
      </button>

      {/* Mobile dropdown */}
      {menuOpen && (
        <div className="mobile-menu">
          <NavLink to="/" end className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`} onClick={closeMenu}>🏠 Home</NavLink>
          <NavLink to="/jobs" className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`} onClick={closeMenu}>💼 Jobs</NavLink>
          <NavLink to="/resume" className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`} onClick={closeMenu}>🤖 Resume AI</NavLink>
          <NavLink to="/analytics" className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`} onClick={closeMenu}>📊 Analytics</NavLink>
        </div>
      )}
    </nav>
  );
}

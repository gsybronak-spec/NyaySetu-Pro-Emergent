import { NavLink } from 'react-router-dom'

const navItems = [
  { label: 'Dashboard', path: '/dashboard', icon: '📊', enabled: true },
  { label: 'Users', path: '/users', icon: '👥', enabled: false },
  { label: 'Cases', path: '/cases', icon: '📋', enabled: false },
  { label: 'Templates', path: '/templates', icon: '📄', enabled: true },
  { label: 'Case Forms', path: '/case-forms', icon: '📝', enabled: true },
  { label: 'Catalog', path: '/catalog', icon: '📚', enabled: false },
  { label: 'Plans', path: '/plans', icon: '💳', enabled: false },
  { label: 'Settings', path: '/settings', icon: '⚙️', enabled: false },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-logo">⚖️</div>
        <div>
          <div className="sidebar-title">NyaySetu Pro</div>
          <div className="sidebar-subtitle">Admin Portal</div>
        </div>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          item.enabled ? (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            >
              <span className="sidebar-icon">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ) : (
            <div key={item.path} className="sidebar-link disabled" title="Coming Soon">
              <span className="sidebar-icon">{item.icon}</span>
              <span>{item.label}</span>
              <span className="coming-soon-badge">Soon</span>
            </div>
          )
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className="sidebar-version">v1.0.0</div>
      </div>
    </aside>
  )
}

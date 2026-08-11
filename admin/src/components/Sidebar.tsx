import { NavLink } from 'react-router-dom'

const navItems = [
  { label: 'Dashboard', path: '/dashboard', icon: '📊' },
  { label: 'Users', path: '/users', icon: '👥' },
  { label: 'Cases', path: '/cases', icon: '📋' },
  { label: 'Templates', path: '/templates', icon: '📄' },
  { label: 'Case Forms', path: '/case-forms', icon: '📝' },
  { label: 'Catalog', path: '/catalog', icon: '📚' },
  { label: 'Plans', path: '/plans', icon: '💳' },
  { label: 'Audit Logs', path: '/audit-logs', icon: '🛡️' },
  { label: 'Settings', path: '/settings', icon: '⚙️' },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img className="sidebar-logo" src="/nyaysetu-logo.png" alt="NyaySetu Pro" />
        <div>
          <div className="sidebar-title">NyaySetu Pro</div>
          <div className="sidebar-subtitle">Admin Portal</div>
        </div>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
          >
            <span className="sidebar-icon">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className="sidebar-version">v1.0.0</div>
      </div>
    </aside>
  )
}

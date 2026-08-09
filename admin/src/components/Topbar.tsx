import { useAdminAuth } from '../lib/auth'
import { useNavigate } from 'react-router-dom'

export default function Topbar() {
  const { admin, logout } = useAdminAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <header className="topbar">
      <div className="topbar-left">
        <h2 className="topbar-page-title">Admin Dashboard</h2>
      </div>
      <div className="topbar-right">
        {admin && (
          <div className="topbar-user">
            <div className="topbar-avatar">
              {(admin.name || admin.email).charAt(0).toUpperCase()}
            </div>
            <div className="topbar-user-info">
              <div className="topbar-user-name">{admin.name || 'Admin'}</div>
              <div className="topbar-user-role">{admin.role === 'super_admin' ? 'Super Admin' : 'Admin'}</div>
            </div>
            <button className="topbar-logout-btn" onClick={handleLogout}>
              Logout
            </button>
          </div>
        )}
      </div>
    </header>
  )
}

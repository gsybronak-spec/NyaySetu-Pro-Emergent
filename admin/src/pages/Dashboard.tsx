import React, { useEffect, useState } from 'react'
import StatCard from '../components/StatCard'
import { adminApi } from '../lib/api'

interface DashboardStats {
  total_users: number;
  recent_users_30d: number;
  total_cases: number;
  total_documents_generated: number;
  total_credits_consumed: number;
  total_transactions: number;
  recent_users: Array<{
    id: string;
    name: string | null;
    mobile: string | null;
    email: string | null;
    created_at: string;
    provider: string;
  }>;
  recent_applications: Array<{
    id: string;
    user_id: string;
    template_name: string;
    language: string;
    format: string;
    created_at: string;
  }>;
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi.dashboardStats()
      .then(setStats)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error">
        <p>Failed to load dashboard: {error}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <p className="dashboard-desc">Overview of NyaySetu Pro platform activity</p>
      </div>

      <div className="stats-grid">
        <StatCard icon="👥" label="Total Users" value={stats.total_users} color="#0B1B3D" />
        <StatCard icon="📅" label="New Users (30d)" value={stats.recent_users_30d} color="#C5A059" />
        <StatCard icon="📋" label="Total Cases" value={stats.total_cases} color="#1E4620" />
        <StatCard icon="📄" label="Documents Generated" value={stats.total_documents_generated} color="#112240" />
        <StatCard icon="🎫" label="Credits Consumed" value={stats.total_credits_consumed} color="#8C6A29" />
        <StatCard icon="💳" label="Transactions" value={stats.total_transactions} color="#7A1C1C" />
      </div>

      <div className="dashboard-tables">
        <div className="dashboard-table-card">
          <h3>Recent Users</h3>
          {stats.recent_users.length === 0 ? (
            <p className="no-data">No users yet</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Contact</th>
                  <th>Provider</th>
                  <th>Joined</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.name || '—'}</td>
                    <td>{u.mobile || u.email || '—'}</td>
                    <td><span className={`badge badge-${u.provider}`}>{u.provider}</span></td>
                    <td>{u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="dashboard-table-card">
          <h3>Recent Documents</h3>
          {stats.recent_applications.length === 0 ? (
            <p className="no-data">No documents generated yet</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Template</th>
                  <th>Language</th>
                  <th>Format</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_applications.map((a) => (
                  <tr key={a.id}>
                    <td>{a.template_name}</td>
                    <td><span className={`badge badge-lang-${a.language}`}>{a.language === 'gu' ? 'ગુજરાતી' : 'English'}</span></td>
                    <td><span className="badge">{a.format.toUpperCase()}</span></td>
                    <td>{a.created_at ? new Date(a.created_at).toLocaleDateString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

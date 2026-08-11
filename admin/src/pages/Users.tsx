import React, { useEffect, useState, useCallback } from 'react'
import { adminApi } from '../lib/api'

interface AdminUser {
  id: string;
  name: string | null;
  mobile: string | null;
  email: string | null;
  provider: string | null;
  language_pref?: string;
  theme_pref?: string;
  referral_code?: string | null;
  referred_by?: string | null;
  created_at?: string;
  last_login?: string;
  active?: boolean;
  disabled_at?: string | null;
}

interface UserDetail {
  user: AdminUser;
  wallet: { balance?: number; total_used?: number } | null;
  cases_count: number;
  applications_count: number;
  transactions_count: number;
}

export default function Users() {
  const [items, setItems] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [detail, setDetail] = useState<UserDetail | null>(null);
  const [detailError, setDetailError] = useState('');
  const [actingId, setActingId] = useState<string | null>(null);
  const [actingError, setActingError] = useState('');

  const load = useCallback((query?: string) => {
    setLoading(true);
    setError('');
    adminApi.listUsers(query)
      .then((res) => {
        setItems(res.items || []);
        setTotal(res.total || 0);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const openDetail = (id: string) => {
    setDetailError('');
    setDetail(null);
    adminApi.getUser(id)
      .then(setDetail)
      .catch((err) => setDetailError(err.message));
  };

  const toggleStatus = async (u: AdminUser) => {
    setActingId(u.id);
    setActingError('');
    const next = !(u.active !== false);
    try {
      await adminApi.setUserStatus(u.id, next);
      setItems((prev) => prev.map((x) => (x.id === u.id ? { ...x, active: next, disabled_at: next ? null : new Date().toISOString() } : x)));
      if (detail && detail.user.id === u.id) {
        setDetail({ ...detail, user: { ...detail.user, active: next, disabled_at: next ? null : new Date().toISOString() } });
      }
    } catch (err: any) {
      setActingError(err.message || 'Failed to update user status');
    } finally {
      setActingId(null);
    }
  };

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setQ(searchInput.trim());
    load(searchInput.trim());
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Users</h1>
        <p className="dashboard-desc">
          {total} platform user{total === 1 ? '' : 's'} · disable accounts to block login and API access
        </p>
      </div>

      <form className="users-search" onSubmit={submitSearch}>
        <input
          type="text"
          placeholder="Search by name, mobile, email or ID…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <button type="submit">Search</button>
        {q && <button type="button" className="btn-ghost" onClick={() => { setQ(''); setSearchInput(''); load(); }}>Clear</button>}
      </form>

      {actingError && <p className="form-error">{actingError}</p>}
      {error && (
        <div className="dashboard-error">
          <p>Failed to load users: {error}</p>
          <button onClick={() => load(q)}>Retry</button>
        </div>
      )}

      {loading ? (
        <div className="dashboard-loading"><div className="spinner"></div><p>Loading users…</p></div>
      ) : (
        <div className="dashboard-table-card">
          {items.length === 0 ? (
            <p className="no-data">{q ? `No users match "${q}"` : 'No users yet'}</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Contact</th>
                  <th>Provider</th>
                  <th>Joined</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((u) => {
                  const active = u.active !== false;
                  return (
                    <tr key={u.id}>
                      <td>
                        <button className="link-btn" onClick={() => openDetail(u.id)}>{u.name || '—'}</button>
                      </td>
                      <td>{u.mobile || u.email || '—'}</td>
                      <td>{u.provider ? <span className={`badge badge-${u.provider}`}>{u.provider}</span> : '—'}</td>
                      <td>{u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</td>
                      <td>
                        <span className={`badge ${active ? 'badge-active' : 'badge-disabled'}`}>
                          {active ? 'Active' : 'Disabled'}
                        </span>
                      </td>
                      <td>
                        <button
                          className={`btn-small ${active ? 'btn-danger' : 'btn-success'}`}
                          disabled={actingId === u.id}
                          onClick={() => toggleStatus(u)}
                        >
                          {actingId === u.id ? '…' : active ? 'Disable' : 'Enable'}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {detail && (
        <div className="dashboard-table-card user-detail">
          <div className="user-detail-header">
            <h3>{detail.user.name || 'Unnamed user'}</h3>
            <span className={`badge ${detail.user.active !== false ? 'badge-active' : 'badge-disabled'}`}>
              {detail.user.active !== false ? 'Active' : 'Disabled'}
            </span>
          </div>
          <div className="user-detail-grid">
            <div><strong>Mobile</strong><span>{detail.user.mobile || '—'}</span></div>
            <div><strong>Email</strong><span>{detail.user.email || '—'}</span></div>
            <div><strong>Provider</strong><span>{detail.user.provider || '—'}</span></div>
            <div><strong>Referral code</strong><span>{detail.user.referral_code || '—'}</span></div>
            <div><strong>Joined</strong><span>{detail.user.created_at ? new Date(detail.user.created_at).toLocaleString() : '—'}</span></div>
            <div><strong>Disabled at</strong><span>{detail.user.disabled_at ? new Date(detail.user.disabled_at).toLocaleString() : '—'}</span></div>
          </div>
          <div className="user-detail-stats">
            <div><strong>{detail.wallet?.balance ?? 0}</strong><span>Wallet credits</span></div>
            <div><strong>{detail.cases_count}</strong><span>Cases</span></div>
            <div><strong>{detail.applications_count}</strong><span>Documents</span></div>
            <div><strong>{detail.transactions_count}</strong><span>Transactions</span></div>
            <div><strong>{detail.wallet?.total_used ?? 0}</strong><span>Credits used</span></div>
          </div>
          <div className="user-detail-actions">
            <button
              className={`btn-small ${detail.user.active !== false ? 'btn-danger' : 'btn-success'}`}
              disabled={actingId === detail.user.id}
              onClick={() => toggleStatus(detail.user)}
            >
              {actingId === detail.user.id ? '…' : detail.user.active !== false ? 'Disable account' : 'Enable account'}
            </button>
          </div>
        </div>
      )}
      {detailError && <p className="form-error">{detailError}</p>}
    </div>
  )
}

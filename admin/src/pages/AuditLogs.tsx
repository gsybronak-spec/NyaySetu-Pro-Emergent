import React, { useEffect, useState, useCallback } from 'react'
import { adminApi } from '../lib/api'

interface AuditEntry {
  id: string;
  admin_id: string | null;
  admin_email: string | null;
  admin_role: string | null;
  action: string;
  target: string | null;
  metadata: Record<string, unknown>;
  timestamp: string;
}

const ACTION_LABELS: Record<string, string> = {
  admin_login: 'Admin login',
  admin_login_failed: 'Login failed',
  template_create: 'Template created',
  template_update: 'Template updated',
  template_publish: 'Template published',
  template_archive: 'Template archived',
  template_clone: 'Template cloned',
  case_form_save: 'Case form saved',
  user_status_update: 'User status changed',
  case_archive: 'Case archived',
  case_restore: 'Case restored',
  plan_create: 'Plan created',
  plan_update: 'Plan updated',
  plan_status_update: 'Plan status changed',
};

export default function AuditLogs() {
  const [items, setItems] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [actionFilter, setActionFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback((action?: string) => {
    setLoading(true);
    setError('');
    adminApi.listAuditLogs({ action: action || undefined, limit: 100 })
      .then((res) => {
        setItems(res.items || []);
        setTotal(res.total || 0);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const actions = ['', ...Object.keys(ACTION_LABELS)];

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Audit Logs</h1>
        <p className="dashboard-desc">
          {total} recorded admin action{total === 1 ? '' : 's'} · immutable append-only trail
        </p>
      </div>

      <div className="audit-filters">
        <select value={actionFilter} onChange={(e) => { setActionFilter(e.target.value); load(e.target.value); }}>
          {actions.map((a) => (
            <option key={a} value={a}>{a ? ACTION_LABELS[a] : 'All actions'}</option>
          ))}
        </select>
      </div>

      {error && (
        <div className="dashboard-error">
          <p>Failed to load audit logs: {error}</p>
          <button onClick={() => load(actionFilter)}>Retry</button>
        </div>
      )}

      {loading ? (
        <div className="dashboard-loading"><div className="spinner"></div><p>Loading audit logs…</p></div>
      ) : (
        <div className="dashboard-table-card">
          {items.length === 0 ? (
            <p className="no-data">No audit entries{actionFilter ? ' for this action' : ''} yet</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Action</th>
                  <th>Admin</th>
                  <th>Target</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {items.map((e) => (
                  <tr key={e.id}>
                    <td>{e.timestamp ? new Date(e.timestamp).toLocaleString() : '—'}</td>
                    <td>
                      <span className="badge badge-audit">{ACTION_LABELS[e.action] || e.action}</span>
                    </td>
                    <td>{e.admin_email || e.admin_id || 'system'}</td>
                    <td>{e.target || '—'}</td>
                    <td className="audit-meta">
                      {Object.entries(e.metadata || {})
                        .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
                        .join(' · ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}

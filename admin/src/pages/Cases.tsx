import React, { useEffect, useState, useCallback, Component, ErrorInfo, ReactNode } from 'react'
import { adminApi } from '../lib/api'

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class CaseErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Cases ErrorBoundary caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '32px', textAlign: 'center' }}>
          <div style={{ backgroundColor: '#fee2e2', border: '1px solid #ef4444', borderRadius: '8px', padding: '24px', maxWidth: '600px', margin: '0 auto', color: '#991b1b' }}>
            <h3 style={{ margin: '0 0 8px 0', fontSize: '18px' }}>Something went wrong loading Cases</h3>
            <p style={{ margin: '0 0 16px 0', fontSize: '14px' }}>{this.state.error?.message || 'An unexpected rendering error occurred.'}</p>
            <button
              onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload(); }}
              style={{ padding: '8px 16px', backgroundColor: '#dc2626', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}
            >
              Reload Cases
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

interface CaseOwner {
  id: string;
  name?: string | null;
  mobile?: string | null;
  email?: string | null;
  provider?: string | null;
  active?: boolean;
}

interface AdminCase {
  id: string;
  nickname?: string | null;
  case_number?: string | null;
  case_type_id?: string | null;
  case_type_label?: string | null;
  category?: string;
  party_name?: string | null;
  opposite_party?: string | null;
  client_name?: string | null;
  client_mobile?: string | null;
  court_label?: string | null;
  district_label?: string | null;
  police_station_label?: string | null;
  law_label?: string | null;
  section_label?: string | null;
  status?: string;
  created_at?: string;
  updated_at?: string;
  application_count?: number;
  owner?: CaseOwner | null;
}

interface ApplicationRecord {
  id: string;
  template_name: string;
  language: string;
  format: string;
  filename: string;
  created_at?: string;
}

interface CaseDetail {
  case: AdminCase & { custom_fields?: Record<string, unknown>; notes?: string | null };
  owner: CaseOwner | null;
  applications: ApplicationRecord[];
}

export const CATEGORIES = ['All', 'Civil', 'Criminal', 'Other'];

function CasesInner() {
  const [items, setItems] = useState<AdminCase[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [detailError, setDetailError] = useState('');
  const [actingId, setActingId] = useState<string | null>(null);
  const [actingError, setActingError] = useState('');

  const load = useCallback((params?: { q?: string; status?: string; category?: string }) => {
    setLoading(true);
    setError('');
    adminApi.listCases({
      q: params?.q ?? undefined,
      status: params?.status ?? statusFilter,
      category: params?.category !== 'All' ? params?.category : undefined,
    })
      .then((res) => {
        setItems(res.items || []);
        setTotal(res.total || 0);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  const openDetail = (id?: string | null) => {
    if (!id) return;
    setDetailError('');
    setDetail(null);
    adminApi.getCase(id)
      .then((res) => setDetail(res))
      .catch((err) => setDetailError(err.message));
  };

  const toggleArchive = async (c: AdminCase) => {
    if (!c.id) return;
    setActingId(c.id);
    setActingError('');
    const isArchived = c.status === 'archived';
    const action = isArchived ? 'restore' : 'archive';
    try {
      await adminApi[action === 'archive' ? 'archiveCase' : 'restoreCase'](c.id);
      setItems((prev) => prev.map((x) => (x.id === c.id ? { ...x, status: isArchived ? 'active' : 'archived' } : x)));
      if (detail && detail.case.id === c.id) {
        setDetail({ ...detail, case: { ...detail.case, status: isArchived ? 'active' : 'archived' } });
      }
    } catch (err: any) {
      setActingError(err.message || `Failed to ${action} case`);
    } finally {
      setActingId(null);
    }
  };

  const deleteCase = async (c: AdminCase) => {
    if (!c.id) return;
    const docCount = c.application_count ?? (detail && detail.case.id === c.id ? detail.applications.length : 0);
    if (docCount > 0) {
      alert(`Deletion Protected:\n\nThis case has ${docCount} linked document(s). Cases with document history cannot be deleted to preserve legal and audit records.\n\nPlease archive the case instead.`);
      return;
    }
    const label = c.nickname || c.case_number || c.case_type_label || (c.id ? c.id.slice(0, 8) : 'Case');
    if (!window.confirm(`Are you sure you want to permanently delete case "${label}"?\n\nThis action cannot be undone.`)) {
      return;
    }
    setActingId(c.id);
    setActingError('');
    try {
      await adminApi.deleteCase(c.id);
      setItems((prev) => prev.filter((x) => x.id !== c.id));
      setTotal((prev) => Math.max(0, prev - 1));
      if (detail && detail.case.id === c.id) {
        setDetail(null);
      }
    } catch (err: any) {
      setActingError(err.message || 'Failed to delete case');
    } finally {
      setActingId(null);
    }
  };

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setQ(searchInput.trim());
    load({ q: searchInput.trim(), status: statusFilter, category: categoryFilter });
  };

  const applyStatus = (s: string) => {
    setStatusFilter(s);
    load({ q, status: s, category: categoryFilter });
  };

  const applyCategory = (c: string) => {
    setCategoryFilter(c);
    load({ q, status: statusFilter, category: c });
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Cases</h1>
        <p className="dashboard-desc">
          {total} case{total === 1 ? '' : 's'} across all advocates · archive/restore preserves data
        </p>
      </div>

      <form className="users-search" onSubmit={submitSearch}>
        <input
          type="text"
          placeholder="Search by nickname, case number, party, client or mobile…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <button type="submit">Search</button>
        {q && (
          <button type="button" className="btn-ghost" onClick={() => { setQ(''); setSearchInput(''); setCategoryFilter('All'); setStatusFilter('all'); load({}); }}>
            Clear
          </button>
        )}
      </form>

      <div className="audit-filters cases-filters">
        <select value={statusFilter} onChange={(e) => applyStatus(e.target.value)}>
          <option value="all">All statuses</option>
          <option value="active">Active</option>
          <option value="archived">Archived</option>
        </select>
        <select value={categoryFilter} onChange={(e) => applyCategory(e.target.value)}>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c === 'All' ? 'All categories' : c}</option>)}
        </select>
      </div>

      {actingError && <p className="form-error">{actingError}</p>}
      {error && (
        <div className="dashboard-error">
          <p>Failed to load cases: {error}</p>
          <button onClick={() => load({ q, status: statusFilter, category: categoryFilter })}>Retry</button>
        </div>
      )}

      {loading ? (
        <div className="dashboard-loading"><div className="spinner"></div><p>Loading cases…</p></div>
      ) : (
        <div className="dashboard-table-card">
          {items.length === 0 ? (
            <p className="no-data">{q ? `No cases match "${q}"` : 'No cases yet'}</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Client / Party</th>
                  <th>Type</th>
                  <th>Court / District</th>
                  <th>Advocate</th>
                  <th>Docs</th>
                  <th>Status</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((c, idx) => {
                  const archived = c.status === 'archived';
                  const caseId = c.id || `case-${idx}`;
                  const docCount = c.application_count ?? 0;
                  return (
                    <tr key={caseId}>
                      <td>
                        <button className="link-btn" onClick={() => c.id && openDetail(c.id)}>
                          {c.nickname || c.case_number || c.case_type_label || (c.id ? c.id.slice(0, 8) : `Case #${idx + 1}`)}
                        </button>
                        {c.case_number && <div className="case-sub">{c.case_number}</div>}
                      </td>
                      <td>
                        {c.client_name || c.party_name || '—'}
                        {c.client_mobile && <div className="case-sub">{c.client_mobile}</div>}
                      </td>
                      <td>
                        {c.case_type_label || '—'}
                        <div className="case-sub">{c.category || ''}</div>
                      </td>
                      <td>
                        {c.court_label || '—'}
                        {c.district_label && <div className="case-sub">{c.district_label}</div>}
                      </td>
                      <td>{c.owner?.name || c.owner?.mobile || '—'}</td>
                      <td>
                        <span className="badge" style={{ backgroundColor: docCount > 0 ? '#e0f2fe' : '#f1f5f9', color: docCount > 0 ? '#0369a1' : '#64748b' }}>
                          {docCount}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${archived ? 'badge-disabled' : 'badge-active'}`}>
                          {archived ? 'Archived' : 'Active'}
                        </span>
                      </td>
                      <td>{c.updated_at ? new Date(c.updated_at).toLocaleDateString() : '—'}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                          <button
                            className={`btn-small ${archived ? 'btn-success' : 'btn-danger'}`}
                            disabled={actingId === c.id}
                            onClick={() => toggleArchive(c)}
                          >
                            {actingId === c.id ? '…' : archived ? 'Restore' : 'Archive'}
                          </button>
                          <button
                            className="btn-small"
                            style={{
                              backgroundColor: docCount > 0 ? '#f8fafc' : '#fee2e2',
                              color: docCount > 0 ? '#94a3b8' : '#ef4444',
                              border: '1px solid',
                              borderColor: docCount > 0 ? '#e2e8f0' : '#fca5a5',
                              cursor: docCount > 0 ? 'not-allowed' : 'pointer',
                              padding: '2px 8px',
                              fontSize: '11px',
                            }}
                            disabled={actingId === c.id || docCount > 0}
                            title={docCount > 0 ? 'Cannot delete case with generated documents' : 'Permanently delete case'}
                            onClick={() => deleteCase(c)}
                          >
                            Delete
                          </button>
                        </div>
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
        <div className="dashboard-table-card user-detail" style={{ marginTop: '24px' }}>
          <div className="user-detail-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h3 style={{ margin: 0 }}>{detail.case.nickname || detail.case.case_number || detail.case.case_type_label || 'Case Detail'}</h3>
              <span className={`badge ${detail.case.status === 'archived' ? 'badge-disabled' : 'badge-active'}`}>
                {detail.case.status === 'archived' ? 'Archived' : 'Active'}
              </span>
            </div>
            <button className="btn-small btn-ghost" onClick={() => setDetail(null)} title="Close detail">
              ✕ Close
            </button>
          </div>

          <div className="user-detail-grid">
            <div><strong>Case number</strong><span>{detail.case.case_number || '—'}</span></div>
            <div><strong>Case type</strong><span>{detail.case.case_type_label || '—'}</span></div>
            <div><strong>Category</strong><span>{detail.case.category || '—'}</span></div>
            <div><strong>Court</strong><span>{detail.case.court_label || '—'}</span></div>
            <div><strong>District</strong><span>{detail.case.district_label || '—'}</span></div>
            <div><strong>Police station</strong><span>{detail.case.police_station_label || '—'}</span></div>
            <div><strong>Law / Section</strong><span>{[detail.case.law_label, detail.case.section_label].filter(Boolean).join(' / ') || '—'}</span></div>
            <div><strong>Party</strong><span>{detail.case.party_name || '—'}</span></div>
            <div><strong>Opposite party</strong><span>{detail.case.opposite_party || '—'}</span></div>
            <div><strong>Client</strong><span>{[detail.case.client_name, detail.case.client_mobile].filter(Boolean).join(' · ') || '—'}</span></div>
            <div><strong>Created</strong><span>{detail.case.created_at ? new Date(detail.case.created_at).toLocaleString() : '—'}</span></div>
            <div><strong>Updated</strong><span>{detail.case.updated_at ? new Date(detail.case.updated_at).toLocaleString() : '—'}</span></div>
          </div>

          {detail.owner && (
            <div className="user-detail-grid">
              <div><strong>Advocate</strong><span>{detail.owner.name || '—'}</span></div>
              <div><strong>Mobile</strong><span>{detail.owner.mobile || '—'}</span></div>
              <div><strong>Email</strong><span>{detail.owner.email || '—'}</span></div>
              <div><strong>Bar council no</strong><span>{(detail.owner as any).bar_council_no || '—'}</span></div>
            </div>
          )}

          {detail.case.custom_fields && Object.keys(detail.case.custom_fields).length > 0 && (
            <div className="user-detail-grid">
              {Object.entries(detail.case.custom_fields).map(([k, v]) => (
                <div key={k}><strong>{k}</strong><span>{String(v ?? '—')}</span></div>
              ))}
            </div>
          )}

          <div className="user-detail-stats">
            <div><strong>{detail.applications.length}</strong><span>Documents</span></div>
          </div>

          {detail.applications.length > 0 && (
            <div style={{
              backgroundColor: '#fffbeb',
              border: '1px solid #fde68a',
              borderRadius: '6px',
              padding: '12px 16px',
              margin: '16px 0',
              fontSize: '13px',
              color: '#92400e',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
            }}>
              <span style={{ fontSize: '18px' }}>⚠️</span>
              <div>
                <strong>Deletion Blocked:</strong> This case has <strong>{detail.applications.length}</strong> generated document{detail.applications.length > 1 ? 's' : ''}. Cases with document history cannot be deleted in order to preserve legal and audit records. You can archive the case instead.
              </div>
            </div>
          )}

          <h4 className="case-docs-title">Generated Documents</h4>
          {detail.applications.length === 0 ? (
            <p className="no-data">No documents generated for this case</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Template</th>
                  <th>Language</th>
                  <th>Format</th>
                  <th>Filename</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {detail.applications.map((a) => (
                  <tr key={a.id}>
                    <td>{a.template_name}</td>
                    <td>{a.language === 'gu' ? 'ગુજરાતી' : 'English'}</td>
                    <td><span className="badge">{a.format.toUpperCase()}</span></td>
                    <td>{a.filename}</td>
                    <td>{a.created_at ? new Date(a.created_at).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div className="user-detail-actions" style={{ display: 'flex', gap: '10px', alignItems: 'center', marginTop: '16px' }}>
            <button
              className={`btn-small ${detail.case.status === 'archived' ? 'btn-success' : 'btn-danger'}`}
              disabled={actingId === detail.case.id}
              onClick={() => toggleArchive(detail.case)}
            >
              {actingId === detail.case.id ? '…' : detail.case.status === 'archived' ? 'Restore case' : 'Archive case'}
            </button>
            <button
              className="btn-small"
              style={{
                backgroundColor: detail.applications.length > 0 ? '#f1f5f9' : '#fee2e2',
                color: detail.applications.length > 0 ? '#94a3b8' : '#991b1b',
                border: '1px solid',
                borderColor: detail.applications.length > 0 ? '#cbd5e1' : '#fca5a5',
                cursor: detail.applications.length > 0 ? 'not-allowed' : 'pointer',
              }}
              disabled={actingId === detail.case.id || detail.applications.length > 0}
              title={detail.applications.length > 0 ? 'Cannot delete case with generated documents' : 'Delete case permanently'}
              onClick={() => deleteCase(detail.case)}
            >
              {actingId === detail.case.id ? '…' : 'Delete Case'}
            </button>
            <button className="btn-small btn-ghost" onClick={() => setDetail(null)}>
              Close
            </button>
          </div>
        </div>
      )}
      {detailError && <p className="form-error">{detailError}</p>}
    </div>
  )
}

export default function Cases() {
  return (
    <CaseErrorBoundary>
      <CasesInner />
    </CaseErrorBoundary>
  );
}

import React, { useEffect, useState, useCallback } from 'react'
import { adminApi } from '../lib/api'

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

const CATEGORIES = ['All', 'Civil', 'Criminal', 'Other'];

export default function Cases() {
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

  const openDetail = (id: string) => {
    setDetailError('');
    setDetail(null);
    adminApi.getCase(id)
      .then((res) => setDetail(res))
      .catch((err) => setDetailError(err.message));
  };

  const toggleArchive = async (c: AdminCase) => {
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
                  <th>Status</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((c) => {
                  const archived = c.status === 'archived';
                  return (
                    <tr key={c.id}>
                      <td>
                        <button className="link-btn" onClick={() => openDetail(c.id)}>
                          {c.nickname || c.case_number || c.case_type_label || c.id.slice(0, 8)}
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
                        <span className={`badge ${archived ? 'badge-disabled' : 'badge-active'}`}>
                          {archived ? 'Archived' : 'Active'}
                        </span>
                      </td>
                      <td>{c.updated_at ? new Date(c.updated_at).toLocaleDateString() : '—'}</td>
                      <td>
                        <button
                          className={`btn-small ${archived ? 'btn-success' : 'btn-danger'}`}
                          disabled={actingId === c.id}
                          onClick={() => toggleArchive(c)}
                        >
                          {actingId === c.id ? '…' : archived ? 'Restore' : 'Archive'}
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
            <h3>{detail.case.nickname || detail.case.case_number || detail.case.case_type_label || 'Case'}</h3>
            <span className={`badge ${detail.case.status === 'archived' ? 'badge-disabled' : 'badge-active'}`}>
              {detail.case.status === 'archived' ? 'Archived' : 'Active'}
            </span>
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
            <div><strong>{detail.case.application_count ?? detail.applications.length}</strong><span>Documents</span></div>
          </div>

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

          <div className="user-detail-actions">
            <button
              className={`btn-small ${detail.case.status === 'archived' ? 'btn-success' : 'btn-danger'}`}
              disabled={actingId === detail.case.id}
              onClick={() => toggleArchive(detail.case)}
            >
              {actingId === detail.case.id ? '…' : detail.case.status === 'archived' ? 'Restore case' : 'Archive case'}
            </button>
          </div>
        </div>
      )}
      {detailError && <p className="form-error">{detailError}</p>}
    </div>
  )
}

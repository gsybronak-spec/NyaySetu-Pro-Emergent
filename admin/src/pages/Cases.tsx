import React, { useEffect, useState, useCallback, useRef, useMemo, Component, ErrorInfo, ReactNode } from 'react'
import { adminApi } from '../lib/api'
import { useAdminAuth } from '../lib/auth'

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
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [detailError, setDetailError] = useState('');
  const [actingId, setActingId] = useState<string | null>(null);
  const [actingError, setActingError] = useState('');

  // Multi-select & Bulk actions state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const headerCheckboxRef = useRef<HTMLInputElement>(null);
  const [bulkActing, setBulkActing] = useState<'archive' | 'restore' | 'delete' | null>(null);
  const [bulkDeleteModalOpen, setBulkDeleteModalOpen] = useState(false);
  const [bulkDeleteError, setBulkDeleteError] = useState('');
  const [bulkActionFeedback, setBulkActionFeedback] = useState<{
    type: 'success' | 'error';
    message: string;
    blockedCases?: any[];
  } | null>(null);

  // Controlled Test Data Cascade Delete state
  const [singleCascadeTarget, setSingleCascadeTarget] = useState<{ caseItem: AdminCase; docCount: number } | null>(null);
  const [singleCascadeConfirmText, setSingleCascadeConfirmText] = useState('');
  const [singleCascadeConfirmed, setSingleCascadeConfirmed] = useState(false);
  const [singleCascadeLoading, setSingleCascadeLoading] = useState(false);
  const [singleCascadeError, setSingleCascadeError] = useState('');

  const [bulkCascadeModalOpen, setBulkCascadeModalOpen] = useState(false);
  const [bulkCascadeConfirmText, setBulkCascadeConfirmText] = useState('');
  const [bulkCascadeConfirmed, setBulkCascadeConfirmed] = useState(false);
  const [bulkCascadeLoading, setBulkCascadeLoading] = useState(false);
  const [bulkCascadeError, setBulkCascadeError] = useState('');

  // Super Admin Clean Reset All Test Cases state
  const { admin } = useAdminAuth();
  const isSuperAdmin = admin?.role === 'super_admin';
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [resetConfirmText, setResetConfirmText] = useState('');
  const [resetConfirmed, setResetConfirmed] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState('');

  const load = useCallback((params?: {
    q?: string;
    status?: string;
    category?: string;
    page?: number;
    pageSize?: number;
  }) => {
    setLoading(true);
    setError('');
    const targetQ = params?.q !== undefined ? params.q : q;
    const targetStatus = params?.status !== undefined ? params.status : statusFilter;
    const targetCategory = params?.category !== undefined ? params.category : categoryFilter;
    const targetPage = params?.page !== undefined ? params.page : page;
    const targetPageSize = params?.pageSize !== undefined ? params.pageSize : pageSize;

    adminApi.listCases({
      q: targetQ || undefined,
      status: targetStatus,
      category: targetCategory !== 'All' ? targetCategory : undefined,
      page: targetPage,
      page_size: targetPageSize,
    })
      .then((res) => {
        setItems(res.items || []);
        setTotal(res.total || 0);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [q, statusFilter, categoryFilter, page, pageSize]);

  useEffect(() => { load(); }, [load]);

  // Page-isolated visible IDs and selection derivations
  const visibleIds = useMemo(() => {
    return items.map((c) => c.id).filter((id): id is string => Boolean(id));
  }, [items]);

  const isAllVisibleSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id));
  const isSomeVisibleSelected = visibleIds.some((id) => selectedIds.has(id));
  const isIndeterminate = isSomeVisibleSelected && !isAllVisibleSelected;

  useEffect(() => {
    if (headerCheckboxRef.current) {
      headerCheckboxRef.current.indeterminate = isIndeterminate;
    }
  }, [isIndeterminate]);

  const handleToggleSelectAllVisible = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (isAllVisibleSelected) {
        visibleIds.forEach((id) => next.delete(id));
      } else {
        visibleIds.forEach((id) => next.add(id));
      }
      return next;
    });
  };

  const handleToggleSelect = (id: string, e?: React.SyntheticEvent) => {
    if (e) e.stopPropagation();
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleClearSelection = () => {
    setSelectedIds(new Set());
  };

  // Selected items breakdown for bulk delete safety modal
  const selectedCases = useMemo(() => {
    return items.filter((c) => selectedIds.has(c.id));
  }, [items, selectedIds]);

  const protectedCases = useMemo(() => {
    return selectedCases.filter((c) => (c.application_count ?? 0) > 0);
  }, [selectedCases]);

  const eligibleCases = useMemo(() => {
    return selectedCases.filter((c) => (c.application_count ?? 0) === 0);
  }, [selectedCases]);

  const totalSelectedDocs = useMemo(() => {
    return selectedCases.reduce((acc, c) => acc + (c.application_count ?? 0), 0);
  }, [selectedCases]);

  // Bulk actions operations
  const handleBulkArchive = async () => {
    if (selectedIds.size === 0 || bulkActing) return;
    setBulkActing('archive');
    setBulkActionFeedback(null);
    try {
      const ids = Array.from(selectedIds);
      const res = await adminApi.bulkArchiveCases(ids);
      setSelectedIds(new Set());
      setBulkActionFeedback({
        type: 'success',
        message: `Successfully archived ${res.updated_count || ids.length} case${(res.updated_count || ids.length) === 1 ? '' : 's'}.`,
      });
      load();
    } catch (err: any) {
      setBulkActionFeedback({
        type: 'error',
        message: err.message || 'Failed to bulk archive cases',
      });
    } finally {
      setBulkActing(null);
    }
  };

  const handleBulkRestore = async () => {
    if (selectedIds.size === 0 || bulkActing) return;
    setBulkActing('restore');
    setBulkActionFeedback(null);
    try {
      const ids = Array.from(selectedIds);
      const res = await adminApi.bulkRestoreCases(ids);
      setSelectedIds(new Set());
      setBulkActionFeedback({
        type: 'success',
        message: `Successfully restored ${res.updated_count || ids.length} case${(res.updated_count || ids.length) === 1 ? '' : 's'}.`,
      });
      load();
    } catch (err: any) {
      setBulkActionFeedback({
        type: 'error',
        message: err.message || 'Failed to bulk restore cases',
      });
    } finally {
      setBulkActing(null);
    }
  };

  const handleExecuteBulkDelete = async () => {
    if (selectedIds.size === 0 || bulkActing) return;
    setBulkActing('delete');
    setBulkDeleteError('');
    try {
      const ids = Array.from(selectedIds);
      const res = await adminApi.bulkDeleteCases(ids);
      if (res.blocked_cases && res.blocked_cases.length > 0) {
        const blockedSet = new Set<string>(res.blocked_cases.map((b: any) => b.case_id));
        setSelectedIds(blockedSet);
        setBulkActionFeedback({
          type: 'error',
          message: `Permanently deleted ${res.deleted_count || 0} case(s). ${res.blocked_count} case(s) were protected from deletion due to existing document history.`,
          blockedCases: res.blocked_cases,
        });
      } else {
        setSelectedIds(new Set());
        setBulkActionFeedback({
          type: 'success',
          message: `Successfully deleted ${res.deleted_count || ids.length} case${(res.deleted_count || ids.length) === 1 ? '' : 's'}.`,
        });
      }
      setBulkDeleteModalOpen(false);
      load();
    } catch (err: any) {
      setBulkDeleteError(err.message || 'Failed to bulk delete cases');
    } finally {
      setBulkActing(null);
    }
  };

  const openSingleCascade = (caseItem: AdminCase, docCount?: number) => {
    const count = docCount !== undefined ? docCount : (caseItem.application_count ?? 0);
    setSingleCascadeTarget({ caseItem, docCount: count });
    setSingleCascadeConfirmText('');
    setSingleCascadeConfirmed(false);
    setSingleCascadeError('');
  };

  const handleExecuteSingleCascadeDelete = async () => {
    if (!singleCascadeTarget || singleCascadeLoading) return;
    if (singleCascadeConfirmText.trim() !== 'DELETE' || !singleCascadeConfirmed) return;
    setSingleCascadeLoading(true);
    setSingleCascadeError('');
    try {
      const res = await adminApi.cascadeDeleteCase(singleCascadeTarget.caseItem.id);
      const caseLabel = singleCascadeTarget.caseItem.nickname || singleCascadeTarget.caseItem.case_number || singleCascadeTarget.caseItem.id;
      setBulkActionFeedback({
        type: 'success',
        message: `Successfully deleted test case "${caseLabel}" along with ${res.deleted_applications_count || 0} linked application(s) and ${res.deleted_drafts_count || 0} draft(s).`,
      });
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(singleCascadeTarget.caseItem.id);
        return next;
      });
      if (detail && detail.case.id === singleCascadeTarget.caseItem.id) {
        setDetail(null);
      }
      setSingleCascadeTarget(null);
      load();
    } catch (err: any) {
      setSingleCascadeError(err.message || 'Failed to cascade delete test case');
    } finally {
      setSingleCascadeLoading(false);
    }
  };

  const openBulkCascadeModal = () => {
    setBulkCascadeConfirmText('');
    setBulkCascadeConfirmed(false);
    setBulkCascadeError('');
    setBulkCascadeModalOpen(true);
  };

  const handleExecuteBulkCascadeDelete = async () => {
    if (selectedIds.size === 0 || bulkCascadeLoading) return;
    if (bulkCascadeConfirmText.trim() !== 'DELETE TEST DATA' || !bulkCascadeConfirmed) return;
    setBulkCascadeLoading(true);
    setBulkCascadeError('');
    try {
      const ids = Array.from(selectedIds);
      const res = await adminApi.bulkCascadeDeleteCases(ids);
      setSelectedIds(new Set());
      setBulkActionFeedback({
        type: 'success',
        message: `Successfully deleted ${res.deleted_cases_count || ids.length} test case(s) along with ${res.deleted_applications_count || 0} linked application(s) and ${res.deleted_drafts_count || 0} draft(s).`,
      });
      if (detail && ids.includes(detail.case.id)) {
        setDetail(null);
      }
      setBulkCascadeModalOpen(false);
      load();
    } catch (err: any) {
      setBulkCascadeError(err.message || 'Failed to bulk cascade delete test cases');
    } finally {
      setBulkCascadeLoading(false);
    }
  };

  const openResetAllModal = () => {
    setResetConfirmText('');
    setResetConfirmed(false);
    setResetError('');
    setResetModalOpen(true);
  };

  const handleExecuteResetAllTestCases = async () => {
    if (resetLoading) return;
    if (resetConfirmText.trim() !== 'DELETE ALL TEST CASES' || !resetConfirmed) return;
    setResetLoading(true);
    setResetError('');
    try {
      const res = await adminApi.resetAllTestCases('DELETE ALL TEST CASES');
      setSelectedIds(new Set());
      setDetail(null);
      setBulkActionFeedback({
        type: 'success',
        message: `Successfully cleaned all dummy cases: deleted ${res.deleted_cases_count || 0} case(s), ${res.deleted_applications_count || 0} linked application(s), and ${res.deleted_drafts_count || 0} draft(s). Cases count is now 0. You can now delete obsolete courts from Admin Catalog.`,
      });
      setResetModalOpen(false);
      load();
    } catch (err: any) {
      setResetError(err.message || 'Failed to clean reset test cases');
    } finally {
      setResetLoading(false);
    }
  };

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
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(c.id!);
        return next;
      });
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

  // Safe search & filter operations that clear selection and reset page
  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSelectedIds(new Set());
    setPage(1);
    setQ(searchInput.trim());
    load({ q: searchInput.trim(), status: statusFilter, category: categoryFilter, page: 1 });
  };

  const applyStatus = (s: string) => {
    setSelectedIds(new Set());
    setPage(1);
    setStatusFilter(s);
    load({ q, status: s, category: categoryFilter, page: 1 });
  };

  const applyCategory = (c: string) => {
    setSelectedIds(new Set());
    setPage(1);
    setCategoryFilter(c);
    load({ q, status: statusFilter, category: c, page: 1 });
  };

  const handlePageChange = (newPage: number) => {
    setSelectedIds(new Set());
    setPage(newPage);
    load({ page: newPage });
  };

  const handlePageSizeChange = (newSize: number) => {
    setSelectedIds(new Set());
    setPageSize(newSize);
    setPage(1);
    load({ page: 1, pageSize: newSize });
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1>Cases</h1>
          <p className="dashboard-desc">
            {total} case{total === 1 ? '' : 's'} across all advocates · archive/restore preserves data
          </p>
        </div>
        {isSuperAdmin && (
          <button
            type="button"
            className="btn-small"
            style={{
              backgroundColor: '#991b1b',
              color: '#ffffff',
              border: 'none',
              padding: '8px 14px',
              fontSize: '12px',
              fontWeight: 700,
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
            }}
            onClick={openResetAllModal}
            title="Super Admin: Permanently delete all existing dummy cases and linked records"
          >
            <span>🚨</span>
            <span>Delete All Existing Test Cases &amp; Linked Data</span>
          </button>
        )}
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

      {bulkActionFeedback && (
        <div style={{
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '16px',
          fontSize: '13px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          backgroundColor: bulkActionFeedback.type === 'success' ? '#f0fdf4' : '#fffbeb',
          border: `1px solid ${bulkActionFeedback.type === 'success' ? '#bbf7d0' : '#fde68a'}`,
          color: bulkActionFeedback.type === 'success' ? '#166534' : '#92400e',
        }}>
          <div>
            <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>{bulkActionFeedback.type === 'success' ? '✓' : '⚠️'}</span>
              <span>{bulkActionFeedback.message}</span>
            </div>
            {bulkActionFeedback.blockedCases && bulkActionFeedback.blockedCases.length > 0 && (
              <ul style={{ margin: '8px 0 0 18px', padding: 0, fontSize: '12px' }}>
                {bulkActionFeedback.blockedCases.map((b: any) => (
                  <li key={b.case_id}>
                    <strong>{b.case_number || b.case_id}</strong>: {b.reason}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button
            onClick={() => setBulkActionFeedback(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '15px', color: 'inherit', padding: '0 4px' }}
            aria-label="Dismiss message"
          >
            ✕
          </button>
        </div>
      )}

      {selectedIds.size > 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#eff6ff',
          border: '1px solid #bfdbfe',
          padding: '12px 20px',
          borderRadius: '8px',
          marginBottom: '16px',
          flexWrap: 'wrap',
          gap: '12px',
        }}>
          <div>
            <strong style={{ color: '#1e40af', fontSize: '1rem' }}>
              {selectedIds.size} {selectedIds.size === 1 ? 'Case Selected' : 'Cases Selected'}
            </strong>
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button
              className="btn-small btn-secondary"
              style={{ padding: '6px 14px', fontSize: '0.85rem' }}
              disabled={bulkActing !== null}
              onClick={handleBulkArchive}
              title="Archive all selected cases"
            >
              {bulkActing === 'archive' ? 'Archiving…' : '📦 Archive Selected'}
            </button>
            <button
              className="btn-small btn-secondary"
              style={{ padding: '6px 14px', fontSize: '0.85rem' }}
              disabled={bulkActing !== null}
              onClick={handleBulkRestore}
              title="Restore all selected cases to active"
            >
              {bulkActing === 'restore' ? 'Restoring…' : '🔄 Restore Selected'}
            </button>
            <button
              className="btn-small btn-danger"
              style={{ padding: '6px 14px', fontSize: '0.85rem' }}
              disabled={bulkActing !== null || bulkCascadeLoading}
              onClick={() => { setBulkDeleteError(''); setBulkDeleteModalOpen(true); }}
              title="Delete eligible selected cases permanently"
            >
              🗑️ Delete Selected
            </button>
            <button
              className="btn-small"
              style={{
                backgroundColor: '#b91c1c',
                color: '#ffffff',
                border: '1px solid #991b1b',
                padding: '6px 14px',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
              disabled={bulkActing !== null || bulkCascadeLoading}
              onClick={openBulkCascadeModal}
              title="Permanently delete selected test cases and all their linked applications and drafts"
            >
              ⚠️ Delete Cases + Linked Test Data
            </button>
            <button
              className="btn-small btn-ghost"
              style={{ padding: '6px 14px', fontSize: '0.85rem' }}
              disabled={bulkActing !== null}
              onClick={handleClearSelection}
              title="Deselect all cases"
            >
              ✕ Clear Selection
            </button>
          </div>
        </div>
      )}

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
            <>
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: '44px', textAlign: 'center' }}>
                      <input
                        type="checkbox"
                        ref={headerCheckboxRef}
                        checked={isAllVisibleSelected}
                        onChange={handleToggleSelectAllVisible}
                        aria-label="Select all visible cases"
                        title="Select all visible cases on this page"
                        style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                      />
                    </th>
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
                    const isSelected = Boolean(c.id && selectedIds.has(c.id));
                    return (
                      <tr key={caseId} style={{ backgroundColor: isSelected ? '#eff6ff' : undefined }}>
                        <td style={{ textAlign: 'center' }}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => c.id && handleToggleSelect(c.id, e)}
                            aria-label={`Select case ${c.case_number || c.nickname || c.id}`}
                            style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                          />
                        </td>
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
                            {docCount > 0 && (
                              <button
                                className="btn-small"
                                style={{
                                  backgroundColor: '#fff1f2',
                                  color: '#e11d48',
                                  border: '1px solid #fecdd3',
                                  cursor: 'pointer',
                                  padding: '2px 8px',
                                  fontSize: '11px',
                                  fontWeight: 600,
                                }}
                                disabled={actingId === c.id}
                                title="Controlled cleanup: Delete this test case and all its linked documents/drafts"
                                onClick={() => openSingleCascade(c, docCount)}
                              >
                                Delete + Test Data
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>

              {total > 0 && (
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px 16px',
                  borderTop: '1px solid #e2e8f0',
                  flexWrap: 'wrap',
                  gap: '12px',
                  fontSize: '13px',
                  color: '#64748b',
                }}>
                  <div>
                    Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} of {total} cases
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                      Per page:
                      <select
                        value={pageSize}
                        onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                        style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '13px', backgroundColor: '#fff' }}
                      >
                        <option value={25}>25</option>
                        <option value={50}>50</option>
                        <option value={100}>100</option>
                      </select>
                    </label>
                    <button
                      className="btn-small btn-ghost"
                      disabled={page <= 1 || loading}
                      onClick={() => handlePageChange(page - 1)}
                      style={{ cursor: page <= 1 ? 'not-allowed' : 'pointer' }}
                    >
                      ← Previous
                    </button>
                    <span style={{ fontWeight: 600 }}>Page {page} of {Math.max(1, Math.ceil(total / pageSize))}</span>
                    <button
                      className="btn-small btn-ghost"
                      disabled={page >= Math.ceil(total / pageSize) || loading}
                      onClick={() => handlePageChange(page + 1)}
                      style={{ cursor: page >= Math.ceil(total / pageSize) ? 'not-allowed' : 'pointer' }}
                    >
                      Next →
                    </button>
                  </div>
                </div>
              )}
            </>
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
            {detail.applications.length > 0 && (
              <button
                className="btn-small"
                style={{
                  backgroundColor: '#b91c1c',
                  color: '#ffffff',
                  border: '1px solid #991b1b',
                  cursor: 'pointer',
                  padding: '4px 12px',
                  fontSize: '12px',
                  fontWeight: 600,
                }}
                disabled={actingId === detail.case.id || singleCascadeLoading}
                title="Controlled cleanup: Delete this test case and all its linked documents/drafts"
                onClick={() => openSingleCascade(detail.case, detail.applications.length)}
              >
                ⚠️ Delete Case + Linked Test Data
              </button>
            )}
            <button className="btn-small btn-ghost" onClick={() => setDetail(null)}>
              Close
            </button>
          </div>
        </div>
      )}
      {detailError && <p className="form-error">{detailError}</p>}

      {/* Bulk Delete Safety Modal */}
      {bulkDeleteModalOpen && (
        <div
          className="modal-overlay"
          onClick={() => {
            if (bulkActing !== 'delete') setBulkDeleteModalOpen(false);
          }}
        >
          <div
            className="modal-card"
            style={{ maxWidth: '580px', width: '100%' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3 style={{ margin: 0, color: '#991b1b' }}>
                Delete {selectedIds.size} Selected Case{selectedIds.size === 1 ? '' : 's'}
              </h3>
              <button
                className="modal-close"
                disabled={bulkActing === 'delete'}
                onClick={() => setBulkDeleteModalOpen(false)}
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <p style={{ fontWeight: 600, color: '#334155', marginBottom: '14px', fontSize: '14px' }}>
                Delete {selectedIds.size} selected case{selectedIds.size === 1 ? '' : 's'}?{' '}
                <span style={{ color: '#dc2626' }}>This action cannot be undone.</span>
              </p>

              {bulkDeleteError && (
                <div style={{
                  backgroundColor: '#fee2e2',
                  border: '1px solid #ef4444',
                  borderRadius: '6px',
                  padding: '10px 14px',
                  marginBottom: '14px',
                  color: '#991b1b',
                  fontSize: '13px',
                }}>
                  <strong>Error:</strong> {bulkDeleteError}
                </div>
              )}

              {protectedCases.length > 0 && (
                <div style={{
                  backgroundColor: '#fffbeb',
                  border: '1px solid #fde68a',
                  borderRadius: '6px',
                  padding: '12px 14px',
                  marginBottom: '14px',
                  fontSize: '13px',
                  color: '#92400e',
                }}>
                  <div style={{ fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>⚠️</span>
                    <span>PROTECTED / BLOCKED CASES ({protectedCases.length})</span>
                  </div>
                  <p style={{ margin: '0 0 8px 0', fontSize: '12px', lineHeight: 1.4 }}>
                    The following cases contain linked applications or drafts. Cases with document history cannot be permanently deleted to preserve legal and audit records:
                  </p>
                  <div style={{
                    maxHeight: '120px',
                    overflowY: 'auto',
                    border: '1px solid #fef3c7',
                    borderRadius: '4px',
                    padding: '6px 10px',
                    backgroundColor: '#fff',
                  }}>
                    {protectedCases.map((c) => (
                      <div
                        key={c.id}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          fontSize: '12px',
                          padding: '4px 0',
                          borderBottom: '1px dashed #f1f5f9',
                        }}
                      >
                        <span style={{ fontWeight: 500, color: '#1e293b' }}>
                          {c.case_number || c.nickname || c.case_type_label || (c.id ? c.id.slice(0, 8) : 'Case')}
                        </span>
                        <span style={{ color: '#b45309', fontWeight: 600, fontSize: '11px' }}>
                          {c.application_count ?? 1} document(s) linked
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {eligibleCases.length > 0 && (
                <div style={{
                  backgroundColor: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  padding: '12px 14px',
                  marginBottom: '14px',
                  fontSize: '13px',
                  color: '#334155',
                }}>
                  <div style={{ fontWeight: 700, marginBottom: '6px', color: '#047857' }}>
                    ✓ ELIGIBLE FOR PERMANENT DELETION ({eligibleCases.length})
                  </div>
                  <p style={{ margin: '0 0 8px 0', fontSize: '12px' }}>
                    These cases have zero linked documents and will be permanently removed from the system:
                  </p>
                  <div style={{
                    maxHeight: '100px',
                    overflowY: 'auto',
                    fontSize: '12px',
                    color: '#64748b',
                    paddingLeft: '6px',
                  }}>
                    {eligibleCases.map((c) => (
                      <div key={c.id} style={{ padding: '2px 0' }}>
                        • {c.case_number || c.nickname || c.case_type_label || (c.id ? c.id.slice(0, 8) : 'Case')}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {eligibleCases.length === 0 && (
                <div style={{
                  backgroundColor: '#fef2f2',
                  border: '1px solid #fecaca',
                  borderRadius: '6px',
                  padding: '12px 14px',
                  fontSize: '13px',
                  color: '#991b1b',
                  marginBottom: '14px',
                  lineHeight: 1.4,
                }}>
                  <strong>Permanent Deletion Blocked:</strong> All {selectedIds.size} selected case{selectedIds.size === 1 ? '' : 's'} have generated legal documents or drafts. None can be permanently deleted. Please use <strong>Archive Selected</strong> instead to hide them from the active list while preserving records.
                </div>
              )}
            </div>

            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="btn-ghost"
                disabled={bulkActing === 'delete'}
                onClick={() => setBulkDeleteModalOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-danger"
                disabled={eligibleCases.length === 0 || bulkActing === 'delete'}
                onClick={handleExecuteBulkDelete}
              >
                {bulkActing === 'delete'
                  ? 'Deleting…'
                  : `Delete ${eligibleCases.length} Case${eligibleCases.length === 1 ? '' : 's'}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Single Case Cascade Delete Modal */}
      {singleCascadeTarget && (
        <div
          className="modal-overlay"
          onClick={() => {
            if (!singleCascadeLoading) setSingleCascadeTarget(null);
          }}
        >
          <div
            className="modal-card"
            style={{ maxWidth: '540px', width: '100%' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3 style={{ margin: 0, color: '#991b1b', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>⚠️</span>
                <span>Delete Case + Linked Test Data</span>
              </h3>
              <button
                className="modal-close"
                disabled={singleCascadeLoading}
                onClick={() => setSingleCascadeTarget(null)}
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <p style={{ fontWeight: 600, color: '#334155', marginBottom: '14px', fontSize: '14px' }}>
                You are about to permanently delete this case and all of its linked document history.{' '}
                <span style={{ color: '#dc2626' }}>This action cannot be undone.</span>
              </p>

              {singleCascadeError && (
                <div style={{
                  backgroundColor: '#fee2e2',
                  border: '1px solid #ef4444',
                  borderRadius: '6px',
                  padding: '10px 14px',
                  marginBottom: '14px',
                  color: '#991b1b',
                  fontSize: '13px',
                }}>
                  <strong>Error:</strong> {singleCascadeError}
                </div>
              )}

              <div style={{
                backgroundColor: '#fff1f2',
                border: '1px solid #fecdd3',
                borderRadius: '6px',
                padding: '12px 14px',
                marginBottom: '16px',
                fontSize: '13px',
                color: '#9f1239',
              }}>
                <div style={{ fontWeight: 700, marginBottom: '6px' }}>RECORDS TO BE PERMANENTLY REMOVED:</div>
                <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '4px 8px', fontSize: '12px' }}>
                  <strong>Case:</strong>
                  <span>{singleCascadeTarget.caseItem.nickname || singleCascadeTarget.caseItem.case_number || singleCascadeTarget.caseItem.id}</span>
                  <strong>Category / Type:</strong>
                  <span>{[singleCascadeTarget.caseItem.category, singleCascadeTarget.caseItem.case_type_label].filter(Boolean).join(' · ') || '—'}</span>
                  <strong>Advocate:</strong>
                  <span>{singleCascadeTarget.caseItem.owner?.name || singleCascadeTarget.caseItem.owner?.mobile || '—'}</span>
                  <strong>Linked Docs:</strong>
                  <span style={{ fontWeight: 700 }}>{singleCascadeTarget.docCount} generated application(s) &amp; all linked drafts</span>
                </div>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#1e293b', marginBottom: '6px' }}>
                  To confirm deletion, please type <strong style={{ color: '#b91c1c' }}>DELETE</strong> in the box below:
                </label>
                <input
                  type="text"
                  value={singleCascadeConfirmText}
                  onChange={(e) => setSingleCascadeConfirmText(e.target.value)}
                  placeholder="Type DELETE"
                  disabled={singleCascadeLoading}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '14px',
                    boxSizing: 'border-box',
                  }}
                  autoFocus
                />
              </div>

              <div style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '8px',
                padding: '10px 12px',
                backgroundColor: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
                fontSize: '12px',
                color: '#475569',
              }}>
                <input
                  type="checkbox"
                  id="confirm-single-cascade-checkbox"
                  checked={singleCascadeConfirmed}
                  disabled={singleCascadeLoading}
                  onChange={(e) => setSingleCascadeConfirmed(e.target.checked)}
                  style={{ marginTop: '2px', cursor: 'pointer' }}
                />
                <label htmlFor="confirm-single-cascade-checkbox" style={{ cursor: 'pointer', lineHeight: 1.4 }}>
                  I confirm this is a test case and I want to permanently delete this case and all its linked generated documents and drafts.
                </label>
              </div>
            </div>

            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="btn-ghost"
                disabled={singleCascadeLoading}
                onClick={() => setSingleCascadeTarget(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-danger"
                style={{
                  backgroundColor: singleCascadeConfirmText.trim() === 'DELETE' && singleCascadeConfirmed && !singleCascadeLoading ? '#b91c1c' : undefined,
                }}
                disabled={singleCascadeConfirmText.trim() !== 'DELETE' || !singleCascadeConfirmed || singleCascadeLoading}
                onClick={handleExecuteSingleCascadeDelete}
              >
                {singleCascadeLoading ? 'Deleting…' : 'Permanently Delete Case + Test Data'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Cases Cascade Delete Modal */}
      {bulkCascadeModalOpen && (
        <div
          className="modal-overlay"
          onClick={() => {
            if (!bulkCascadeLoading) setBulkCascadeModalOpen(false);
          }}
        >
          <div
            className="modal-card"
            style={{ maxWidth: '600px', width: '100%' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3 style={{ margin: 0, color: '#991b1b', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>⚠️</span>
                <span>Delete {selectedIds.size} Cases + Linked Test Data</span>
              </h3>
              <button
                className="modal-close"
                disabled={bulkCascadeLoading}
                onClick={() => setBulkCascadeModalOpen(false)}
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <p style={{ fontWeight: 600, color: '#334155', marginBottom: '14px', fontSize: '14px' }}>
                Permanently delete {selectedIds.size} selected test case{selectedIds.size === 1 ? '' : 's'} and all {totalSelectedDocs} linked document(s)?{' '}
                <span style={{ color: '#dc2626' }}>This action cannot be undone.</span>
              </p>

              {bulkCascadeError && (
                <div style={{
                  backgroundColor: '#fee2e2',
                  border: '1px solid #ef4444',
                  borderRadius: '6px',
                  padding: '10px 14px',
                  marginBottom: '14px',
                  color: '#991b1b',
                  fontSize: '13px',
                }}>
                  <strong>Error:</strong> {bulkCascadeError}
                </div>
              )}

              <div style={{
                backgroundColor: '#fff1f2',
                border: '1px solid #fecdd3',
                borderRadius: '6px',
                padding: '12px 14px',
                marginBottom: '14px',
                fontSize: '13px',
                color: '#9f1239',
              }}>
                <div style={{ fontWeight: 700, marginBottom: '6px' }}>
                  TOTAL RECORDS: {selectedIds.size} CASES · {totalSelectedDocs} DOCUMENTS · ALL LINKED DRAFTS
                </div>
                <div style={{
                  maxHeight: '140px',
                  overflowY: 'auto',
                  border: '1px solid #ffe4e6',
                  borderRadius: '4px',
                  padding: '6px 10px',
                  backgroundColor: '#fff',
                }}>
                  {selectedCases.map((c) => (
                    <div
                      key={c.id}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '12px',
                        padding: '4px 0',
                        borderBottom: '1px dashed #fecdd3',
                      }}
                    >
                      <span style={{ fontWeight: 500, color: '#1e293b' }}>
                        {c.case_number || c.nickname || c.case_type_label || (c.id ? c.id.slice(0, 8) : 'Case')}
                      </span>
                      <span style={{ color: '#be123c', fontWeight: 600, fontSize: '11px' }}>
                        {c.application_count ?? 0} document(s)
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#1e293b', marginBottom: '6px' }}>
                  To confirm bulk cleanup, please type <strong style={{ color: '#b91c1c' }}>DELETE TEST DATA</strong> below:
                </label>
                <input
                  type="text"
                  value={bulkCascadeConfirmText}
                  onChange={(e) => setBulkCascadeConfirmText(e.target.value)}
                  placeholder="Type DELETE TEST DATA"
                  disabled={bulkCascadeLoading}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '14px',
                    boxSizing: 'border-box',
                  }}
                  autoFocus
                />
              </div>

              <div style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '8px',
                padding: '10px 12px',
                backgroundColor: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
                fontSize: '12px',
                color: '#475569',
              }}>
                <input
                  type="checkbox"
                  id="confirm-bulk-cascade-checkbox"
                  checked={bulkCascadeConfirmed}
                  disabled={bulkCascadeLoading}
                  onChange={(e) => setBulkCascadeConfirmed(e.target.checked)}
                  style={{ marginTop: '2px', cursor: 'pointer' }}
                />
                <label htmlFor="confirm-bulk-cascade-checkbox" style={{ cursor: 'pointer', lineHeight: 1.4 }}>
                  I confirm these are test cases and I want to permanently delete them and all linked test applications/drafts.
                </label>
              </div>
            </div>

            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="btn-ghost"
                disabled={bulkCascadeLoading}
                onClick={() => setBulkCascadeModalOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-danger"
                style={{
                  backgroundColor: bulkCascadeConfirmText.trim() === 'DELETE TEST DATA' && bulkCascadeConfirmed && !bulkCascadeLoading ? '#b91c1c' : undefined,
                }}
                disabled={bulkCascadeConfirmText.trim() !== 'DELETE TEST DATA' || !bulkCascadeConfirmed || bulkCascadeLoading}
                onClick={handleExecuteBulkCascadeDelete}
              >
                {bulkCascadeLoading ? 'Deleting…' : `Permanently Delete ${selectedIds.size} Cases + Test Data`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Super Admin Clean Reset Modal */}
      {resetModalOpen && (
        <div
          className="modal-overlay"
          onClick={() => {
            if (!resetLoading) setResetModalOpen(false);
          }}
        >
          <div
            className="modal-card"
            style={{ maxWidth: '620px', width: '100%', border: '2px solid #b91c1c' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header" style={{ borderBottom: '1px solid #fee2e2', backgroundColor: '#fff5f5' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '20px' }}>🚨</span>
                <div>
                  <h3 style={{ margin: 0, color: '#991b1b' }}>
                    Delete All Existing Test Cases &amp; Linked Data
                  </h3>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: '#b91c1c', letterSpacing: '0.5px' }}>
                    SUPER ADMIN ONLY · PERMANENT CLEANUP
                  </span>
                </div>
              </div>
              <button
                className="modal-close"
                disabled={resetLoading}
                onClick={() => setResetModalOpen(false)}
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div style={{
                backgroundColor: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: '6px',
                padding: '12px 16px',
                marginBottom: '16px',
                color: '#991b1b',
                fontSize: '14px',
                fontWeight: 600,
                lineHeight: 1.5,
              }}>
                ⚠️ This will permanently delete all existing Cases and their linked test data. This cannot be undone.
              </div>

              {resetError && (
                <div style={{
                  backgroundColor: '#fee2e2',
                  border: '1px solid #ef4444',
                  borderRadius: '6px',
                  padding: '10px 14px',
                  marginBottom: '14px',
                  color: '#991b1b',
                  fontSize: '13px',
                }}>
                  <strong>Error:</strong> {resetError}
                </div>
              )}

              <div style={{ fontSize: '13px', color: '#334155', lineHeight: 1.5, marginBottom: '16px' }}>
                <p style={{ margin: '0 0 10px 0' }}>
                  Use this action to clean all dummy cases before real client data entry:
                </p>
                <ul style={{ margin: '0 0 12px 20px', padding: 0 }}>
                  <li><strong>All existing Cases ({total})</strong> will be permanently removed from the database.</li>
                  <li><strong>All linked Applications, Drafts, and Document History</strong> for these cases will be permanently removed.</li>
                  <li><strong>Foreign-Key References Cleared:</strong> Any Court previously blocked from deletion will become eligible for normal deletion in Admin Catalog.</li>
                  <li><strong style={{ color: '#047857' }}>Preserved Data:</strong> Users, advocate profiles, templates, plans, catalog structure, settings, and audit logs will NOT be deleted.</li>
                </ul>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#1e293b', marginBottom: '6px' }}>
                  To confirm execution, please type <strong style={{ color: '#b91c1c' }}>DELETE ALL TEST CASES</strong> in the box below:
                </label>
                <input
                  type="text"
                  value={resetConfirmText}
                  onChange={(e) => setResetConfirmText(e.target.value)}
                  placeholder="Type DELETE ALL TEST CASES"
                  disabled={resetLoading}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '14px',
                    boxSizing: 'border-box',
                    fontFamily: 'monospace',
                  }}
                  autoFocus
                />
              </div>

              <div style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '8px',
                padding: '10px 12px',
                backgroundColor: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
                fontSize: '12px',
                color: '#475569',
              }}>
                <input
                  type="checkbox"
                  id="confirm-reset-all-checkbox"
                  checked={resetConfirmed}
                  disabled={resetLoading}
                  onChange={(e) => setResetConfirmed(e.target.checked)}
                  style={{ marginTop: '2px', cursor: 'pointer' }}
                />
                <label htmlFor="confirm-reset-all-checkbox" style={{ cursor: 'pointer', lineHeight: 1.4 }}>
                  I confirm that all currently existing cases are dummy test cases and I want to permanently delete all cases and their linked test data.
                </label>
              </div>
            </div>

            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="btn-ghost"
                disabled={resetLoading}
                onClick={() => setResetModalOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-danger"
                style={{
                  backgroundColor: resetConfirmText.trim() === 'DELETE ALL TEST CASES' && resetConfirmed && !resetLoading ? '#991b1b' : undefined,
                  fontWeight: 700,
                }}
                disabled={resetConfirmText.trim() !== 'DELETE ALL TEST CASES' || !resetConfirmed || resetLoading}
                onClick={handleExecuteResetAllTestCases}
              >
                {resetLoading ? 'Cleaning all cases…' : 'Permanently Delete All Test Cases & Linked Data'}
              </button>
            </div>
          </div>
        </div>
      )}
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

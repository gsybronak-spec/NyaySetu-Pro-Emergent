import React, { useEffect, useState, useCallback } from 'react'
import { adminApi } from '../lib/api'
import { useAdminAuth } from '../lib/auth'

interface CatalogItem {
  id: string;
  en: string;
  gu?: string;
  cat?: string;
  district_id?: string;
  sections?: Array<{ id: string; label: string }>;
  active: boolean;
}

interface KindConfig {
  kind: string;
  label: string;
  hasCat: boolean;
  hasDistrict: boolean;
  hasSections: boolean;
}

const KINDS: KindConfig[] = [
  { kind: 'case-types', label: 'Case Types', hasCat: true, hasDistrict: false, hasSections: false },
  { kind: 'laws', label: 'Laws / Sections', hasCat: false, hasDistrict: false, hasSections: true },
  { kind: 'districts', label: 'Districts', hasCat: false, hasDistrict: false, hasSections: false },
  { kind: 'talukas', label: 'Talukas', hasCat: false, hasDistrict: true, hasSections: false },
  { kind: 'courts', label: 'Courts', hasCat: false, hasDistrict: true, hasSections: false },
  { kind: 'police-stations', label: 'Police Stations', hasCat: false, hasDistrict: true, hasSections: false },
];

interface FormState {
  en: string;
  gu: string;
  cat: string;
  district_id: string;
  sectionsText: string;
}

export default function Catalog() {
  const { admin } = useAdminAuth();
  const isSuper = admin?.role === 'super_admin';

  const [activeKind, setActiveKind] = useState<KindConfig>(KINDS[0]);
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [districts, setDistricts] = useState<Array<{ id: string; en: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>({ en: '', gu: '', cat: 'Other', district_id: '', sectionsText: '' });
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const [actingId, setActingId] = useState<string | null>(null);

  const load = useCallback(async (kind: KindConfig) => {
    setLoading(true);
    setError('');
    try {
      const [itemsRes, districtsRes] = await Promise.all([
        adminApi.listCatalog(kind.kind),
        kind.hasDistrict ? adminApi.listCatalog('districts') : Promise.resolve([]),
      ]);
      setItems(itemsRes);
      setDistricts(districtsRes);
    } catch (err: any) {
      setError(err.message || 'Failed to load catalog');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(activeKind); }, [activeKind, load]);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
  const [bulkDeleteError, setBulkDeleteError] = useState('');
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const switchKind = (k: KindConfig) => {
    setActiveKind(k);
    setSelectedIds(new Set());
    setSearchQuery('');
  };

  const openCreate = () => {
    setEditingId(null);
    setForm({ en: '', gu: '', cat: 'Other', district_id: '', sectionsText: '' });
    setFormError('');
    setFormOpen(true);
  };

  const openEdit = (item: CatalogItem) => {
    setEditingId(item.id);
    setForm({
      en: item.en,
      gu: item.gu || '',
      cat: item.cat || 'Other',
      district_id: item.district_id || '',
      sectionsText: (item.sections || []).map((s) => `${s.id}|${s.label}`).join('\n'),
    });
    setFormError('');
    setFormOpen(true);
  };

  const parseSections = (): Array<{ id: string; label: string }> | undefined => {
    if (!activeKind.hasSections) return undefined;
    const out: Array<{ id: string; label: string }> = [];
    for (const line of form.sectionsText.split('\n')) {
      const t = line.trim();
      if (!t) continue;
      const idx = t.indexOf('|');
      const id = idx >= 0 ? t.slice(0, idx).trim() : t.trim();
      const label = idx >= 0 ? t.slice(idx + 1).trim() : t.trim();
      if (!id || !label) throw new Error(`Invalid section line: "${t}" — use format "id|label"`);
      out.push({ id, label });
    }
    return out;
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    if (!form.en.trim()) return setFormError('English label is required');
    let sections: Array<{ id: string; label: string }> | undefined;
    try {
      sections = parseSections();
    } catch (err: any) {
      return setFormError(err.message);
    }
    const payload: any = { en: form.en.trim(), gu: form.gu.trim() };
    if (activeKind.hasCat) payload.cat = form.cat || 'Other';
    if (activeKind.hasDistrict) payload.district_id = form.district_id || 'generic';
    if (sections !== undefined) payload.sections = sections;

    setSaving(true);
    try {
      if (editingId) {
        await adminApi.updateCatalogItem(activeKind.kind, editingId, payload);
      } else {
        await adminApi.createCatalogItem(activeKind.kind, payload);
      }
      setFormOpen(false);
      load(activeKind);
    } catch (err: any) {
      setFormError(err.message || 'Failed to save catalog entry');
    } finally {
      setSaving(false);
    }
  };

  const toggleStatus = async (item: CatalogItem) => {
    setActingId(item.id);
    try {
      await adminApi.setCatalogStatus(activeKind.kind, item.id, !item.active);
      setItems((prev) => prev.map((x) => (x.id === item.id ? { ...x, active: !item.active } : x)));
    } catch (err: any) {
      setError(err.message || 'Failed to update status');
    } finally {
      setActingId(null);
    }
  };

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteItem, setDeleteItem] = useState<CatalogItem | null>(null);
  const [deleteError, setDeleteError] = useState('');
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);
  const [dragOverIdx, setDragOverIdx] = useState<number | null>(null);
  const [reorderSaving, setReorderSaving] = useState(false);

  const confirmDelete = (item: CatalogItem) => {
    setDeleteItem(item);
    setDeleteError('');
    setDeleteOpen(true);
  };

  const executeDelete = async () => {
    if (!deleteItem) return;
    setSaving(true);
    try {
      await adminApi.deleteCatalogItem(activeKind.kind, deleteItem.id, true);
      setItems((prev) => prev.filter((x) => x.id !== deleteItem.id));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(deleteItem.id);
        return next;
      });
      setDeleteOpen(false);
      setDeleteItem(null);
    } catch (err: any) {
      setDeleteError(err.message || 'Failed to permanently delete item.');
    } finally {
      setSaving(false);
    }
  };

  const filteredItems = items.filter((item) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase().trim();
    return (
      item.id.toLowerCase().includes(q) ||
      item.en.toLowerCase().includes(q) ||
      (item.gu && item.gu.toLowerCase().includes(q)) ||
      (item.cat && item.cat.toLowerCase().includes(q))
    );
  });

  const handleSelectAll = () => {
    const allFilteredSelected = filteredItems.length > 0 && filteredItems.every((i) => selectedIds.has(i.id));
    if (allFilteredSelected) {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        filteredItems.forEach((i) => next.delete(i.id));
        return next;
      });
    } else {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        filteredItems.forEach((i) => next.add(i.id));
        return next;
      });
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const executeBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    setBulkDeleting(true);
    setBulkDeleteError('');
    const idsToDelete = Array.from(selectedIds);
    try {
      const res = await adminApi.bulkDeleteCatalogItems(activeKind.kind, idsToDelete);
      const deletedList: string[] = res.deleted_ids || idsToDelete;
      const deletedSet = new Set<string>(deletedList);
      setItems((prev) => prev.filter((x) => !deletedSet.has(x.id)));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        deletedSet.forEach((id: string) => next.delete(id));
        return next;
      });
      setBulkDeleteOpen(false);
      if (res.failed_count > 0 && res.failed_ids?.length) {
        const reasons = res.failed_ids.map((f: any) => `${f.id}: ${f.reason}`).join(', ');
        alert(`Deleted ${res.deleted_count} items. ${res.failed_count} items could not be deleted because: ${reasons}`);
      }
      load(activeKind);
    } catch (err: any) {
      setBulkDeleteError(err.message || 'Failed to bulk delete selected items.');
    } finally {
      setBulkDeleting(false);
    }
  };

  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDraggedIdx(index);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(index));
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragOverIdx !== index) {
      setDragOverIdx(index);
    }
  };

  const handleDragEnd = () => {
    setDraggedIdx(null);
    setDragOverIdx(null);
  };

  const handleDrop = async (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();
    if (draggedIdx === null || draggedIdx === dropIndex) {
      setDraggedIdx(null);
      setDragOverIdx(null);
      return;
    }
    const previousItems = [...items];
    const newItems = [...items];
    const [movedItem] = newItems.splice(draggedIdx, 1);
    newItems.splice(dropIndex, 0, movedItem);

    setItems(newItems);
    setDraggedIdx(null);
    setDragOverIdx(null);
    setReorderSaving(true);

    try {
      await adminApi.reorderCatalog(activeKind.kind, newItems.map((i) => i.id));
    } catch (err: any) {
      setError(err.message || 'Failed to save new order');
      setItems(previousItems);
    } finally {
      setReorderSaving(false);
    }
  };

  const catChoices = ['Civil', 'Criminal', 'Other'];

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Catalog</h1>
        <p className="dashboard-desc">
          Case types, laws, districts, courts and police stations · deactivated entries stay valid for existing cases
        </p>
      </div>

      <div className="tab-bar catalog-tabs">
        {KINDS.map((k) => (
          <button
            key={k.kind}
            className={`tab-btn ${k.kind === activeKind.kind ? 'active' : ''}`}
            onClick={() => switchKind(k)}
          >
            {k.label}
          </button>
        ))}
      </div>

      {isSuper && (
        <div className="plans-toolbar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button className="btn-primary" onClick={openCreate}>+ Add {activeKind.label.replace(/ \/.*/, '')} Entry</button>
            <span className="plans-hint">
              {reorderSaving ? 'Saving order...' : 'Drag rows using the ⋮⋮ handle to reorder'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              type="text"
              className="form-input"
              style={{ width: '220px', padding: '6px 12px', fontSize: '0.85rem' }}
              placeholder={`Search ${activeKind.label}...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <span className="plans-hint">Catalog changes require super admin</span>
          </div>
        </div>
      )}

      {selectedIds.size > 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#eff6ff',
          border: '1px solid #bfdbfe',
          padding: '10px 16px',
          borderRadius: '6px',
          margin: '12px 0'
        }}>
          <div>
            <strong style={{ color: '#1e40af', fontSize: '0.95rem' }}>
              {selectedIds.size} {activeKind.label} selected
            </strong>
            {filteredItems.length !== items.length && (
              <span style={{ marginLeft: '8px', color: '#6b7280', fontSize: '0.85rem' }}>
                (filtered from {items.length} total)
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn-small btn-danger"
              onClick={() => { setBulkDeleteError(''); setBulkDeleteOpen(true); }}
              disabled={bulkDeleting}
            >
              🗑️ Delete Selected ({selectedIds.size})
            </button>
            <button
              className="btn-small btn-plain"
              onClick={() => setSelectedIds(new Set())}
              disabled={bulkDeleting}
            >
              Clear Selection
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="dashboard-error">
          <p>Failed to load catalog: {error}</p>
          <button onClick={() => load(activeKind)}>Retry</button>
        </div>
      )}

      {loading ? (
        <div className="dashboard-loading"><div className="spinner"></div><p>Loading {activeKind.label}…</p></div>
      ) : (
        <div className="dashboard-table-card">
          {filteredItems.length === 0 ? (
            <p className="no-data">No entries found matching your criteria</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  {isSuper && (
                    <th style={{ width: '36px', textAlign: 'center' }}>
                      <input
                        type="checkbox"
                        checked={filteredItems.length > 0 && filteredItems.every((i) => selectedIds.has(i.id))}
                        onChange={handleSelectAll}
                        title="Select all visible"
                      />
                    </th>
                  )}
                  {isSuper && <th style={{ width: '40px', textAlign: 'center' }}>⇅</th>}
                  <th>ID</th>
                  <th>English</th>
                  <th>ગુજરાતી</th>
                  {activeKind.hasCat && <th>Category</th>}
                  {activeKind.hasDistrict && <th>District</th>}
                  {activeKind.hasSections && <th>Sections</th>}
                  <th>Status</th>
                  {isSuper && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item, idx) => (
                  <tr
                    key={item.id}
                    draggable={isSuper}
                    onDragStart={(e) => handleDragStart(e, idx)}
                    onDragOver={(e) => handleDragOver(e, idx)}
                    onDragEnd={handleDragEnd}
                    onDrop={(e) => handleDrop(e, idx)}
                    style={{
                      opacity: draggedIdx === idx ? 0.35 : 1,
                      backgroundColor: dragOverIdx === idx ? '#f0fdf4' : (selectedIds.has(item.id) ? '#eff6ff' : undefined),
                      borderTop: dragOverIdx === idx ? '2px solid #16a34a' : undefined,
                      transition: 'background-color 0.15s ease',
                    }}
                  >
                    {isSuper && (
                      <td style={{ textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(item.id)}
                          onChange={() => handleToggleSelect(item.id)}
                        />
                      </td>
                    )}
                    {isSuper && (
                      <td
                        style={{
                          cursor: 'grab',
                          userSelect: 'none',
                          textAlign: 'center',
                          color: '#9ca3af',
                          fontSize: '1.2rem',
                          padding: '8px 4px',
                        }}
                        title="Drag to reorder"
                      >
                        ⋮⋮
                      </td>
                    )}
                    <td className="catalog-id">{item.id}</td>
                    <td>{item.en}</td>
                    <td>{item.gu || '—'}</td>
                    {activeKind.hasCat && <td>{item.cat || '—'}</td>}
                    {activeKind.hasDistrict && (
                      <td>{districts.find((d) => d.id === item.district_id)?.en || item.district_id || '—'}</td>
                    )}
                    {activeKind.hasSections && <td>{(item.sections || []).length}</td>}
                    <td>
                      <span className={`badge ${item.active ? 'badge-active' : 'badge-disabled'}`}>
                        {item.active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    {isSuper && (
                      <td>
                        <div className="plans-actions">
                          <button className="btn-small btn-plain" onClick={() => openEdit(item)}>Edit</button>
                          <button
                            className={`btn-small ${item.active ? 'btn-danger' : 'btn-success'}`}
                            disabled={actingId === item.id}
                            onClick={() => toggleStatus(item)}
                          >
                            {actingId === item.id ? '…' : item.active ? 'Deactivate' : 'Activate'}
                          </button>
                          <button 
                            className="btn-small btn-danger" 
                            style={{ marginLeft: '4px' }}
                            onClick={() => confirmDelete(item)}
                          >
                            🗑️ Delete
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {formOpen && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h3>{editingId ? 'Edit Entry' : 'New Entry'} — {activeKind.label}</h3>
              <button className="modal-close" onClick={() => setFormOpen(false)}>✕</button>
            </div>
            <form onSubmit={save}>
              <div className="modal-body">
                <label className="form-label">English label *</label>
                <input className="form-input" value={form.en} onChange={(e) => setForm({ ...form, en: e.target.value })} placeholder="e.g. Motor Accident Claims Tribunal" />
                <label className="form-label">ગુજરાતી label</label>
                <input className="form-input" value={form.gu} onChange={(e) => setForm({ ...form, gu: e.target.value })} placeholder="e.g. મોટર દુર્ઘટના દાવા અધિકરણ" />
                {activeKind.hasCat && (
                  <>
                    <label className="form-label">Category</label>
                    <select className="form-input" value={form.cat} onChange={(e) => setForm({ ...form, cat: e.target.value })}>
                      {catChoices.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </>
                )}
                {activeKind.hasDistrict && (
                  <>
                    <label className="form-label">District</label>
                    <select className="form-input" value={form.district_id} onChange={(e) => setForm({ ...form, district_id: e.target.value })}>
                      <option value="generic">Generic (all districts)</option>
                      {districts.map((d) => <option key={d.id} value={d.id}>{d.en}</option>)}
                    </select>
                  </>
                )}
                {activeKind.hasSections && (
                  <>
                    <label className="form-label">Sections (one per line, format: id|label)</label>
                    <textarea className="form-input" rows={6} value={form.sectionsText} onChange={(e) => setForm({ ...form, sectionsText: e.target.value })} placeholder={"138|Section 138 - Dishonour of cheque\n139|Section 139 - Presumption in favour of holder"} />
                  </>
                )}
                {formError && <p className="form-error">{formError}</p>}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-ghost" onClick={() => setFormOpen(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {deleteOpen && deleteItem && (
        <div className="modal-overlay">
          <div className="modal-card modal-card-danger">
            <div className="modal-header">
              <h3>Delete {activeKind.label.replace(/ \/.*/, '')} Permanently?</h3>
              <button className="modal-close" onClick={() => setDeleteOpen(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p>Delete <strong>"{deleteItem.en}"</strong> permanently?</p>
              <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', margin: '16px 0', fontFamily: 'monospace' }}>
                <div><strong>Type:</strong> {activeKind.label}</div>
                <div><strong>ID:</strong> {deleteItem.id}</div>
                <div><strong>Name (EN):</strong> {deleteItem.en}</div>
                <div><strong>Name (GU):</strong> {deleteItem.gu || '—'}</div>
                <div><strong>Status:</strong> {deleteItem.active ? 'Active' : 'Inactive'}</div>
              </div>
              <p style={{ color: '#d32f2f', fontWeight: 600, fontSize: '0.9rem' }}>
                This action cannot be undone. If this record is referenced by any existing cases or applications, deletion will be blocked and you will receive a 409 Conflict error.
              </p>
              {deleteError && (
                <div style={{ marginTop: '12px', padding: '8px', background: '#ffebee', color: '#c62828', borderRadius: '4px', fontSize: '0.9rem' }}>
                  <strong>Deletion Failed:</strong><br/>{deleteError}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn-ghost" onClick={() => setDeleteOpen(false)} disabled={saving}>Cancel</button>
              <button 
                className="btn-danger" 
                disabled={saving} 
                onClick={executeDelete}
              >
                {saving ? 'Deleting...' : 'Delete Permanently'}
              </button>
            </div>
          </div>
        </div>
      )}

      {bulkDeleteOpen && (
        <div className="modal-overlay">
          <div className="modal-card modal-card-danger">
            <div className="modal-header">
              <h3>Delete {selectedIds.size} {activeKind.label} Permanently?</h3>
              <button className="modal-close" onClick={() => setBulkDeleteOpen(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p>
                Delete <strong>{selectedIds.size} {activeKind.label}</strong> permanently?
              </p>
              <p style={{ color: '#d32f2f', fontWeight: 600, fontSize: '0.9rem', marginTop: '12px' }}>
                This action cannot be undone. All {selectedIds.size} selected records will be permanently removed from the database.
              </p>
              <div style={{ maxHeight: '160px', overflowY: 'auto', background: '#f9fafb', border: '1px solid #e5e7eb', padding: '8px 12px', borderRadius: '4px', margin: '12px 0', fontSize: '0.85rem' }}>
                {Array.from(selectedIds).map((id) => {
                  const it = items.find((x) => x.id === id);
                  return (
                    <div key={id} style={{ padding: '2px 0' }}>
                      • <strong>{it ? it.en : id}</strong> <span style={{ color: '#888' }}>({id})</span>
                    </div>
                  );
                })}
              </div>
              {bulkDeleteError && (
                <div style={{ marginTop: '12px', padding: '8px', background: '#ffebee', color: '#c62828', borderRadius: '4px', fontSize: '0.9rem' }}>
                  <strong>Bulk Deletion Failed:</strong><br/>{bulkDeleteError}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn-ghost" onClick={() => setBulkDeleteOpen(false)} disabled={bulkDeleting}>Cancel</button>
              <button 
                className="btn-danger" 
                disabled={bulkDeleting} 
                onClick={executeBulkDelete}
              >
                {bulkDeleting ? 'Deleting...' : 'Delete Permanently'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

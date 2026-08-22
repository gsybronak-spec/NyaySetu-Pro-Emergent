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

  const switchKind = (k: KindConfig) => {
    setActiveKind(k);
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
  const [deleteConfirm, setDeleteConfirm] = useState('');
  const [deleteError, setDeleteError] = useState('');

  const confirmDelete = (item: CatalogItem) => {
    setDeleteItem(item);
    setDeleteConfirm('');
    setDeleteError('');
    setDeleteOpen(true);
  };

  const executeDelete = async () => {
    if (!deleteItem) return;
    if (deleteConfirm !== 'DELETE') return;
    setSaving(true);
    try {
      await adminApi.deleteCatalogItem(activeKind.kind, deleteItem.id, true);
      setDeleteOpen(false);
      setDeleteItem(null);
      load(activeKind);
    } catch (err: any) {
      setDeleteError(err.message || 'Failed to permanently delete item.');
    } finally {
      setSaving(false);
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
        <div className="plans-toolbar">
          <button className="btn-primary" onClick={openCreate}>+ Add {activeKind.label.replace(/ \/.*/, '')} Entry</button>
          <span className="plans-hint">Catalog changes require super admin</span>
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
          {items.length === 0 ? (
            <p className="no-data">No entries in {activeKind.label}</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
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
                {items.map((item) => (
                  <tr key={item.id}>
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
              <h3>Permanent Hard Delete</h3>
              <button className="modal-close" onClick={() => setDeleteOpen(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p>You are about to <strong>PERMANENTLY DELETE</strong> this catalog record:</p>
              <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', margin: '16px 0', fontFamily: 'monospace' }}>
                <div><strong>Type:</strong> {activeKind.label}</div>
                <div><strong>ID:</strong> {deleteItem.id}</div>
                <div><strong>Name (EN):</strong> {deleteItem.en}</div>
                <div><strong>Name (GU):</strong> {deleteItem.gu || '—'}</div>
                <div><strong>Status:</strong> {deleteItem.active ? 'Active' : 'Inactive'}</div>
              </div>
              <p style={{ color: '#d32f2f', fontWeight: 600, fontSize: '0.9rem' }}>
                WARNING: This action cannot be undone. If this record is referenced by any existing cases or applications, deletion will be blocked and you will receive a 409 Conflict error. In that scenario, you must mark it as Inactive instead.
              </p>
              <p style={{ marginTop: '16px' }}>Type <strong>DELETE</strong> below to confirm:</p>
              <input 
                className="form-input" 
                value={deleteConfirm} 
                onChange={e => setDeleteConfirm(e.target.value)} 
                placeholder="DELETE" 
                style={{ marginTop: '8px', border: '1px solid #d32f2f' }}
              />
              {deleteError && (
                <div style={{ marginTop: '12px', padding: '8px', background: '#ffebee', color: '#c62828', borderRadius: '4px', fontSize: '0.9rem' }}>
                  <strong>Deletion Failed:</strong><br/>{deleteError}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn-ghost" onClick={() => setDeleteOpen(false)}>Cancel</button>
              <button 
                className="btn-danger" 
                disabled={deleteConfirm !== 'DELETE' || saving} 
                onClick={executeDelete}
              >
                {saving ? 'Deleting...' : 'Permanently Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

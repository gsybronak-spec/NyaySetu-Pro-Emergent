import React, { useEffect, useState } from 'react'
import { adminApi } from '../lib/api'
import { useAdminAuth } from '../lib/auth'

interface Plan {
  id: string;
  name: string;
  price: number;
  credits: number;
  popular: boolean;
  per_template?: number;
  description?: string | null;
  active: boolean;
}

interface PlanFormState {
  name: string;
  price: string;
  credits: string;
  popular: boolean;
  description: string;
}

const EMPTY_FORM: PlanFormState = { name: '', price: '', credits: '', popular: false, description: '' };

export default function Plans() {
  const { admin } = useAdminAuth();
  const isSuper = admin?.role === 'super_admin';

  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<PlanFormState>(EMPTY_FORM);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const [actingId, setActingId] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError('');
    adminApi.listPlans()
      .then(setPlans)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setFormError('');
    setFormOpen(true);
  };

  const openEdit = (p: Plan) => {
    setEditingId(p.id);
    setForm({ name: p.name, price: String(p.price), credits: String(p.credits), popular: p.popular, description: p.description || '' });
    setFormError('');
    setFormOpen(true);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    const price = parseInt(form.price, 10);
    const credits = parseInt(form.credits, 10);
    if (!form.name.trim()) return setFormError('Plan name is required');
    if (isNaN(price) || price < 0) return setFormError('Price must be a non-negative number');
    if (isNaN(credits) || credits < 1) return setFormError('Credits must be a positive number');

    const payload = { name: form.name.trim(), price, credits, popular: form.popular, description: form.description.trim() || null };
    setSaving(true);
    try {
      if (editingId) {
        await adminApi.updatePlan(editingId, payload);
      } else {
        await adminApi.createPlan(payload);
      }
      setFormOpen(false);
      load();
    } catch (err: any) {
      setFormError(err.message || 'Failed to save plan');
    } finally {
      setSaving(false);
    }
  };

  const toggleStatus = async (p: Plan) => {
    setActingId(p.id);
    try {
      await adminApi.setPlanStatus(p.id, !p.active);
      setPlans((prev) => prev.map((x) => (x.id === p.id ? { ...x, active: !p.active } : x)));
    } catch (err: any) {
      setError(err.message || 'Failed to update plan status');
    } finally {
      setActingId(null);
    }
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Plans & Pricing</h1>
        <p className="dashboard-desc">
          {plans.length} plan{plans.length === 1 ? '' : 's'} · inactive plans are hidden from the lawyer catalog and cannot be purchased
        </p>
      </div>

      {isSuper && (
        <div className="plans-toolbar">
          <button className="btn-primary" onClick={openCreate}>+ New Plan</button>
          <span className="plans-hint">Pricing changes require super admin</span>
        </div>
      )}
      {!isSuper && <p className="plans-hint">Only super admins can create or edit plans.</p>}

      {error && (
        <div className="dashboard-error">
          <p>Failed to load plans: {error}</p>
          <button onClick={load}>Retry</button>
        </div>
      )}

      {loading ? (
        <div className="dashboard-loading"><div className="spinner"></div><p>Loading plans…</p></div>
      ) : (
        <div className="dashboard-table-card">
          {plans.length === 0 ? (
            <p className="no-data">No plans configured</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Plan</th>
                  <th>Price</th>
                  <th>Credits</th>
                  <th>Per Template</th>
                  <th>Popular</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {plans.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <strong>{p.name}</strong>
                      {p.description && <div className="case-sub">{p.description}</div>}
                    </td>
                    <td>₹{p.price}</td>
                    <td>{p.credits}</td>
                    <td>₹{p.per_template ?? (p.credits ? (p.price / p.credits).toFixed(2) : '—')}</td>
                    <td>{p.popular ? <span className="badge badge-audit">Popular</span> : '—'}</td>
                    <td>
                      <span className={`badge ${p.active ? 'badge-active' : 'badge-disabled'}`}>
                        {p.active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      <div className="plans-actions">
                        {isSuper && (
                          <button className="btn-small btn-plain" onClick={() => openEdit(p)}>Edit</button>
                        )}
                        {isSuper && (
                          <button
                            className={`btn-small ${p.active ? 'btn-danger' : 'btn-success'}`}
                            disabled={actingId === p.id}
                            onClick={() => toggleStatus(p)}
                          >
                            {actingId === p.id ? '…' : p.active ? 'Deactivate' : 'Activate'}
                          </button>
                        )}
                      </div>
                    </td>
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
              <h3>{editingId ? 'Edit Plan' : 'New Plan'}</h3>
              <button className="modal-close" onClick={() => setFormOpen(false)}>✕</button>
            </div>
            <form onSubmit={save}>
              <div className="modal-body">
                <label className="form-label">Plan name *</label>
                <input className="form-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Starter Pack" />
                <div className="form-row">
                  <div>
                    <label className="form-label">Price (₹) *</label>
                    <input className="form-input" type="number" min="0" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} placeholder="299" />
                  </div>
                  <div>
                    <label className="form-label">Credits *</label>
                    <input className="form-input" type="number" min="1" value={form.credits} onChange={(e) => setForm({ ...form, credits: e.target.value })} placeholder="51" />
                  </div>
                </div>
                <label className="form-check">
                  <input type="checkbox" checked={form.popular} onChange={(e) => setForm({ ...form, popular: e.target.checked })} />
                  Mark as popular
                </label>
                <label className="form-label">Description</label>
                <textarea className="form-input" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Optional description shown to lawyers" />
                {formError && <p className="form-error">{formError}</p>}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-ghost" onClick={() => setFormOpen(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save Plan'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

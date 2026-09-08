import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminApi } from '../lib/api';
import { useAdminAuth } from '../lib/auth';
import StatusBadge from '../components/StatusBadge';
import { ADMIN_TEMPLATE_PAIRS, AdminTemplatePair, getOrderedAdminPairs } from '../lib/templatePairs';

export default function Templates() {
  const navigate = useNavigate();
  const { admin } = useAdminAuth();
  const isSuperAdmin = admin?.role === 'super_admin';
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals state
  const [previewModal, setPreviewModal] = useState<{ open: boolean; template: any; previewEn: string; previewGu: string; lang: 'en'|'gu'; loading: boolean } | null>(null);
  const [historyModal, setHistoryModal] = useState<{ open: boolean; template: any; versions: any[]; loading: boolean } | null>(null);
  const [cloneModal, setCloneModal] = useState<{ open: boolean; template: any; newId: string; newNameEn: string; newNameGu: string } | null>(null);
  const [importModal, setImportModal] = useState<{
    step: 'pick' | 'review' | 'creating';
    fileName: string;
    error: string;
    analysis: any | null;
    id: string;
    nameEn: string;
    nameGu: string;
    category: string;
    fields: any[];
  } | null>(null);
  const [deleteModal, setDeleteModal] = useState<{
    open: boolean;
    template: any;
    confirmText: string;
    loading: boolean;
    error: string;
  } | null>(null);

  const [orderModal, setOrderModal] = useState<{
    open: boolean;
    pairs: AdminTemplatePair[];
    loading: boolean;
    saving: boolean;
    successMsg: string;
    error: string;
  } | null>(null);

  const handleOpenOrderModal = async () => {
    setOrderModal({
      open: true,
      pairs: [...ADMIN_TEMPLATE_PAIRS],
      loading: true,
      saving: false,
      successMsg: '',
      error: '',
    });
    try {
      const res = await adminApi.getTemplateOrder();
      const order = res?.template_order || [];
      const ordered = getOrderedAdminPairs(order);
      setOrderModal(prev => prev ? { ...prev, pairs: ordered, loading: false } : null);
    } catch (err: any) {
      setOrderModal(prev => prev ? { ...prev, loading: false, error: 'Failed to fetch current order: ' + err.message } : null);
    }
  };

  const moveOrder = (index: number, direction: 'up' | 'down' | 'top' | 'bottom') => {
    if (!orderModal) return;
    const current = [...orderModal.pairs];
    if (direction === 'up' && index > 0) {
      const temp = current[index];
      current[index] = current[index - 1];
      current[index - 1] = temp;
    } else if (direction === 'down' && index < current.length - 1) {
      const temp = current[index];
      current[index] = current[index + 1];
      current[index + 1] = temp;
    } else if (direction === 'top' && index > 0) {
      const [item] = current.splice(index, 1);
      current.unshift(item);
    } else if (direction === 'bottom' && index < current.length - 1) {
      const [item] = current.splice(index, 1);
      current.push(item);
    }
    setOrderModal({ ...orderModal, pairs: current, successMsg: '', error: '' });
  };

  const resetToDefaultOrder = () => {
    if (!orderModal) return;
    setOrderModal({ ...orderModal, pairs: [...ADMIN_TEMPLATE_PAIRS], successMsg: '', error: '' });
  };

  const handleSaveOrder = async () => {
    if (!orderModal) return;
    setOrderModal(prev => prev ? { ...prev, saving: true, error: '', successMsg: '' } : null);
    try {
      const keys = orderModal.pairs.map(p => p.baseKey);
      await adminApi.updateTemplateOrder(keys);
      setOrderModal(prev => prev ? {
        ...prev,
        saving: false,
        successMsg: '✅ Display order updated successfully! The first 10 items will appear on the Home Page and all 21 in the Main Catalog.',
      } : null);
    } catch (err: any) {
      setOrderModal(prev => prev ? { ...prev, saving: false, error: err.message || 'Failed to save order' } : null);
    }
  };

  const loadTemplates = () => {
    setLoading(true);
    adminApi.adminListTemplates(statusFilter || undefined, categoryFilter || undefined, searchQuery || undefined)
      .then(setTemplates)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadTemplates();
  }, [statusFilter, categoryFilter, searchQuery]);

  const handleMigrate = async () => {
    if (!window.confirm('Are you sure you want to migrate seed templates into MongoDB? Existing admin edits will be preserved.')) return;
    try {
      await adminApi.adminMigrateSeed();
      loadTemplates();
    } catch (err: any) {
      alert(`Migration failed: ${err.message}`);
    }
  };

  const handleEdit = async (template: any) => {
    if (template.status === 'draft' && !template.locked) {
      navigate(`/templates/${template.id}/edit`);
    } else {
      const nextVer = (template.version || 0) + 1;
      const ok = window.confirm(
        `Editing this ${template.status} template will create a new Draft (v${nextVer}).\n\nThe current published version will remain active for lawyers until you publish the new draft.\n\nDo you want to continue?`
      );
      if (!ok) return;
      try {
        const res = await adminApi.adminCloneTemplate(template.id);
        const targetId = res.template?.id || res.id || template.id;
        navigate(`/templates/${targetId}/edit`);
      } catch (err: any) {
        alert(`Failed to start draft version: ${err.message}`);
      }
    }
  };

  const handleOpenPreview = async (template: any) => {
    setPreviewModal({
      open: true,
      template,
      previewEn: '',
      previewGu: '',
      lang: 'en',
      loading: true,
    });
    try {
      const res = await adminApi.adminPreviewTemplate(template.id, {});
      setPreviewModal(prev => prev ? {
        ...prev,
        previewEn: res.preview?.en?.content || res.content_en || 'No preview available',
        previewGu: res.preview?.gu?.content || res.content_gu || 'No preview available',
        loading: false,
      } : null);
    } catch (err: any) {
      alert(`Failed to load preview: ${err.message}`);
      setPreviewModal(null);
    }
  };

  const handleOpenHistory = async (template: any) => {
    setHistoryModal({ open: true, template, versions: [], loading: true });
    try {
      const versions = await adminApi.adminTemplateVersions(template.id);
      setHistoryModal({ open: true, template, versions, loading: false });
    } catch (err: any) {
      alert(`Failed to load version history: ${err.message}`);
      setHistoryModal(null);
    }
  };

  const handleOpenClone = (template: any) => {
    setCloneModal({
      open: true,
      template,
      newId: `${template.id}_copy_${Date.now().toString().slice(-4)}`,
      newNameEn: `${template.name_en} (Copy)`,
      newNameGu: `${template.name_gu} (નકલ)`,
    });
  };

  const handleExecuteClone = async () => {
    if (!cloneModal) return;
    try {
      const res = await adminApi.adminCloneTemplate(cloneModal.template.id, {
        as_new_template: true,
        new_id: cloneModal.newId,
        new_name_en: cloneModal.newNameEn,
        new_name_gu: cloneModal.newNameGu,
      });
      setCloneModal(null);
      const targetId = res.template?.id || res.id;
      navigate(`/templates/${targetId}/edit`);
    } catch (err: any) {
      alert(`Clone failed: ${err.message}`);
    }
  };

  const handlePublish = async (id: string) => {
    if (!window.confirm('Publish this draft template? It will become active and read-only for lawyers.')) return;
    try {
      await adminApi.adminPublishTemplate(id);
      loadTemplates();
    } catch (err: any) {
      alert(`Failed to publish: ${err.message}`);
    }
  };

  const handleArchive = async (id: string) => {
    if (!window.confirm('Archive this template? It will be hidden from lawyers but preserved in history.')) return;
    try {
      await adminApi.adminArchiveTemplate(id);
      loadTemplates();
    } catch (err: any) {
      alert(`Failed to archive: ${err.message}`);
    }
  };

  const handleExecuteDelete = async () => {
    if (!deleteModal || deleteModal.confirmText !== 'DELETE') return;
    setDeleteModal(prev => prev ? { ...prev, loading: true, error: '' } : null);
    try {
      await adminApi.adminDeleteTemplate(deleteModal.template.id);
      const deletedId = deleteModal.template.id;
      setDeleteModal(null);
      loadTemplates();
      alert(`Template '${deletedId}' has been permanently deleted from the catalog.`);
    } catch (err: any) {
      setDeleteModal(prev => prev ? { ...prev, loading: false, error: err.message } : null);
    }
  };

  const isShadowRow = (t: any) =>
    t.is_seed_template && (t.status === 'draft' || t.status === 'archived');

  const handleRemoveShadowDraft = async (t: any) => {
    const ok = window.confirm(
      `Remove Shadow Draft (${t.id})?\n\nThis will remove the ${t.status} record that is currently hiding the seeded template from the lawyer app. The published/seed template will remain unchanged.`
    );
    if (!ok) return;
    try {
      await adminApi.adminRemoveShadowDraft(t.id, true);
      loadTemplates();
    } catch (err: any) {
      alert(`Failed to remove shadow draft: ${err.message}`);
    }
  };

  const FIELD_TYPES = ['text', 'textarea', 'number', 'mobile', 'email', 'date', 'select', 'radio', 'checkbox'];

  const handleImportFile = async (file: File | undefined) => {
    if (!file) return;
    const isDocx = file.name.toLowerCase().endsWith('.docx');
    const isOdt = file.name.toLowerCase().endsWith('.odt');
    if (!isDocx && !isOdt) {
      setImportModal(prev => prev ? { ...prev, error: 'Unsupported file type. Only .docx Word or .odt LibreOffice documents are accepted for import.' } : prev);
      return;
    }
    const reader = new FileReader();
    reader.onload = async () => {
      const b64 = String(reader.result).split(',')[1] || '';
      setImportModal(prev => prev ? { ...prev, fileName: file.name, error: '', step: 'review' } : prev);
      try {
        const analysis = await adminApi.adminImportAnalyze(file.name, b64);
        const fields = (analysis.fields || []).map((f: any, i: number) => ({
          ...f,
          order: i + 1,
          _optionsText: (f.options || []).map((o: any) => o.label_gu || o.label_en || o.value).join('\n'),
        }));
        setImportModal(prev => prev ? {
          ...prev,
          analysis,
          fields,
          id: '',
          nameEn: analysis.suggested_name_en || file.name.replace(/\.(docx|odt)$/i, ''),
          nameGu: analysis.suggested_name_gu || '',
          category: analysis.suggested_category || 'General',
          error: '',
        } : prev);
      } catch (err: any) {
        setImportModal(prev => prev ? { ...prev, error: err.message, step: 'pick' } : prev);
      }
    };
    reader.onerror = () => {
      setImportModal(prev => prev ? { ...prev, error: 'Could not read the selected file.' } : prev);
    };
    reader.readAsDataURL(file);
  };

  const updateImportField = (idx: number, patch: any) => {
    setImportModal(prev => {
      if (!prev) return prev;
      const fields = prev.fields.map((f, i) => (i === idx ? { ...f, ...patch } : f));
      return { ...prev, fields };
    });
  };

  const handleImportCreate = async () => {
    if (!importModal || !importModal.analysis) return;
    if (!importModal.id || !importModal.nameEn || !importModal.nameGu) {
      setImportModal(prev => prev ? { ...prev, error: 'Template ID, English name and Gujarati name are required.' } : prev);
      return;
    }
    const fields = importModal.fields.map((f: any, i: number) => {
      const options = (f.type === 'select' || f.type === 'radio' || f.type === 'checkbox')
        ? (f._optionsText || '').split(/\n|,/).map((s: string) => s.trim()).filter(Boolean)
            .map((v: string) => ({ value: v, label_en: v, label_gu: v }))
        : (f.options || []);
      return {
        key: f.key,
        label_en: f.label_en || f.label_gu || f.key,
        label_gu: f.label_gu || f.label_en || f.key,
        type: f.type || 'text',
        required: !!f.required,
        order: i + 1,
        default_value: f.default_value ?? null,
        options,
        validation: f.validation ?? null,
      };
    });
    setImportModal(prev => prev ? { ...prev, step: 'creating', error: '' } : prev);
    try {
      const created = await adminApi.adminImportCreate({
        id: importModal.id,
        name_en: importModal.nameEn,
        name_gu: importModal.nameGu,
        category: importModal.category || 'General',
        description: `Imported from Word document: ${importModal.fileName}`,
        content_en: importModal.analysis.content_en || '',
        content_gu: importModal.analysis.draft_content_gu || '',
        fields,
        settings: importModal.analysis.settings || {},
      });
      setImportModal(null);
      navigate(`/templates/${created.id}/edit`);
    } catch (err: any) {
      setImportModal(prev => prev ? { ...prev, step: 'review', error: err.message } : prev);
    }
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Templates</h1>
          <p className="dashboard-desc">Manage legal document templates, custom fields, and version lifecycles</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn-secondary" onClick={handleOpenOrderModal} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>📐</span> Template Placement / Order
          </button>
          <button className="btn-secondary" onClick={handleMigrate}>Migrate Seed Templates</button>
          {isSuperAdmin && (
            <button className="btn-secondary" onClick={() => setImportModal({
              step: 'pick', fileName: '', error: '', analysis: null, id: '', nameEn: '', nameGu: '', category: 'General', fields: [],
            })}>+ Import Word Template</button>
          )}
          <button className="btn-primary" onClick={() => navigate('/templates/new')}>+ Create Template</button>
        </div>
      </div>

      <div className="filters-bar">
        <div className="filter-group">
          <label>Status:</label>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option value="">All Statuses</option>
            <option value="seed">Seed (Not in DB)</option>
            <option value="published">Published</option>
            <option value="draft">Draft</option>
            <option value="archived">Archived</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Category:</label>
          <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}>
            <option value="">All Categories</option>
            <option value="General">General</option>
            <option value="Civil">Civil</option>
            <option value="Criminal">Criminal</option>
            <option value="Bail">Bail</option>
            <option value="Family">Family</option>
            <option value="Revenue">Revenue</option>
          </select>
        </div>
        <div className="filter-group search-group">
          <input 
            type="text" 
            placeholder="Search by name, ID, or aliases..." 
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <div className="dashboard-loading">
          <div className="spinner"></div>
          <p>Loading templates...</p>
        </div>
      ) : error ? (
        <div className="dashboard-error">
          <p>Failed to load templates: {error}</p>
          <button onClick={loadTemplates}>Retry</button>
        </div>
      ) : (
        <div className="dashboard-table-card">
          {templates.length === 0 ? (
            <p className="no-data">No templates found matching your criteria</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name (EN / GU)</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Version</th>
                  <th>Fields</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {templates.map(t => (
                  <tr key={t.id}>
                    <td>
                      <div><strong>{t.name_en}</strong></div>
                      <div className="text-gu" style={{ fontSize: '0.88rem', color: '#666' }}>{t.name_gu}</div>
                      <code style={{ fontSize: '0.75rem', color: '#888' }}>{t.id}</code>
                    </td>
                    <td>
                      <span className="category-pill">{t.category}</span>
                      {t.sub_category && <div style={{ fontSize: '0.75rem', color: '#888', marginTop: '2px' }}>{t.sub_category}</div>}
                    </td>
                    <td><StatusBadge status={t.status} /></td>
                    <td>
                      <span className="version-badge">v{t.version || 1}</span>
                      {/* The lock is the published-version lock: only published
                          templates are immutable (edits go through Clone). A
                          stray `locked` flag on a draft/seed/archived record is
                          not a real lock and must not show a lock icon. */}
                      {t.locked && t.status === 'published' && <span style={{ marginLeft: '4px', fontSize: '0.75rem', color: '#888' }}>🔒</span>}
                    </td>
                    <td>{t.fields?.length || 0} fields</td>
                    <td>
                      <div className="action-buttons">
                        <button className="action-btn" title="Preview Document" onClick={() => handleOpenPreview(t)}>
                          👁️ View
                        </button>
                        <button className="action-btn text-primary" title="Edit Template" onClick={() => handleEdit(t)}>
                          ✏️ Edit
                        </button>
                        <button className="action-btn" title="Clone Template" onClick={() => handleOpenClone(t)}>
                          📋 Clone
                        </button>
                        <button className="action-btn" title="Version History" onClick={() => handleOpenHistory(t)}>
                          📜 History
                        </button>
                        {t.status === 'draft' && (
                          <button className="action-btn text-success" title="Publish Draft" onClick={() => handlePublish(t.id)}>
                            🚀 Publish
                          </button>
                        )}
                        {t.status !== 'archived' && (
                          <button className="action-btn text-danger" title="Archive Template" onClick={() => handleArchive(t.id)}>
                            📦 Archive
                          </button>
                        )}
                        {isSuperAdmin && (
                          <button
                            className="action-btn text-danger"
                            title="Permanently Delete Template from Catalog"
                            style={{ color: '#dc2626', fontWeight: 500 }}
                            onClick={() => setDeleteModal({
                              open: true,
                              template: t,
                              confirmText: '',
                              loading: false,
                              error: '',
                            })}
                          >
                            🗑️ Delete
                          </button>
                        )}
                        {isSuperAdmin && isShadowRow(t) && (
                          <button
                            className="action-btn text-danger"
                            title="Remove the draft/archived record hiding the seed template from the lawyer app"
                            onClick={() => handleRemoveShadowDraft(t)}
                          >
                            🗑️ Remove Shadow Draft
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

      {/* Preview Modal */}
      {previewModal?.open && (
        <div className="modal-overlay" onClick={() => setPreviewModal(null)}>
          <div className="modal-card modal-lg" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3>Document Preview: {previewModal.template.name_en}</h3>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>{previewModal.template.name_gu}</p>
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <div className="lang-tabs">
                  <button 
                    className={`lang-tab ${previewModal.lang === 'en' ? 'active' : ''}`}
                    onClick={() => setPreviewModal({ ...previewModal, lang: 'en' })}
                  >
                    English
                  </button>
                  <button 
                    className={`lang-tab ${previewModal.lang === 'gu' ? 'active' : ''}`}
                    onClick={() => setPreviewModal({ ...previewModal, lang: 'gu' })}
                  >
                    ગુજરાતી
                  </button>
                </div>
                <button className="btn-icon" onClick={() => setPreviewModal(null)}>✕</button>
              </div>
            </div>
            <div className="modal-body">
              {previewModal.loading ? (
                <div className="dashboard-loading"><div className="spinner"></div><p>Rendering preview...</p></div>
              ) : (
                <div className="preview-paper">
                  <div 
                    className={`preview-rendered ${previewModal.lang === 'gu' ? 'text-gu' : 'content-en'}`}
                    style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', fontSize: '14px' }}
                  >
                    {previewModal.lang === 'gu' ? previewModal.previewGu : previewModal.previewEn}
                  </div>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setPreviewModal(null)}>Close</button>
              <button className="btn-primary" onClick={() => { setPreviewModal(null); handleEdit(previewModal.template); }}>
                Edit this Template
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Version History Modal */}
      {historyModal?.open && (
        <div className="modal-overlay" onClick={() => setHistoryModal(null)}>
          <div className="modal-card" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Version History: {historyModal.template.name_en}</h3>
              <button className="btn-icon" onClick={() => setHistoryModal(null)}>✕</button>
            </div>
            <div className="modal-body">
              {historyModal.loading ? (
                <div className="dashboard-loading"><div className="spinner"></div><p>Loading history...</p></div>
              ) : historyModal.versions.length === 0 ? (
                <p className="no-data">No previous published versions recorded for this template yet.</p>
              ) : (
                <div className="timeline">
                  {historyModal.versions.map((ver: any, idx: number) => (
                    <div key={idx} className="timeline-item">
                      <div className="timeline-badge">v{ver.version}</div>
                      <div className="timeline-content">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <strong>Version {ver.version} (Published)</strong>
                          <span style={{ fontSize: '0.75rem', color: '#888' }}>
                            {new Date(ver.created_at || ver.published_at).toLocaleString()}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#555', marginTop: '4px' }}>
                          Fields: {ver.fields?.length || 0} | Category: {ver.category}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#888', marginTop: '2px' }}>
                          Snapshot ID: <code>{ver.id}</code>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setHistoryModal(null)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Clone Modal */}
      {cloneModal?.open && (
        <div className="modal-overlay" onClick={() => setCloneModal(null)}>
          <div className="modal-card" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Clone Template as New Document</h3>
              <button className="btn-icon" onClick={() => setCloneModal(null)}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: '0.9rem', color: '#555', marginBottom: '16px' }}>
                This creates a completely independent new template copy with all fields, settings, and content prefilled.
              </p>
              <div className="form-group" style={{ marginBottom: '12px' }}>
                <label>New Template ID (Slug):</label>
                <input 
                  type="text" 
                  value={cloneModal.newId} 
                  onChange={e => setCloneModal({ ...cloneModal, newId: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })} 
                />
              </div>
              <div className="form-group" style={{ marginBottom: '12px' }}>
                <label>English Name:</label>
                <input 
                  type="text" 
                  value={cloneModal.newNameEn} 
                  onChange={e => setCloneModal({ ...cloneModal, newNameEn: e.target.value })} 
                />
              </div>
              <div className="form-group">
                <label>Gujarati Name:</label>
                <input 
                  type="text" 
                  className="text-gu"
                  value={cloneModal.newNameGu} 
                  onChange={e => setCloneModal({ ...cloneModal, newNameGu: e.target.value })} 
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setCloneModal(null)}>Cancel</button>
              <button className="btn-primary" onClick={handleExecuteClone}>Create Clone</button>
            </div>
          </div>
        </div>
      )}

      {/* Import Word Template Modal */}
      {importModal && (
        <div className="modal-overlay" onClick={() => { if (importModal.step !== 'creating') setImportModal(null); }}>
          <div className="modal-card modal-lg" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3>Import Word Template</h3>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>
                  Upload a .docx (Word) or .odt (LibreOffice Writer) — the source document stays unchanged; a new template draft is created from its analysis.
                </p>
              </div>
              <button className="btn-icon" disabled={importModal.step === 'creating'} onClick={() => setImportModal(null)}>✕</button>
            </div>
            <div className="modal-body">
              {importModal.error && (
                <div className="dashboard-error" style={{ marginBottom: '12px' }}>
                  <p>{importModal.error}</p>
                </div>
              )}

              {importModal.step === 'pick' && (
                <div>
                  <input
                    type="file"
                    accept=".docx,.odt"
                    onChange={e => handleImportFile(e.target.files?.[0] || undefined)}
                  />
                  <p style={{ fontSize: '0.8rem', color: '#888', marginTop: '8px' }}>
                    Only .docx and .odt files are supported. The document should normally contain two parts:
                    Page 1 (required information / field definitions) and Page 2 (the actual legal draft
                    with {"{{placeholder}}"} markers where lawyer data must appear).
                  </p>
                </div>
              )}

              {importModal.step === 'review' && importModal.analysis && (
                <div>
                  {/* Source document summary */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '16px' }}>
                    <span className="category-pill">Page: {importModal.analysis.page_size}</span>
                    <span className="category-pill">Margins: T{importModal.analysis.margins_cm.top_cm} / B{importModal.analysis.margins_cm.bottom_cm} / L{importModal.analysis.margins_cm.left_cm} / R{importModal.analysis.margins_cm.right_cm} cm</span>
                    <span className="category-pill">Font: {importModal.analysis.fonts.gujarati_font}</span>
                    <span className="category-pill">Body: {importModal.analysis.fonts.body_size} pt</span>
                    <span className="category-pill">Spacing: {importModal.analysis.line_spacing_pts} pt</span>
                    {!importModal.analysis.page_break_detected && (
                      <span className="category-pill" style={{ background: '#fff3cd', color: '#856404' }}>
                        No explicit page break detected — draft/spec split inferred
                      </span>
                    )}
                  </div>

                  <div className="form-group" style={{ marginBottom: '12px' }}>
                    <label>Template ID (Slug):</label>
                    <input
                      type="text"
                      value={importModal.id}
                      onChange={e => setImportModal({ ...importModal, id: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })}
                      placeholder="e.g. return_of_documents"
                    />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                    <div className="form-group">
                      <label>English Name:</label>
                      <input type="text" value={importModal.nameEn} onChange={e => setImportModal({ ...importModal, nameEn: e.target.value })} />
                    </div>
                    <div className="form-group">
                      <label>Gujarati Name:</label>
                      <input type="text" className="text-gu" value={importModal.nameGu} onChange={e => setImportModal({ ...importModal, nameGu: e.target.value })} />
                    </div>
                    <div className="form-group">
                      <label>Category:</label>
                      <select value={importModal.category} onChange={e => setImportModal({ ...importModal, category: e.target.value })}>
                        <option value="General">General</option>
                        <option value="Civil">Civil</option>
                        <option value="Criminal">Criminal</option>
                        <option value="Bail">Bail</option>
                        <option value="Family">Family</option>
                        <option value="Revenue">Revenue</option>
                      </select>
                    </div>
                  </div>

                  <h4 style={{ margin: '0 0 8px', fontSize: '1rem' }}>Extracted Fields ({importModal.fields.length})</h4>
                  {importModal.fields.length === 0 ? (
                    <p className="no-data">No fields could be detected automatically. You can add them later in the template editor.</p>
                  ) : (
                    <div className="table-scroll">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Key</th>
                            <th>Gujarati Label</th>
                            <th>English Label</th>
                            <th>Type</th>
                            <th>Req.</th>
                            <th>Options / Source</th>
                          </tr>
                        </thead>
                        <tbody>
                          {importModal.fields.map((f: any, i: number) => (
                            <tr key={i}>
                              <td>
                                <input
                                  style={{ width: '110px', fontFamily: 'monospace', fontSize: '0.75rem' }}
                                  value={f.key}
                                  onChange={e => updateImportField(i, { key: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })}
                                />
                              </td>
                              <td>
                                <input className="text-gu" value={f.label_gu || ''} onChange={e => updateImportField(i, { label_gu: e.target.value })} />
                              </td>
                              <td>
                                <input value={f.label_en || ''} onChange={e => updateImportField(i, { label_en: e.target.value })} />
                              </td>
                              <td>
                                <select value={f.type || 'text'} onChange={e => updateImportField(i, { type: e.target.value })}>
                                  {FIELD_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                                </select>
                              </td>
                              <td>
                                <input
                                  type="checkbox"
                                  checked={!!f.required}
                                  onChange={e => updateImportField(i, { required: e.target.checked })}
                                />
                              </td>
                              <td style={{ maxWidth: '220px' }}>
                                {['select', 'radio', 'checkbox'].includes(f.type) ? (
                                  <div>
                                    <textarea
                                      className="text-gu"
                                      rows={2}
                                      style={{ width: '100%', fontSize: '0.75rem' }}
                                      placeholder="One option per line (or comma-separated)"
                                      value={f._optionsText || ''}
                                      onChange={e => updateImportField(i, { _optionsText: e.target.value })}
                                    />
                                    <div style={{ fontSize: '0.7rem', color: '#999', marginTop: '2px' }}>
                                      {f.source === 'draft_placeholder' ? 'Draft {{placeholder}} · in draft: ' + (f.referenced_in_draft ? 'yes' : 'no') : (f.source_location || f.source)}
                                    </div>
                                  </div>
                                ) : (
                                  <span style={{ fontSize: '0.75rem', color: '#666' }}>
                                    {f.source === 'draft_placeholder' ? 'Draft {{placeholder}} · in draft: ' + (f.referenced_in_draft ? 'yes' : 'no') : (f.source_location || f.source)}
                                  </span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {importModal.analysis.unmapped && importModal.analysis.unmapped.length > 0 && (
                    <div style={{ marginTop: '16px' }}>
                      <h4 style={{ margin: '0 0 8px', fontSize: '1rem', color: '#b8860b' }}>
                        Unmapped / Review Required ({importModal.analysis.unmapped.length})
                      </h4>
                      <p style={{ fontSize: '0.8rem', color: '#888', margin: '0 0 8px' }}>
                        These items could not be reliably detected as fields. They are shown for review —
                        nothing is guessed. Add them as fields later in the template editor if needed.
                      </p>
                      <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.85rem', color: '#555' }}>
                        {importModal.analysis.unmapped.map((u: any, i: number) => (
                          <li key={i} style={{ marginBottom: '4px' }}>
                            <span className="text-gu">{u.text}</span>
                            <span style={{ color: '#999', marginLeft: '8px', fontSize: '0.75rem' }}>({u.source_location})</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div style={{ marginTop: '16px' }}>
                    <h4 style={{ margin: '0 0 8px', fontSize: '1rem' }}>Draft Preview (from the Word document)</h4>
                    <div className="preview-paper">
                      <pre className="text-gu" style={{ whiteSpace: 'pre-wrap', fontSize: '13px', margin: 0 }}>
                        {importModal.analysis.draft_content_gu.split('\n').slice(0, 12).join('\n')}
                        {importModal.analysis.draft_content_gu.split('\n').length > 12 ? '\n…' : ''}
                      </pre>
                    </div>
                    <p style={{ fontSize: '0.8rem', color: '#888', marginTop: '6px' }}>
                      Full draft content, formatting, fields and page settings can be edited after creation
                      in the template editor before publishing.
                    </p>
                  </div>
                </div>
              )}

              {importModal.step === 'creating' && (
                <div className="dashboard-loading">
                  <div className="spinner"></div>
                  <p>Creating draft template from the Word document...</p>
                </div>
              )}
            </div>
            {importModal.step === 'review' && (
              <div className="modal-footer">
                <button className="btn-secondary" onClick={() => setImportModal(null)}>Cancel</button>
                <button className="btn-primary" onClick={handleImportCreate}>
                  Create Draft Template
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Permanent Delete Modal */}
      {deleteModal?.open && (
        <div className="modal-overlay" onClick={() => { if (!deleteModal.loading) setDeleteModal(null); }}>
          <div className="modal-card" onClick={e => e.stopPropagation()} style={{ maxWidth: '540px' }}>
            <div className="modal-header" style={{ borderBottom: '1px solid #fee2e2' }}>
              <h3 style={{ color: '#b91c1c', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                ⚠️ Permanently Delete Template?
              </h3>
              <button className="btn-icon" disabled={deleteModal.loading} onClick={() => setDeleteModal(null)}>✕</button>
            </div>
            <div className="modal-body">
              {deleteModal.error && (
                <div className="dashboard-error" style={{ marginBottom: '12px' }}>
                  <p>{deleteModal.error}</p>
                </div>
              )}

              <p style={{ fontSize: '0.9rem', color: '#374151', lineHeight: '1.5', margin: '0 0 16px' }}>
                This will <strong>permanently remove</strong> the template from the active template catalog. Historical revisions and past generated documents will remain intact, but lawyers will no longer be able to create new applications with this template.
              </p>

              <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', padding: '12px', marginBottom: '16px', fontSize: '0.85rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', rowGap: '6px', columnGap: '8px', color: '#1f2937' }}>
                  <strong>Template Name:</strong> <span>{deleteModal.template.name_en}</span>
                  <strong>Gujarati Name:</strong> <span className="text-gu">{deleteModal.template.name_gu}</span>
                  <strong>Template ID:</strong> <code>{deleteModal.template.id}</code>
                  <strong>Current Status:</strong> <div><StatusBadge status={deleteModal.template.status} /></div>
                  <strong>Version:</strong> <span>v{deleteModal.template.version || 1}</span>
                </div>
              </div>

              <div className="form-group">
                <label style={{ fontSize: '0.85rem', fontWeight: 600, color: '#374151', marginBottom: '6px', display: 'block' }}>
                  To confirm permanent deletion, type <code style={{ backgroundColor: '#fee2e2', color: '#991b1b', padding: '2px 6px', borderRadius: '4px', fontWeight: 700 }}>DELETE</code> below:
                </label>
                <input
                  type="text"
                  placeholder="Type DELETE to confirm"
                  value={deleteModal.confirmText}
                  onChange={e => setDeleteModal({ ...deleteModal, confirmText: e.target.value })}
                  disabled={deleteModal.loading}
                  style={{ width: '100%', borderColor: deleteModal.confirmText === 'DELETE' ? '#dc2626' : undefined }}
                  autoFocus
                />
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn-secondary"
                disabled={deleteModal.loading}
                onClick={() => setDeleteModal(null)}
              >
                Cancel
              </button>
              <button
                className="btn-danger"
                style={{
                  backgroundColor: deleteModal.confirmText === 'DELETE' ? '#dc2626' : '#9ca3af',
                  borderColor: deleteModal.confirmText === 'DELETE' ? '#dc2626' : '#9ca3af',
                  cursor: deleteModal.confirmText === 'DELETE' ? 'pointer' : 'not-allowed',
                  color: '#fff',
                }}
                disabled={deleteModal.confirmText !== 'DELETE' || deleteModal.loading}
                onClick={handleExecuteDelete}
              >
                {deleteModal.loading ? 'Deleting...' : 'Permanently Delete Template'}
              </button>
            </div>
          </div>
        </div>
      )}

      {orderModal && (
        <div className="modal-overlay" style={{ zIndex: 1100 }}>
          <div className="modal-content" style={{ maxWidth: '850px', width: '90%', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>
            <div className="modal-header">
              <div>
                <h2 style={{ margin: 0, fontSize: '1.25rem' }}>📐 Template Placement & Display Order / પ્લેસમેન્ટ ક્રમ</h2>
                <p style={{ margin: '4px 0 0', fontSize: '0.82rem', color: '#6b7280' }}>
                  Authoritative ordering for all 21 templates. The <strong>first 10 templates</strong> appear on the Home Page.
                </p>
              </div>
              <button
                className="btn-icon"
                onClick={() => setOrderModal(null)}
                style={{ fontSize: '1.2rem', background: 'none', border: 'none', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div className="modal-body" style={{ overflowY: 'auto', flex: 1, padding: '16px' }}>
              {orderModal.error && (
                <div style={{ backgroundColor: '#fee2e2', color: '#991b1b', padding: '10px 14px', borderRadius: '6px', marginBottom: '12px', fontSize: '0.88rem' }}>
                  {orderModal.error}
                </div>
              )}
              {orderModal.successMsg && (
                <div style={{ backgroundColor: '#ecfdf5', color: '#065f46', padding: '10px 14px', borderRadius: '6px', marginBottom: '12px', fontSize: '0.88rem', fontWeight: 600 }}>
                  {orderModal.successMsg}
                </div>
              )}

              {orderModal.loading ? (
                <div style={{ textAlign: 'center', padding: '40px' }}>
                  <div className="spinner" style={{ margin: '0 auto 12px' }}></div>
                  <p>Loading authoritative order...</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {orderModal.pairs.map((pair, index) => {
                    const isTop10 = index < 10;
                    return (
                      <div
                        key={pair.baseKey}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '10px 14px',
                          borderRadius: '8px',
                          border: isTop10 ? '1px solid #c5a059' : '1px solid #e5e7eb',
                          backgroundColor: isTop10 ? '#fffdf7' : '#fafafa',
                          gap: '12px',
                        }}
                      >
                        {/* Position Number & Destination Badge */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: '150px' }}>
                          <span
                            style={{
                              width: '28px',
                              height: '28px',
                              borderRadius: '50%',
                              backgroundColor: isTop10 ? '#0b1b3d' : '#9ca3af',
                              color: '#fff',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '0.82rem',
                              fontWeight: 700,
                            }}
                          >
                            {index + 1}
                          </span>
                          <span
                            style={{
                              fontSize: '0.72rem',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: '999px',
                              backgroundColor: isTop10 ? '#fef3c7' : '#f3f4f6',
                              color: isTop10 ? '#92400e' : '#6b7280',
                              border: isTop10 ? '1px solid #fde68a' : '1px solid #e5e7eb',
                            }}
                          >
                            {isTop10 ? '🏠 Home (1-10)' : 'Catalog (11-21)'}
                          </span>
                        </div>

                        {/* Titles */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#111827' }}>
                            {pair.name_gu}
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '2px' }}>
                            {pair.name_en}
                          </div>
                        </div>

                        {/* Category */}
                        <div style={{ minWidth: '80px', textAlign: 'center' }}>
                          <span
                            style={{
                              fontSize: '0.72rem',
                              fontWeight: 600,
                              padding: '2px 8px',
                              borderRadius: '4px',
                              backgroundColor: '#e0e7ff',
                              color: '#3730a3',
                            }}
                          >
                            {pair.category}
                          </span>
                        </div>

                        {/* Move Actions */}
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button
                            type="button"
                            className="btn-secondary"
                            disabled={index === 0 || orderModal.saving}
                            onClick={() => moveOrder(index, 'up')}
                            style={{ padding: '4px 8px', fontSize: '0.78rem', minWidth: '32px' }}
                            title="Move Up"
                          >
                            ↑
                          </button>
                          <button
                            type="button"
                            className="btn-secondary"
                            disabled={index === orderModal.pairs.length - 1 || orderModal.saving}
                            onClick={() => moveOrder(index, 'down')}
                            style={{ padding: '4px 8px', fontSize: '0.78rem', minWidth: '32px' }}
                            title="Move Down"
                          >
                            ↓
                          </button>
                          <button
                            type="button"
                            className="btn-secondary"
                            disabled={index === 0 || orderModal.saving}
                            onClick={() => moveOrder(index, 'top')}
                            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                            title="Move to Top"
                          >
                            Top
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={resetToDefaultOrder}
                disabled={orderModal.saving || orderModal.loading}
                style={{ color: '#b45309' }}
              >
                🔄 Reset to Default
              </button>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setOrderModal(null)}
                  disabled={orderModal.saving}
                >
                  Close
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleSaveOrder}
                  disabled={orderModal.saving || orderModal.loading}
                  style={{ backgroundColor: '#0b1b3d' }}
                >
                  {orderModal.saving ? 'Saving...' : 'Save Display Order (ઓર્ડર સેવ કરો)'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

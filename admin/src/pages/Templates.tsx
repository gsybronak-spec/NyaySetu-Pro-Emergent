import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminApi } from '../lib/api';
import StatusBadge from '../components/StatusBadge';

export default function Templates() {
  const navigate = useNavigate();
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

  return (
    <div className="dashboard">
      <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Templates</h1>
          <p className="dashboard-desc">Manage legal document templates, custom fields, and version lifecycles</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn-secondary" onClick={handleMigrate}>Migrate Seed Templates</button>
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
                      {t.locked && <span style={{ marginLeft: '4px', fontSize: '0.75rem', color: '#888' }}>🔒</span>}
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
    </div>
  );
}

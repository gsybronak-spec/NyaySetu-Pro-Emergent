import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { adminApi } from '../lib/api';
import StatusBadge from '../components/StatusBadge';

const BUILT_IN_PLACEHOLDERS = [
  'advocate_name', 'today', 'district', 'court', 
  'case_number', 'case_type', 'party_name', 'opposite_party'
];

interface FieldOption {
  label_en: string;
  label_gu: string;
  value: string;
}

interface TemplateField {
  key: string;
  label_en: string;
  label_gu: string;
  type: string;
  required: boolean;
  order: number;
  default_value?: string;
  options?: FieldOption[];
}

export default function TemplateEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = !!id;
  
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  
  // Preview & Validation
  const [previewEn, setPreviewEn] = useState('');
  const [previewGu, setPreviewGu] = useState('');
  const [validation, setValidation] = useState<{ valid: boolean; unknown: string[]; unused: string[]; duplicate_keys?: string[] } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  
  // Active expanded options index
  const [expandedOptionIdx, setExpandedOptionIdx] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'content' | 'settings' | 'preview'>('content');

  const [template, setTemplate] = useState<any>({
    name_en: '',
    name_gu: '',
    category: 'General',
    sub_category: '',
    description: '',
    tags: [],
    aliases: [],
    case_types: [],
    courts: [],
    jurisdiction: '',
    status: 'draft',
    version: 1,
    content_en: '',
    content_gu: '',
    fields: [] as TemplateField[],
    settings: {
      margin_top_cm: 2.5,
      margin_bottom_cm: 2.5,
      margin_left_cm: 2.5,
      margin_right_cm: 2.5,
      gujarati_font: 'Noto Sans Gujarati',
      english_font: 'Times-Roman',
      body_size: 12,
      heading_size: 13,
      line_spacing: 18,
      paragraph_spacing: 6,
      page_size: 'A4',
    }
  });
  
  const contentEnRef = useRef<HTMLTextAreaElement>(null);
  const contentGuRef = useRef<HTMLTextAreaElement>(null);
  const [lastFocused, setLastFocused] = useState<'en'|'gu'>('en');

  useEffect(() => {
    if (isEdit) {
      adminApi.adminGetTemplate(id!)
        .then(data => {
          setTemplate({
            ...data,
            fields: (data.fields || []).map((f: any, idx: number) => ({
              key: f.key || '',
              label_en: f.label_en || '',
              label_gu: f.label_gu || '',
              type: f.type || 'text',
              required: f.required !== false,
              order: f.order !== undefined ? f.order : idx,
              default_value: f.default_value || '',
              options: f.options || [],
            })),
            settings: data.settings || {
              margin_top_cm: 2.5,
              margin_bottom_cm: 2.5,
              margin_left_cm: 2.5,
              margin_right_cm: 2.5,
              gujarati_font: 'Noto Sans Gujarati',
              english_font: 'Times-Roman',
              body_size: 12,
              heading_size: 13,
              line_spacing: 18,
              paragraph_spacing: 6,
              page_size: 'A4',
            }
          });
        })
        .catch(err => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [id, isEdit]);

  const handleChange = (field: string, value: any) => {
    setTemplate((prev: any) => ({ ...prev, [field]: value }));
  };

  const handleSettingsChange = (key: string, value: any) => {
    setTemplate((prev: any) => ({
      ...prev,
      settings: {
        ...(prev.settings || {}),
        [key]: value,
      }
    }));
  };

  const handleArrayChange = (field: string, strValue: string) => {
    const arr = strValue.split(',').map(s => s.trim()).filter(Boolean);
    handleChange(field, arr);
  };

  // Field Operations
  const addField = () => {
    const newIdx = template.fields.length;
    const newField: TemplateField = {
      key: `field_${newIdx + 1}`,
      label_en: `Field ${newIdx + 1}`,
      label_gu: `વિગત ${newIdx + 1}`,
      type: 'text',
      required: true,
      order: newIdx,
      options: [],
    };
    setTemplate((prev: any) => ({
      ...prev,
      fields: [...prev.fields, newField]
    }));
  };

  const updateFieldKey = (index: number, newKey: string) => {
    const oldKey = template.fields[index].key;
    if (oldKey && oldKey !== newKey && (template.content_en?.includes(`{{${oldKey}}}`) || template.content_gu?.includes(`{{${oldKey}}}`))) {
      const confirmChange = window.confirm(
        `Warning: Changing field key from '{{${oldKey}}}' to '{{${newKey}}}' may break existing references in the document content.\n\nDo you want to proceed?`
      );
      if (!confirmChange) return;
    }
    const cleanKey = newKey.toLowerCase().replace(/[^a-z0-9_]/g, '_');
    updateField(index, 'key', cleanKey);
  };

  const updateField = (index: number, key: string, value: any) => {
    const newFields = [...template.fields];
    newFields[index] = { ...newFields[index], [key]: value };
    handleChange('fields', newFields);
  };

  const duplicateField = (index: number) => {
    const src = template.fields[index];
    const dup: TemplateField = {
      ...src,
      key: `${src.key}_copy`,
      label_en: `${src.label_en} (Copy)`,
      label_gu: `${src.label_gu} (નકલ)`,
      order: template.fields.length,
      options: src.options ? JSON.parse(JSON.stringify(src.options)) : [],
    };
    setTemplate((prev: any) => ({
      ...prev,
      fields: [...prev.fields, dup]
    }));
  };

  const removeField = (index: number) => {
    const field = template.fields[index];
    if (template.content_en?.includes(`{{${field.key}}}`) || template.content_gu?.includes(`{{${field.key}}}`)) {
      if (!window.confirm(`Field '{{${field.key}}}' is used in the template content. Are you sure you want to delete it?`)) {
        return;
      }
    }
    const newFields = template.fields.filter((_: any, i: number) => i !== index);
    handleChange('fields', newFields);
    if (expandedOptionIdx === index) setExpandedOptionIdx(null);
  };

  const moveField = (index: number, direction: 'up' | 'down') => {
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === template.fields.length - 1) return;
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    const newFields = [...template.fields];
    const temp = newFields[index];
    newFields[index] = newFields[targetIdx];
    newFields[targetIdx] = temp;
    newFields.forEach((f, idx) => { f.order = idx; });
    handleChange('fields', newFields);
  };

  // Option Operations for Select/Radio/Checkbox
  const addOption = (fieldIdx: number) => {
    const field = template.fields[fieldIdx];
    const opts = field.options || [];
    const newOpt: FieldOption = {
      label_en: `Option ${opts.length + 1}`,
      label_gu: `વિકલ્પ ${opts.length + 1}`,
      value: `option_${opts.length + 1}`,
    };
    updateField(fieldIdx, 'options', [...opts, newOpt]);
  };

  const updateOption = (fieldIdx: number, optIdx: number, key: string, value: string) => {
    const field = template.fields[fieldIdx];
    const opts = [...(field.options || [])];
    opts[optIdx] = { ...opts[optIdx], [key]: value };
    updateField(fieldIdx, 'options', opts);
  };

  const removeOption = (fieldIdx: number, optIdx: number) => {
    const field = template.fields[fieldIdx];
    const opts = (field.options || []).filter((_: any, i: number) => i !== optIdx);
    updateField(fieldIdx, 'options', opts);
  };

  const moveOption = (fieldIdx: number, optIdx: number, direction: 'up' | 'down') => {
    const field = template.fields[fieldIdx];
    const opts = [...(field.options || [])];
    if (direction === 'up' && optIdx === 0) return;
    if (direction === 'down' && optIdx === opts.length - 1) return;
    const target = direction === 'up' ? optIdx - 1 : optIdx + 1;
    const temp = opts[optIdx];
    opts[optIdx] = opts[target];
    opts[target] = temp;
    updateField(fieldIdx, 'options', opts);
  };

  // Placeholder insertion
  const insertPlaceholder = (key: string) => {
    const ref = lastFocused === 'en' ? contentEnRef : contentGuRef;
    if (!ref.current) return;
    
    const textarea = ref.current;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const placeholder = `{{${key}}}`;
    
    const newText = text.substring(0, start) + placeholder + text.substring(end);
    
    if (lastFocused === 'en') {
      handleChange('content_en', newText);
    } else {
      handleChange('content_gu', newText);
    }
    
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + placeholder.length, start + placeholder.length);
    }, 0);
  };

  // Save / Publish
  const handleSaveDraft = async () => {
    try {
      setSaving(true);
      if (isEdit) {
        await adminApi.adminUpdateTemplate(id!, template);
        alert('Draft saved successfully!');
      } else {
        const created = await adminApi.adminCreateTemplate(template);
        alert('Template created as draft!');
        navigate(`/templates/${created.id}/edit`, { replace: true });
      }
    } catch (err: any) {
      alert(`Failed to save draft: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!window.confirm('Publish this template? It will become active and immutable for lawyers.')) return;
    try {
      setSaving(true);
      let targetId = id;
      if (!isEdit) {
        const created = await adminApi.adminCreateTemplate(template);
        targetId = created.id;
      } else {
        await adminApi.adminUpdateTemplate(id!, template);
      }
      const res = await adminApi.adminPublishTemplate(targetId!);
      alert(`Template published successfully as Version ${res.template?.version || 1}!`);
      navigate('/templates');
    } catch (err: any) {
      alert(`Failed to publish: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleBranchDraft = async () => {
    try {
      setSaving(true);
      const res = await adminApi.adminCloneTemplate(id!);
      const targetId = res.template?.id || res.id || id;
      navigate(`/templates/${targetId}/edit`);
    } catch (err: any) {
      alert(`Failed to create draft: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handlePreview = async () => {
    setPreviewLoading(true);
    try {
      const res = await adminApi.adminPreviewTemplate(id || 'preview_temp', {
        content_en: template.content_en,
        content_gu: template.content_gu,
        name_en: template.name_en,
        name_gu: template.name_gu,
        fields: template.fields,
        settings: template.settings,
      });
      // Correct property accesses:
      setPreviewEn(res.preview?.en?.content || '');
      setPreviewGu(res.preview?.gu?.content || '');
      setValidation(res.validation || null);
    } catch (err: any) {
      alert(`Preview failed: ${err.message}`);
    } finally {
      setPreviewLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Loading template editor...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error">
        <p>Error: {error}</p>
        <button onClick={() => navigate('/templates')}>Back to Templates</button>
      </div>
    );
  }

  const isLocked = template.status === 'published' || template.status === 'archived';
  const customPlaceholders = template.fields.map((f: any) => f.key).filter(Boolean);

  return (
    <div className="editor-page">
      <div className="editor-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="btn-icon" onClick={() => navigate('/templates')}>←</button>
          <h2>{isEdit ? `Edit: ${template.name_en}` : 'Create New Template'}</h2>
          {isEdit && <StatusBadge status={template.status} />}
          {isEdit && <span className="version-badge">v{template.version || 1}</span>}
        </div>
        <div className="editor-actions">
          {!isLocked ? (
            <>
              <button className="btn-secondary" onClick={handleSaveDraft} disabled={saving}>💾 Save Draft</button>
              <button className="btn-success" onClick={handlePublish} disabled={saving}>🚀 Publish</button>
            </>
          ) : (
            <button className="btn-primary" onClick={handleBranchDraft} disabled={saving}>✏️ Create Draft Version (v{(template.version || 1) + 1})</button>
          )}
        </div>
      </div>

      {isLocked && (
        <div className="locked-warning">
          🔒 <strong>Locked (Published v{template.version}):</strong> This published version is active and immutable.
          <button className="btn-link" style={{ marginLeft: '12px', fontWeight: 'bold' }} onClick={handleBranchDraft}>
            Create Draft Version to Edit
          </button>
        </div>
      )}

      {/* Editor Navigation Tabs */}
      <div className="editor-tabs">
        <button 
          className={`tab-btn ${activeTab === 'content' ? 'active' : ''}`}
          onClick={() => setActiveTab('content')}
        >
          📝 Document & Fields
        </button>
        <button 
          className={`tab-btn ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          ⚙️ Page & Typography Settings
        </button>
        <button 
          className={`tab-btn ${activeTab === 'preview' ? 'active' : ''}`}
          onClick={() => { setActiveTab('preview'); handlePreview(); }}
        >
          👁️ Live Preview & Validation
        </button>
      </div>

      {activeTab === 'content' && (
        <>
          {/* Metadata Section */}
          <div className="editor-section">
            <h3>1. Template Metadata & Case Matching</h3>
            <div className="grid-2">
              <div className="form-group">
                <label>Name (English) *</label>
                <input 
                  type="text" 
                  value={template.name_en} 
                  onChange={e => handleChange('name_en', e.target.value)} 
                  disabled={isLocked} 
                  placeholder="e.g. Adjournment Application"
                />
              </div>
              <div className="form-group">
                <label>Name (Gujarati) *</label>
                <input 
                  type="text" 
                  className="text-gu" 
                  value={template.name_gu} 
                  onChange={e => handleChange('name_gu', e.target.value)} 
                  disabled={isLocked} 
                  placeholder="દા.ત. મુદત અરજી"
                />
              </div>
              <div className="form-group">
                <label>Category</label>
                <select value={template.category} onChange={e => handleChange('category', e.target.value)} disabled={isLocked}>
                  <option value="General">General</option>
                  <option value="Civil">Civil</option>
                  <option value="Criminal">Criminal</option>
                  <option value="Bail">Bail</option>
                  <option value="Family">Family</option>
                  <option value="Revenue">Revenue</option>
                </select>
              </div>
              <div className="form-group">
                <label>Sub-category</label>
                <input 
                  type="text" 
                  value={template.sub_category || ''} 
                  onChange={e => handleChange('sub_category', e.target.value)} 
                  disabled={isLocked} 
                  placeholder="e.g. Procedural, Interim Relief"
                />
              </div>
              <div className="form-group" style={{ gridColumn: 'span 2' }}>
                <label>Description / Usage Note</label>
                <textarea 
                  rows={2}
                  value={template.description || ''} 
                  onChange={e => handleChange('description', e.target.value)} 
                  disabled={isLocked} 
                  placeholder="Brief guidance for advocates when selecting this template..."
                />
              </div>
              <div className="form-group">
                <label>Aliases / Search Keywords (comma-separated)</label>
                <input 
                  type="text" 
                  value={template.aliases?.join(', ') || ''} 
                  onChange={e => handleArrayChange('aliases', e.target.value)} 
                  disabled={isLocked} 
                  placeholder="mudat, adjournment, મુદત"
                />
              </div>
              <div className="form-group">
                <label>Matching Case Types (comma-separated IDs)</label>
                <input 
                  type="text" 
                  value={template.case_types?.join(', ') || ''} 
                  onChange={e => handleArrayChange('case_types', e.target.value)} 
                  disabled={isLocked} 
                  placeholder="civil_suit, criminal_case, bail_regular"
                />
              </div>
            </div>
          </div>

          {/* Fields Management Section */}
          <div className="editor-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3>2. Template Custom Fields ({template.fields.length})</h3>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>
                  Define input fields for advocates. Supported types: text, textarea, number, date, select, radio, checkbox.
                </p>
              </div>
              {!isLocked && <button className="btn-secondary btn-sm" onClick={addField}>+ Add New Field</button>}
            </div>
            
            {template.fields.length === 0 ? (
              <p className="no-data">No custom fields defined yet. Click "+ Add New Field" above.</p>
            ) : (
              <div className="fields-table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th style={{ width: '40px' }}>#</th>
                      <th>Placeholder Key</th>
                      <th>Label (EN)</th>
                      <th>Label (GU)</th>
                      <th>Type</th>
                      <th>Req</th>
                      <th>Default Value</th>
                      {!isLocked && <th>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {template.fields.map((field: TemplateField, idx: number) => (
                      <React.Fragment key={idx}>
                        <tr>
                          <td><strong>{idx + 1}</strong></td>
                          <td>
                            <input 
                              type="text" 
                              className="table-input" 
                              value={field.key} 
                              onChange={e => updateFieldKey(idx, e.target.value)} 
                              disabled={isLocked} 
                              placeholder="key_name"
                            />
                          </td>
                          <td>
                            <input 
                              type="text" 
                              className="table-input" 
                              value={field.label_en} 
                              onChange={e => updateField(idx, 'label_en', e.target.value)} 
                              disabled={isLocked} 
                            />
                          </td>
                          <td>
                            <input 
                              type="text" 
                              className="table-input text-gu" 
                              value={field.label_gu} 
                              onChange={e => updateField(idx, 'label_gu', e.target.value)} 
                              disabled={isLocked} 
                            />
                          </td>
                          <td>
                            <select 
                              className="table-input" 
                              value={field.type} 
                              onChange={e => updateField(idx, 'type', e.target.value)} 
                              disabled={isLocked}
                            >
                              <option value="text">Text</option>
                              <option value="textarea">Textarea</option>
                              <option value="number">Number</option>
                              <option value="date">Date</option>
                              <option value="select">Dropdown Select</option>
                              <option value="radio">Radio Buttons</option>
                              <option value="checkbox">Checkbox</option>
                            </select>
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            <input 
                              type="checkbox" 
                              checked={field.required} 
                              onChange={e => updateField(idx, 'required', e.target.checked)} 
                              disabled={isLocked} 
                            />
                          </td>
                          <td>
                            <input 
                              type="text" 
                              className="table-input" 
                              value={field.default_value || ''} 
                              onChange={e => updateField(idx, 'default_value', e.target.value)} 
                              disabled={isLocked} 
                              placeholder="Optional default"
                            />
                          </td>
                          {!isLocked && (
                            <td>
                              <div style={{ display: 'flex', gap: '4px' }}>
                                <button className="btn-icon" title="Move Up" onClick={() => moveField(idx, 'up')} disabled={idx === 0}>↑</button>
                                <button className="btn-icon" title="Move Down" onClick={() => moveField(idx, 'down')} disabled={idx === template.fields.length - 1}>↓</button>
                                <button className="btn-icon" title="Duplicate Field" onClick={() => duplicateField(idx)}>📋</button>
                                {['select', 'radio', 'checkbox'].includes(field.type) && (
                                  <button 
                                    className={`btn-icon ${expandedOptionIdx === idx ? 'text-primary' : ''}`}
                                    title="Manage Options"
                                    onClick={() => setExpandedOptionIdx(expandedOptionIdx === idx ? null : idx)}
                                  >
                                    ⚙️ Options ({field.options?.length || 0})
                                  </button>
                                )}
                                <button className="btn-icon text-danger" title="Delete Field" onClick={() => removeField(idx)}>✕</button>
                              </div>
                            </td>
                          )}
                        </tr>

                        {/* Options Manager Row for select / radio / checkbox */}
                        {expandedOptionIdx === idx && ['select', 'radio', 'checkbox'].includes(field.type) && (
                          <tr>
                            <td colSpan={8} style={{ backgroundColor: '#fcfcfc', padding: '12px 24px', borderLeft: '4px solid #0B1B3D' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                <strong>Options for "{field.label_en || field.key}":</strong>
                                {!isLocked && <button className="btn-secondary btn-sm" onClick={() => addOption(idx)}>+ Add Option</button>}
                              </div>
                              {(!field.options || field.options.length === 0) ? (
                                <p style={{ fontSize: '0.85rem', color: '#888', margin: 0 }}>No options added. Click "+ Add Option" to define choices.</p>
                              ) : (
                                <table style={{ width: '100%', fontSize: '0.85rem' }}>
                                  <thead>
                                    <tr>
                                      <th>Option Value</th>
                                      <th>Label (English)</th>
                                      <th>Label (Gujarati)</th>
                                      {!isLocked && <th style={{ width: '100px' }}>Actions</th>}
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {field.options.map((opt: FieldOption, optIdx: number) => (
                                      <tr key={optIdx}>
                                        <td>
                                          <input 
                                            type="text" 
                                            className="table-input" 
                                            value={opt.value} 
                                            onChange={e => updateOption(idx, optIdx, 'value', e.target.value)} 
                                            disabled={isLocked}
                                            placeholder="value_key"
                                          />
                                        </td>
                                        <td>
                                          <input 
                                            type="text" 
                                            className="table-input" 
                                            value={opt.label_en} 
                                            onChange={e => updateOption(idx, optIdx, 'label_en', e.target.value)} 
                                            disabled={isLocked}
                                            placeholder="English display"
                                          />
                                        </td>
                                        <td>
                                          <input 
                                            type="text" 
                                            className="table-input text-gu" 
                                            value={opt.label_gu} 
                                            onChange={e => updateOption(idx, optIdx, 'label_gu', e.target.value)} 
                                            disabled={isLocked}
                                            placeholder="ગુજરાતી દર્શાવ"
                                          />
                                        </td>
                                        {!isLocked && (
                                          <td>
                                            <button className="btn-icon" title="Move Up" onClick={() => moveOption(idx, optIdx, 'up')} disabled={optIdx === 0}>↑</button>
                                            <button className="btn-icon" title="Move Down" onClick={() => moveOption(idx, optIdx, 'down')} disabled={optIdx === field.options!.length - 1}>↓</button>
                                            <button className="btn-icon text-danger" title="Delete Option" onClick={() => removeOption(idx, optIdx)}>✕</button>
                                          </td>
                                        )}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              )}
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Content Editor Section */}
          <div className="editor-section">
            <h3>3. Document Content & Placeholders</h3>
            
            {/* Clickable Placeholder Palette */}
            <div className="palette-container">
              <div className="palette-section">
                <span className="palette-title">System Auto-Fill:</span>
                {BUILT_IN_PLACEHOLDERS.map(p => (
                  <button key={p} className="palette-btn" onClick={() => insertPlaceholder(p)} disabled={isLocked} title={`Auto-filled from case/advocate`}>
                    + {`{{${p}}}`}
                  </button>
                ))}
              </div>
              {customPlaceholders.length > 0 && (
                <div className="palette-section" style={{ marginTop: '8px' }}>
                  <span className="palette-title">Template Custom Fields:</span>
                  {customPlaceholders.map((p: string) => (
                    <button key={p} className="palette-btn custom" onClick={() => insertPlaceholder(p)} disabled={isLocked} title={`Dynamic template field`}>
                      + {`{{${p}}}`}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Split Content Panes */}
            <div className="split-pane">
              <div className="pane">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label className="pane-label">English Document Content</label>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>Monospace / Latin</span>
                </div>
                <textarea
                  ref={contentEnRef}
                  className="content-textarea content-en"
                  rows={16}
                  value={template.content_en}
                  onChange={e => handleChange('content_en', e.target.value)}
                  onFocus={() => setLastFocused('en')}
                  disabled={isLocked}
                  placeholder="IN THE COURT OF {{court}}&#10;&#10;{{party_name}} ... Applicant&#10;VERSUS&#10;{{opposite_party}} ... Opponent..."
                />
              </div>
              <div className="pane">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label className="pane-label">Gujarati Document Content</label>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>ગુજરાતી લિપિ / Lohit Gujarati</span>
                </div>
                <textarea
                  ref={contentGuRef}
                  className="content-textarea content-gu text-gu"
                  rows={16}
                  value={template.content_gu}
                  onChange={e => handleChange('content_gu', e.target.value)}
                  onFocus={() => setLastFocused('gu')}
                  disabled={isLocked}
                  placeholder="માનનીય ન્યાયાલય {{court}} સમક્ષ&#10;&#10;{{party_name}} ... અરજદાર&#10;વિરૂદ્ધ&#10;{{opposite_party}} ... સામાવાળા..."
                />
              </div>
            </div>
          </div>
        </>
      )}

      {activeTab === 'settings' && (
        <div className="editor-section">
          <h3>Page & Typography Settings</h3>
          <p style={{ fontSize: '0.85rem', color: '#666', marginBottom: '20px' }}>
            Configure the paper size, page margins, typography, and line spacing for this template's generated PDF and DOCX documents. Paper size is applied automatically — the lawyer is not asked to choose it.
          </p>
          <div className="grid-2">
            <div className="form-group">
              <label>Paper Size</label>
              <select
                value={template.settings?.page_size || 'A4'}
                onChange={e => handleSettingsChange('page_size', e.target.value)}
                disabled={isLocked}
              >
                <option value="A4">A4 (210 × 297 mm) — standard applications</option>
                <option value="Legal">Legal (216 × 356 mm) — affidavits / સોગંદનામું</option>
              </select>
            </div>
            <div className="form-group">
              <label>Top Margin (cm)</label>
              <input 
                type="number" 
                step="0.1" 
                value={template.settings?.margin_top_cm ?? 2.5} 
                onChange={e => handleSettingsChange('margin_top_cm', parseFloat(e.target.value) || 2.5)} 
                disabled={isLocked} 
              />
            </div>
            <div className="form-group">
              <label>Bottom Margin (cm)</label>
              <input 
                type="number" 
                step="0.1" 
                value={template.settings?.margin_bottom_cm ?? 2.5} 
                onChange={e => handleSettingsChange('margin_bottom_cm', parseFloat(e.target.value) || 2.5)} 
                disabled={isLocked} 
              />
            </div>
            <div className="form-group">
              <label>Left Margin (cm)</label>
              <input 
                type="number" 
                step="0.1" 
                value={template.settings?.margin_left_cm ?? 2.5} 
                onChange={e => handleSettingsChange('margin_left_cm', parseFloat(e.target.value) || 2.5)} 
                disabled={isLocked} 
              />
            </div>
            <div className="form-group">
              <label>Right Margin (cm)</label>
              <input 
                type="number" 
                step="0.1" 
                value={template.settings?.margin_right_cm ?? 2.5} 
                onChange={e => handleSettingsChange('margin_right_cm', parseFloat(e.target.value) || 2.5)} 
                disabled={isLocked} 
              />
            </div>
            <div className="form-group">
              <label>Default English Font</label>
              <select 
                value={template.settings?.english_font || 'Times-Roman'} 
                onChange={e => handleSettingsChange('english_font', e.target.value)} 
                disabled={isLocked}
              >
                <option value="Times-Roman">Times New Roman / Times-Roman (Court Standard)</option>
                <option value="Helvetica">Helvetica (Sans-Serif)</option>
              </select>
            </div>
            <div className="form-group">
              <label>Document Font (Gujarati)</label>
              <select 
                value={template.settings?.gujarati_font || 'Noto Sans Gujarati'} 
                onChange={e => handleSettingsChange('gujarati_font', e.target.value)} 
                disabled={isLocked}
              >
                <option value="Noto Sans Gujarati">Noto Sans Gujarati (Recommended — full Latin + digits)</option>
                <option value="Noto Serif Gujarati">Noto Serif Gujarati (Serif style)</option>
                <option value="Lohit Gujarati">Lohit Gujarati (Compatibility)</option>
              </select>
            </div>
            <div className="form-group">
              <label>Body Font Size (pt)</label>
              <input 
                type="number" 
                value={template.settings?.body_size ?? 12} 
                onChange={e => handleSettingsChange('body_size', parseInt(e.target.value) || 12)} 
                disabled={isLocked} 
              />
            </div>
            <div className="form-group">
              <label>Heading Font Size (pt)</label>
              <input 
                type="number" 
                value={template.settings?.heading_size ?? 13} 
                onChange={e => handleSettingsChange('heading_size', parseInt(e.target.value) || 13)} 
                disabled={isLocked} 
              />
            </div>
            <div className="form-group">
              <label>Line Spacing (pt)</label>
              <input 
                type="number" 
                value={template.settings?.line_spacing ?? 18} 
                onChange={e => handleSettingsChange('line_spacing', parseInt(e.target.value) || 18)} 
                disabled={isLocked} 
              />
            </div>
            <div className="form-group">
              <label>Paragraph Spacing (pt)</label>
              <input 
                type="number" 
                value={template.settings?.paragraph_spacing ?? 6} 
                onChange={e => handleSettingsChange('paragraph_spacing', parseInt(e.target.value) || 6)} 
                disabled={isLocked} 
              />
            </div>
          </div>
        </div>
      )}

      {activeTab === 'preview' && (
        <div className="editor-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3>Live Document Preview & Validation</h3>
            <button className="btn-secondary btn-sm" onClick={handlePreview} disabled={previewLoading}>
              {previewLoading ? 'Rendering...' : '🔄 Refresh Live Preview'}
            </button>
          </div>

          {/* Validation Banner */}
          {validation && (
            <div style={{ marginBottom: '16px' }}>
              {validation.valid ? (
                <div style={{ padding: '12px 16px', backgroundColor: '#e8f5e9', border: '1px solid #4caf50', borderRadius: '6px', color: '#2e7d32' }}>
                  ✅ <strong>Placeholders Valid:</strong> All document placeholders match declared fields and system auto-fill variables.
                </div>
              ) : (
                <div style={{ padding: '12px 16px', backgroundColor: '#ffebee', border: '1px solid #f44336', borderRadius: '6px', color: '#c62828' }}>
                  ⚠️ <strong>Validation Alerts:</strong>
                  {validation.unknown?.length > 0 && (
                    <div>• Unknown placeholders found in document: <strong>{validation.unknown.map(k => `{{${k}}}`).join(', ')}</strong> (Add these as template fields or remove them from content).</div>
                  )}
                  {validation.duplicate_keys && validation.duplicate_keys.length > 0 && (
                    <div>• Duplicate field keys found: <strong>{validation.duplicate_keys.join(', ')}</strong> (Each field must have a unique key).</div>
                  )}
                </div>
              )}
            </div>
          )}

          {previewLoading ? (
            <div className="dashboard-loading"><div className="spinner"></div><p>Rendering preview...</p></div>
          ) : (
            <div className="split-pane">
              <div className="pane">
                <label className="pane-label">English Rendered Preview</label>
                <div className="preview-pane content-en" style={{ minHeight: '300px', whiteSpace: 'pre-wrap', backgroundColor: '#fff', border: '1px solid #ddd', padding: '16px', borderRadius: '4px' }}>
                  {previewEn || 'No preview generated. Click "Refresh Live Preview".'}
                </div>
              </div>
              <div className="pane">
                <label className="pane-label">Gujarati Rendered Preview</label>
                <div className="preview-pane content-gu text-gu" style={{ minHeight: '300px', whiteSpace: 'pre-wrap', backgroundColor: '#fff', border: '1px solid #ddd', padding: '16px', borderRadius: '4px' }}>
                  {previewGu || 'No preview generated. Click "Refresh Live Preview".'}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

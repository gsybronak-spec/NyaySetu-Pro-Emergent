import { useEffect, useState } from 'react';
import { adminApi } from '../lib/api';

interface FieldConfig {
  key: string;
  label_en: string;
  label_gu: string;
  type: string;
  required: boolean;
  order: number;
  placeholder?: string;
  default_value?: string;
  autofill_map?: string;
}

interface CaseFormConfig {
  case_type_id: string;
  name_en: string;
  name_gu: string;
  category: string;
  fields: FieldConfig[];
}

export default function CaseFormBuilder() {
  const [caseTypes, setCaseTypes] = useState<string[]>(['civil', 'bail', 'revenue', 'criminal', 'family', 'other']);
  const [selectedType, setSelectedType] = useState<string>('civil');
  const [config, setConfig] = useState<CaseFormConfig | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [msg, setMsg] = useState<string>('');

  useEffect(() => {
    loadConfig(selectedType);
  }, [selectedType]);

  const loadConfig = async (typeId: string) => {
    setLoading(true);
    setMsg('');
    try {
      const data = await adminApi.getCaseFormConfig(typeId);
      setConfig(data);
    } catch (e: any) {
      setMsg(`Failed to load case form: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const addField = () => {
    if (!config) return;
    const newField: FieldConfig = {
      key: `custom_field_${config.fields.length + 1}`,
      label_en: 'New Field',
      label_gu: 'નવું ફીલ્ડ',
      type: 'text',
      required: false,
      order: config.fields.length,
      autofill_map: '',
    };
    setConfig({ ...config, fields: [...config.fields, newField] });
  };

  const removeField = (index: number) => {
    if (!config) return;
    const updated = [...config.fields];
    updated.splice(index, 1);
    setConfig({ ...config, fields: updated });
  };

  const updateField = (index: number, key: keyof FieldConfig, value: any) => {
    if (!config) return;
    const updated = [...config.fields];
    updated[index] = { ...updated[index], [key]: value };
    setConfig({ ...config, fields: updated });
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    setMsg('');
    try {
      await adminApi.adminSaveCaseForm(selectedType, {
        name_en: config.name_en,
        name_gu: config.name_gu,
        category: config.category,
        fields: config.fields,
      });
      setMsg('Case form configuration saved successfully!');
    } catch (e: any) {
      setMsg(`Error saving case form: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 'bold', color: '#1e293b' }}>Case Form Builder</h1>
          <p style={{ color: '#64748b', fontSize: '14px' }}>
            Configure dynamic fields, labels, Gujarati translations, and client autofill mappings per case type.
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving || !config}
          style={{
            padding: '10px 20px',
            backgroundColor: '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: saving ? 'not-allowed' : 'pointer',
            fontWeight: 600,
          }}
        >
          {saving ? 'Saving...' : 'Save Case Form'}
        </button>
      </div>

      {msg && (
        <div style={{ padding: '12px', marginBottom: '16px', borderRadius: '6px', backgroundColor: msg.includes('Error') || msg.includes('Failed') ? '#fee2e2' : '#dcfce7', color: msg.includes('Error') || msg.includes('Failed') ? '#991b1b' : '#166534' }}>
          {msg}
        </div>
      )}

      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
        {caseTypes.map((t) => (
          <button
            key={t}
            onClick={() => setSelectedType(t)}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: selectedType === t ? '2px solid #2563eb' : '1px solid #cbd5e1',
              backgroundColor: selectedType === t ? '#eff6ff' : '#ffffff',
              color: selectedType === t ? '#1d4ed8' : '#334155',
              cursor: 'pointer',
              fontWeight: 500,
              textTransform: 'capitalize',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {loading || !config ? (
        <div>Loading case form configuration...</div>
      ) : (
        <div style={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', padding: '20px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '20px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Title (English)</label>
              <input
                type="text"
                value={config.name_en}
                onChange={(e) => setConfig({ ...config, name_en: e.target.value })}
                style={{ width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '4px' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Title (Gujarati)</label>
              <input
                type="text"
                value={config.name_gu}
                onChange={(e) => setConfig({ ...config, name_gu: e.target.value })}
                style={{ width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '4px' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Category</label>
              <input
                type="text"
                value={config.category}
                onChange={(e) => setConfig({ ...config, category: e.target.value })}
                style={{ width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '4px' }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#0f172a' }}>Form Fields ({config.fields.length})</h3>
            <button
              onClick={addField}
              style={{ padding: '6px 12px', backgroundColor: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: '4px', cursor: 'pointer', fontSize: '13px', fontWeight: 500 }}
            >
              + Add Custom Field
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {config.fields.map((field, idx) => (
              <div key={idx} style={{ padding: '12px', border: '1px solid #e2e8f0', borderRadius: '6px', backgroundColor: '#f8fafc', display: 'grid', gridTemplateColumns: '1fr 1.5fr 1.5fr 1fr 1.5fr 70px 40px', gap: '10px', alignItems: 'center' }}>
                <div>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>Key</span>
                  <input
                    type="text"
                    value={field.key}
                    onChange={(e) => updateField(idx, 'key', e.target.value)}
                    style={{ width: '100%', padding: '6px', fontSize: '13px', border: '1px solid #cbd5e1', borderRadius: '4px' }}
                  />
                </div>
                <div>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>English Label</span>
                  <input
                    type="text"
                    value={field.label_en}
                    onChange={(e) => updateField(idx, 'label_en', e.target.value)}
                    style={{ width: '100%', padding: '6px', fontSize: '13px', border: '1px solid #cbd5e1', borderRadius: '4px' }}
                  />
                </div>
                <div>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>Gujarati Label</span>
                  <input
                    type="text"
                    value={field.label_gu}
                    onChange={(e) => updateField(idx, 'label_gu', e.target.value)}
                    style={{ width: '100%', padding: '6px', fontSize: '13px', border: '1px solid #cbd5e1', borderRadius: '4px' }}
                  />
                </div>
                <div>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>Type</span>
                  <select
                    value={field.type}
                    onChange={(e) => updateField(idx, 'type', e.target.value)}
                    style={{ width: '100%', padding: '6px', fontSize: '13px', border: '1px solid #cbd5e1', borderRadius: '4px' }}
                  >
                    <option value="text">Text</option>
                    <option value="textarea">Textarea</option>
                    <option value="number">Number</option>
                    <option value="mobile">Mobile</option>
                    <option value="email">Email</option>
                    <option value="date">Date</option>
                    <option value="select">Select</option>
                  </select>
                </div>
                <div>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>Autofill Map</span>
                  <select
                    value={field.autofill_map || ''}
                    onChange={(e) => updateField(idx, 'autofill_map', e.target.value)}
                    style={{ width: '100%', padding: '6px', fontSize: '13px', border: '1px solid #cbd5e1', borderRadius: '4px' }}
                  >
                    <option value="">None (Manual)</option>
                    <option value="user.name">Client Name (user.name)</option>
                    <option value="user.mobile">Client Mobile (user.mobile)</option>
                    <option value="user.email">Client Email (user.email)</option>
                    <option value="user.address">Client Address (user.address)</option>
                    <option value="user.district">Client District (user.district)</option>
                  </select>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <span style={{ fontSize: '11px', color: '#64748b', display: 'block' }}>Req?</span>
                  <input
                    type="checkbox"
                    checked={field.required}
                    onChange={(e) => updateField(idx, 'required', e.target.checked)}
                  />
                </div>
                <div>
                  <button
                    onClick={() => removeField(idx)}
                    style={{ color: '#ef4444', backgroundColor: 'transparent', border: 'none', cursor: 'pointer', fontWeight: 'bold' }}
                    title="Remove field"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

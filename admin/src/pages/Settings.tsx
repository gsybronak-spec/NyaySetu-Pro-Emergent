import React, { useEffect, useState } from 'react'
import { adminApi } from '../lib/api'
import { useAdminAuth } from '../lib/auth'

interface Setting {
  key: string;
  value: number | string;
  default: number | string;
  description: string;
  type: 'int' | 'str';
}

const SETTING_LABELS: Record<string, string> = {
  signup_credits: 'Signup Credits',
  default_page_size: 'Default Page Size',
  otp_ttl_seconds: 'OTP Validity (seconds)',
  otp_resend_cooldown_seconds: 'OTP Resend Cooldown (seconds)',
  otp_max_attempts: 'OTP Max Attempts',
};

export default function Settings() {
  const { admin } = useAdminAuth();
  const isSuper = admin?.role === 'super_admin';

  const [settings, setSettings] = useState<Setting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [savedKey, setSavedKey] = useState<string | null>(null);
  const [formError, setFormError] = useState('');

  const load = () => {
    setLoading(true);
    setError('');
    adminApi.listSettings()
      .then((items) => {
        setSettings(items);
        const d: Record<string, string> = {};
        items.forEach((s: Setting) => { d[s.key] = String(s.value); });
        setDrafts(d);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const save = async (s: Setting) => {
    setFormError('');
    setSavedKey(null);
    const raw = drafts[s.key] ?? '';
    let value: number | string;
    if (s.type === 'int') {
      const n = parseInt(raw, 10);
      if (isNaN(n) || n < 0) return setFormError(`"${SETTING_LABELS[s.key] || s.key}" must be a non-negative number`);
      value = n;
    } else {
      value = raw;
    }
    setSavingKey(s.key);
    try {
      const updated = await adminApi.updateSetting(s.key, value);
      setDrafts((d) => ({ ...d, [s.key]: String(updated.value) }));
      setSettings((list) => list.map((it) => (it.key === s.key ? { ...it, value: updated.value } : it)));
      setSavedKey(s.key);
    } catch (err: any) {
      setFormError(err.message);
    } finally {
      setSavingKey(null);
    }
  };

  if (loading) return <div className="dashboard"><div className="dashboard-loading"><div className="spinner"></div><p>Loading settings…</p></div></div>;

  if (error) return (
    <div className="dashboard">
      <div className="dashboard-error">
        <p>{error}</p>
        <button className="btn" onClick={load}>Retry</button>
      </div>
    </div>
  );

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Settings</h1>
        <p className="dashboard-desc">Operational settings applied immediately to the lawyer app. Mutations are audit-logged.</p>
      </div>

      {formError && <p className="form-error">{formError}</p>}

      <div className="dashboard-table-card">
        {!isSuper && <p className="no-data">You have read-only access. Only super admins can change settings.</p>}
        <table className="data-table">
          <thead>
            <tr>
              <th>Setting</th>
              <th>Description</th>
              <th>Current Value</th>
              <th>Default</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {settings.map((s) => (
              <tr key={s.key}>
                <td><strong>{SETTING_LABELS[s.key] || s.key}</strong><br /><code>{s.key}</code></td>
                <td>{s.description}</td>
                <td>
                  {s.type === 'str' ? (
                    <select
                      value={drafts[s.key] ?? String(s.value)}
                      onChange={(e) => setDrafts((d) => ({ ...d, [s.key]: e.target.value }))}
                      disabled={!isSuper}
                    >
                      <option value="A4">A4</option>
                      <option value="LEGAL">Legal</option>
                    </select>
                  ) : (
                    <input
                      type="number"
                      min={0}
                      value={drafts[s.key] ?? String(s.value)}
                      onChange={(e) => setDrafts((d) => ({ ...d, [s.key]: e.target.value }))}
                      disabled={!isSuper}
                    />
                  )}
                </td>
                <td>{String(s.default)}</td>
                <td>
                  {isSuper && (
                    <button className="btn-small" onClick={() => save(s)} disabled={savingKey === s.key}>
                      {savingKey === s.key ? 'Saving…' : savedKey === s.key ? 'Saved ✓' : 'Save'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

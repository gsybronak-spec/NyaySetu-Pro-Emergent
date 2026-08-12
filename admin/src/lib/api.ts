const BASE = import.meta.env.VITE_API_BASE || 'https://nyaysetu-backend-nwp2.onrender.com';

async function request(path: string, method = 'GET', body?: unknown) {
  const token = localStorage.getItem('admin_token');
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${BASE}/api/admin${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err: any) {
    // Network-level failure (backend unreachable / connection reset / CORS).
    // Surface a readable message instead of the raw browser 'Failed to fetch'.
    throw new Error('Server connection failed. Check that the backend is reachable and try again.');
  }

  const text = await res.text();
  let json: any = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = { raw: text };
  }

  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem('admin_token');
      window.dispatchEvent(new Event('admin:unauthorized'));
    }
    const msg = json?.detail || json?.message || `HTTP ${res.status}`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return json;
}

export const adminApi = {
  login: (email: string, password: string) =>
    request('/auth/login', 'POST', { email, password }),
  me: () => request('/auth/me'),
  logout: () => request('/auth/logout', 'POST'),
  dashboardStats: () => request('/dashboard/stats'),
  adminListTemplates: (status?: string, category?: string, q?: string) => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (category) params.append('category', category);
    if (q) params.append('q', q);
    const qs = params.toString();
    return request(`/templates${qs ? '?' + qs : ''}`);
  },
  adminGetTemplate: (id: string) => request(`/templates/${id}`),
  adminCreateTemplate: (data: any) => request('/templates', 'POST', data),
  adminUpdateTemplate: (id: string, data: any) => request(`/templates/${id}`, 'PUT', data),
  adminPublishTemplate: (id: string) => request(`/templates/${id}/publish`, 'POST'),
  adminArchiveTemplate: (id: string) => request(`/templates/${id}/archive`, 'POST'),
  adminRemoveShadowDraft: (id: string, confirm = true) => request(`/templates/${id}/draft?confirm=${confirm}`, 'DELETE'),
  adminCloneTemplate: (id: string, data?: any) => request(`/templates/${id}/clone`, 'POST', data),
  adminTemplateVersions: (id: string) => request(`/templates/${id}/versions`),
  adminPreviewTemplate: (id: string, data?: any) => request(`/templates/${id}/preview`, 'POST', data),
  adminMigrateSeed: () => request('/templates/migrate-seed', 'POST'),
  adminImportAnalyze: (file_name: string, content_base64: string) =>
    request('/templates/import-word/analyze', 'POST', { file_name, content_base64 }),
  adminImportCreate: (data: any) => request('/templates/import-word', 'POST', data),
  getCaseForms: () => fetch(`${BASE}/api/catalog/case-forms`).then(r => r.json()),
  getCaseFormConfig: (id: string) => fetch(`${BASE}/api/catalog/case-forms/${id}`).then(r => r.json()),
  getCaseTypes: () => fetch(`${BASE}/api/catalog/case-types`).then(r => r.json()),
  adminSaveCaseForm: (id: string, data: any) => request(`/case-forms/${id}`, 'POST', data),
  listUsers: (q?: string, limit = 50, offset = 0) => {
    const params = new URLSearchParams();
    if (q) params.append('q', q);
    params.append('limit', String(limit));
    params.append('offset', String(offset));
    return request(`/users?${params.toString()}`);
  },
  getUser: (id: string) => request(`/users/${id}`),
  setUserStatus: (id: string, active: boolean) => request(`/users/${id}/status`, 'PATCH', { active }),
  listAuditLogs: (params?: { action?: string; admin_id?: string; limit?: number; offset?: number }) => {
    const p = new URLSearchParams();
    if (params?.action) p.append('action', params.action);
    if (params?.admin_id) p.append('admin_id', params.admin_id);
    p.append('limit', String(params?.limit ?? 50));
    p.append('offset', String(params?.offset ?? 0));
    return request(`/audit-logs?${p.toString()}`);
  },
  listCases: (params?: { q?: string; status?: string; category?: string; user_id?: string; limit?: number; offset?: number }) => {
    const p = new URLSearchParams();
    if (params?.q) p.append('q', params.q);
    if (params?.status) p.append('status', params.status);
    if (params?.category) p.append('category', params.category);
    if (params?.user_id) p.append('user_id', params.user_id);
    p.append('limit', String(params?.limit ?? 50));
    p.append('offset', String(params?.offset ?? 0));
    return request(`/cases?${p.toString()}`);
  },
  getCase: (id: string) => request(`/cases/${id}`),
  archiveCase: (id: string) => request(`/cases/${id}/archive`, 'POST'),
  restoreCase: (id: string) => request(`/cases/${id}/restore`, 'POST'),
  listPlans: () => request('/plans'),
  createPlan: (data: any) => request('/plans', 'POST', data),
  updatePlan: (id: string, data: any) => request(`/plans/${id}`, 'PUT', data),
  setPlanStatus: (id: string, active: boolean) => request(`/plans/${id}/status`, 'POST', { active }),
  listCatalog: (kind: string) => request(`/catalog/${kind}`),
  createCatalogItem: (kind: string, data: any) => request(`/catalog/${kind}`, 'POST', data),
  updateCatalogItem: (kind: string, id: string, data: any) => request(`/catalog/${kind}/${id}`, 'PUT', data),
  setCatalogStatus: (kind: string, id: string, active: boolean) => request(`/catalog/${kind}/${id}/status`, 'POST', { active }),
  listSettings: () => request('/settings'),
  updateSetting: (key: string, value: number | string) => request(`/settings/${key}`, 'PUT', { value }),
};

const BASE = import.meta.env.VITE_API_BASE || 'https://backend-gold-iota-nyngopebeg.vercel.app';

let isRefreshing = false;
let refreshSubscribers: Array<(token: string | null, error?: Error) => void> = [];

function subscribeTokenRefresh(cb: (token: string | null, error?: Error) => void) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token: string | null, error?: Error) {
  refreshSubscribers.forEach((cb) => cb(token, error));
  refreshSubscribers = [];
}

async function performSilentRefresh(): Promise<string> {
  const refreshToken = localStorage.getItem('admin_refresh_token');
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  let res: Response;
  try {
    res = await fetch(`${BASE}/api/admin/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch (err: any) {
    // Network/infrastructure failure — NOT an auth revocation.
    // Do NOT wipe credentials on network error.
    throw new Error('Network failure during session refresh');
  }

  const text = await res.text();
  let json: any = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = { raw: text };
  }

  if (!res.ok) {
    // If the refresh endpoint explicitly rejected with 401, the persistent session is revoked/expired
    if (res.status === 401) {
      localStorage.removeItem('admin_token');
      localStorage.removeItem('admin_refresh_token');
      localStorage.removeItem('admin_user');
      window.dispatchEvent(new Event('admin:unauthorized'));
    }
    const msg = json?.detail || json?.message || `HTTP ${res.status}`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }

  if (json?.token) {
    localStorage.setItem('admin_token', json.token);
    if (json.refresh_token) {
      localStorage.setItem('admin_refresh_token', json.refresh_token);
    }
    if (json.admin) {
      localStorage.setItem('admin_user', JSON.stringify(json.admin));
    }
    return json.token;
  }

  throw new Error('Invalid refresh response structure');
}

async function request(path: string, method = 'GET', body?: unknown, isRetry = false): Promise<any> {
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
    // Network-level failure (backend unreachable / connection reset / CORS / cold start).
    // NEVER wipe credentials on network failures.
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
    // Handle 401 Unauthorized
    if (res.status === 401) {
      const isAuthEndpoint = path.startsWith('/auth/login') || path.startsWith('/auth/refresh');
      
      // If it's a login endpoint or already retried once, do NOT attempt silent refresh
      if (isAuthEndpoint || isRetry) {
        if (path.startsWith('/auth/refresh')) {
          localStorage.removeItem('admin_token');
          localStorage.removeItem('admin_refresh_token');
          localStorage.removeItem('admin_user');
          window.dispatchEvent(new Event('admin:unauthorized'));
        }
        const msg = json?.detail || json?.message || `HTTP ${res.status}`;
        throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      }

      // If a refresh is already in flight, queue this request
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh((newToken, refreshErr) => {
            if (refreshErr || !newToken) {
              reject(refreshErr || new Error('Session expired. Please log in again.'));
            } else {
              resolve(request(path, method, body, true));
            }
          });
        });
      }

      // Check if we have a refresh token
      const refreshToken = localStorage.getItem('admin_refresh_token');
      if (!refreshToken) {
        localStorage.removeItem('admin_token');
        localStorage.removeItem('admin_user');
        window.dispatchEvent(new Event('admin:unauthorized'));
        throw new Error('Session expired. Please log in again.');
      }

      // Initiate single silent refresh
      isRefreshing = true;
      try {
        const newToken = await performSilentRefresh();
        isRefreshing = false;
        onRefreshed(newToken);
        return request(path, method, body, true);
      } catch (refreshErr: any) {
        isRefreshing = false;
        onRefreshed(null, refreshErr);
        throw refreshErr;
      }
    }

    // For ALL other HTTP statuses (400, 403, 404, 409, 422, 429, 500, 502, 503):
    // NEVER wipe credentials or trigger logout.
    const msg = json?.detail || json?.message || `HTTP ${res.status}`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }

  return json;
}

export const adminApi = {
  login: (email: string, password: string) =>
    request('/auth/login', 'POST', { email, password }),
  me: () => request('/auth/me'),
  refresh: (refreshToken?: string) =>
    request('/auth/refresh', 'POST', { refresh_token: refreshToken || localStorage.getItem('admin_refresh_token') }),
  logout: (refreshToken?: string) =>
    request('/auth/logout', 'POST', { refresh_token: refreshToken || localStorage.getItem('admin_refresh_token') }),
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
  adminDeleteTemplate: (id: string) => request(`/templates/${id}`, 'DELETE'),
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

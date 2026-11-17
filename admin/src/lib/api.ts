const BASE = (typeof (import.meta as any) !== 'undefined' && (import.meta as any).env?.VITE_API_BASE) || 'https://backend-gold-iota-nyngopebeg.vercel.app';

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

export type InvalidationComponent = 'templates' | 'template_order' | 'catalog' | 'settings' | 'plans' | 'case_forms';

type InvalidationListener = (component: InvalidationComponent, details?: any) => void;
const invalidationListeners = new Set<InvalidationListener>();

export function subscribeAdminInvalidation(listener: InvalidationListener): () => void {
  invalidationListeners.add(listener);
  return () => {
    invalidationListeners.delete(listener);
  };
}

export function notifyAdminMutation(component: InvalidationComponent, details?: any) {
  // 1. Notify internal Admin subscribers
  invalidationListeners.forEach((cb) => {
    try {
      cb(component, details);
    } catch (e) {
      console.warn('[adminApi] Invalidation listener error', e);
    }
  });

  // 2. Broadcast to Lawyer Frontend across tabs / windows
  if (typeof window !== 'undefined') {
    try {
      const payload = JSON.stringify({ component, timestamp: Date.now(), details });
      localStorage.setItem('nyaysetu_cache_bust', payload);
      window.dispatchEvent(new CustomEvent('nyaysetu:invalidation', { detail: { component, details } }));
    } catch {}

    try {
      if (typeof BroadcastChannel !== 'undefined') {
        const bc = new BroadcastChannel('nyaysetu_sync_channel');
        bc.postMessage({ type: 'invalidate', component, timestamp: Date.now(), details });
        bc.close();
      }
    } catch {}
  }
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
  adminCreateTemplate: async (data: any) => {
    const res = await request('/templates', 'POST', data);
    notifyAdminMutation('templates', { action: 'create', id: res?.id || data?.id });
    return res;
  },
  adminUpdateTemplate: async (id: string, data: any) => {
    const res = await request(`/templates/${id}`, 'PUT', data);
    notifyAdminMutation('templates', { action: 'update', id });
    return res;
  },
  adminPublishTemplate: async (id: string) => {
    const res = await request(`/templates/${id}/publish`, 'POST');
    notifyAdminMutation('templates', { action: 'publish', id });
    return res;
  },
  adminArchiveTemplate: async (id: string) => {
    const res = await request(`/templates/${id}/archive`, 'POST');
    notifyAdminMutation('templates', { action: 'archive', id });
    return res;
  },
  adminDeleteTemplate: async (id: string) => {
    const res = await request(`/templates/${id}`, 'DELETE');
    notifyAdminMutation('templates', { action: 'delete', id });
    notifyAdminMutation('template_order', { action: 'delete', id });
    return res;
  },
  adminRemoveShadowDraft: async (id: string, confirm = true) => {
    const res = await request(`/templates/${id}/draft?confirm=${confirm}`, 'DELETE');
    notifyAdminMutation('templates', { action: 'remove_draft', id });
    return res;
  },
  adminCloneTemplate: (id: string, data?: any) => request(`/templates/${id}/clone`, 'POST', data),
  adminTemplateVersions: (id: string) => request(`/templates/${id}/versions`),
  adminPreviewTemplate: (id: string, data?: any) => request(`/templates/${id}/preview`, 'POST', data),
  adminMigrateSeed: async () => {
    const res = await request('/templates/migrate-seed', 'POST');
    notifyAdminMutation('templates', { action: 'migrate_seed' });
    notifyAdminMutation('template_order', { action: 'migrate_seed' });
    return res;
  },
  adminImportAnalyze: (file_name: string, content_base64: string) =>
    request('/templates/import-word/analyze', 'POST', { file_name, content_base64 }),
  adminImportCreate: async (data: any) => {
    const res = await request('/templates/import-word', 'POST', data);
    notifyAdminMutation('templates', { action: 'import_create', id: res?.id || data?.id });
    return res;
  },
  getCaseForms: () => request('/case-forms').catch(() => fetch(`${BASE}/api/catalog/case-forms`).then(r => r.json())),
  getCaseFormConfig: (id: string) => request(`/case-forms/${id}`).catch(() => fetch(`${BASE}/api/catalog/case-forms/${id}`).then(r => r.json())),
  getCaseTypes: () => fetch(`${BASE}/api/catalog/case-types`).then(r => r.json()),
  adminSaveCaseForm: async (id: string, data: any) => {
    const res = await request(`/case-forms/${id}`, 'POST', data);
    notifyAdminMutation('case_forms', { id });
    return res;
  },
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
  listCases: (params?: {
    q?: string;
    status?: string;
    category?: string;
    user_id?: string;
    page?: number;
    page_size?: number;
    limit?: number;
    offset?: number;
  }) => {
    const p = new URLSearchParams();
    if (params?.q) p.append('q', params.q);
    if (params?.status) p.append('status', params.status);
    if (params?.category) p.append('category', params.category);
    if (params?.user_id) p.append('user_id', params.user_id);
    if (params?.page !== undefined) p.append('page', String(params.page));
    if (params?.page_size !== undefined) p.append('page_size', String(params.page_size));
    if (params?.limit !== undefined) p.append('limit', String(params.limit));
    if (params?.offset !== undefined) p.append('offset', String(params.offset));
    else if (params?.page === undefined && params?.limit === undefined) {
      p.append('limit', '50');
      p.append('offset', '0');
    }
    return request(`/cases?${p.toString()}`);
  },
  getCase: (id: string) => request(`/cases/${id}`),
  deleteCase: (id: string) => request(`/cases/${id}`, 'DELETE'),
  cascadeDeleteCase: (id: string) => request(`/cases/${id}/cascade`, 'DELETE'),
  archiveCase: (id: string) => request(`/cases/${id}/archive`, 'POST'),
  restoreCase: (id: string) => request(`/cases/${id}/restore`, 'POST'),
  bulkArchiveCases: (ids: string[]) => request('/cases/bulk-archive', 'POST', { ids }),
  bulkRestoreCases: (ids: string[]) => request('/cases/bulk-restore', 'POST', { ids }),
  bulkDeleteCases: (ids: string[]) => request('/cases/bulk-delete', 'POST', { ids }),
  bulkCascadeDeleteCases: (ids: string[]) => request('/cases/bulk-cascade-delete', 'POST', { ids }),
  resetAllTestCases: (confirmText: string) => request('/cases/reset-all-test-data', 'POST', { confirm_text: confirmText }),
  listPlans: () => request('/plans'),
  createPlan: async (data: any) => {
    const res = await request('/plans', 'POST', data);
    notifyAdminMutation('plans', { action: 'create' });
    return res;
  },
  updatePlan: async (id: string, data: any) => {
    const res = await request(`/plans/${id}`, 'PUT', data);
    notifyAdminMutation('plans', { action: 'update', id });
    return res;
  },
  setPlanStatus: async (id: string, active: boolean) => {
    const res = await request(`/plans/${id}/status`, 'POST', { active });
    notifyAdminMutation('plans', { action: 'status', id, active });
    return res;
  },
  listCatalog: (kind: string) => request(`/catalog/${kind}`),
  createCatalogItem: async (kind: string, data: any) => {
    const res = await request(`/catalog/${kind}`, 'POST', data);
    notifyAdminMutation('catalog', { action: 'create', kind });
    return res;
  },
  updateCatalogItem: async (kind: string, id: string, data: any) => {
    const res = await request(`/catalog/${kind}/${id}`, 'PUT', data);
    notifyAdminMutation('catalog', { action: 'update', kind, id });
    return res;
  },
  deleteCatalogItem: async (kind: string, id: string, hard = false) => {
    const res = await request(`/catalog/${kind}/${id}?hard=${hard}`, 'DELETE');
    notifyAdminMutation('catalog', { action: 'delete', kind, id });
    return res;
  },
  bulkDeleteCatalogItems: async (kind: string, ids: string[]) => {
    const res = await request(`/catalog/${kind}/bulk-delete`, 'POST', { ids });
    notifyAdminMutation('catalog', { action: 'bulk_delete', kind, ids });
    return res;
  },
  setCatalogStatus: async (kind: string, id: string, active: boolean) => {
    const res = await request(`/catalog/${kind}/${id}/status`, 'POST', { active });
    notifyAdminMutation('catalog', { action: 'status', kind, id, active });
    return res;
  },
  reorderCatalog: async (kind: string, order: string[]) => {
    const res = await request(`/catalog/${kind}/reorder`, 'PUT', { order });
    notifyAdminMutation('catalog', { action: 'reorder', kind, order });
    return res;
  },
  listSettings: () => request('/settings'),
  updateSetting: async (key: string, value: number | string) => {
    const res = await request(`/settings/${key}`, 'PUT', { value });
    notifyAdminMutation('settings', { key, value });
    return res;
  },
  getTemplateOrder: () => request('/template-order'),
  updateTemplateOrder: async (order: string[]) => {
    const res = await request('/template-order', 'PUT', { template_order: order });
    notifyAdminMutation('template_order', { action: 'order_update', order });
    return res;
  },
  reorderTemplates: async (order: string[]) => {
    const res = await request('/template-order', 'PUT', { template_order: order });
    notifyAdminMutation('template_order', { action: 'order_update', order });
    return res;
  },
  bulkDeleteTemplates: async (ids: string[]) => {
    const res = await request('/templates/bulk-delete', 'POST', { ids });
    notifyAdminMutation('templates', { action: 'bulk_delete', ids });
    notifyAdminMutation('template_order', { action: 'bulk_delete', ids });
    return res;
  },
};

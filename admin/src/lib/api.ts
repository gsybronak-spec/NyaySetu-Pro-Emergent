const BASE = import.meta.env.VITE_API_BASE || 'https://nyaysetu-backend-nwp2.onrender.com';

async function request(path: string, method = 'GET', body?: unknown) {
  const token = localStorage.getItem('admin_token');
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}/api/admin${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

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
  adminCloneTemplate: (id: string, data?: any) => request(`/templates/${id}/clone`, 'POST', data),
  adminTemplateVersions: (id: string) => request(`/templates/${id}/versions`),
  adminPreviewTemplate: (id: string, data?: any) => request(`/templates/${id}/preview`, 'POST', data),
  adminMigrateSeed: () => request('/templates/migrate-seed', 'POST'),
};

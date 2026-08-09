import { storage } from "@/src/utils/storage";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;
const TOKEN_KEY = "nyaysetu_token";

export async function setToken(t: string | null) {
  if (t) await storage.secureSet(TOKEN_KEY, t);
  else await storage.secureRemove(TOKEN_KEY);
}

export async function getToken(): Promise<string | null> {
  return storage.secureGet(TOKEN_KEY, null as any);
}

async function request(path: string, method = "GET", body?: any) {
  const token = await getToken();
  const headers: any = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${BASE}/api${path}`, {
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
    const msg = json?.detail || json?.message || `HTTP ${res.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return json;
}

export const api = {
  sendOtp: (mobile: string) => request("/auth/send-otp", "POST", { mobile }),
  verifyOtp: (mobile: string, otp: string, referral_code?: string) =>
    request("/auth/verify-otp", "POST", { mobile, otp, referral_code }),
  googleSession: (session_id: string, referral_code?: string) =>
    request("/auth/google-session", "POST", { session_id, referral_code }),
  me: () => request("/profile/me"),
  updateProfile: (data: any) => request("/profile/update", "PUT", data),
  caseTypes: () => request("/catalog/case-types"),
  laws: () => request("/catalog/laws"),
  lawSections: (id: string) => request(`/catalog/laws/${id}/sections`),
  districts: () => request("/catalog/districts"),
  plans: () => request("/catalog/plans"),
  quote: () => request("/catalog/quote"),
  createCase: (data: any) => request("/cases", "POST", data),
  listCases: (params?: { q?: string; status?: string; category?: string }) => {
    const p = new URLSearchParams();
    if (params?.q) p.set("q", params.q);
    if (params?.status) p.set("status", params.status);
    if (params?.category) p.set("category", params.category);
    const qs = p.toString();
    return request(`/cases${qs ? `?${qs}` : ""}`);
  },
  getCase: (id: string) => request(`/cases/${id}`),
  updateCase: (id: string, data: any) => request(`/cases/${id}`, "PUT", data),
  archiveCase: (id: string) => request(`/cases/${id}/archive`, "POST"),
  restoreCase: (id: string) => request(`/cases/${id}/restore`, "POST"),
  deleteCase: (id: string) => request(`/cases/${id}`, "DELETE"),
  templates: (q?: string, category?: string) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category) params.set("category", category);
    const qs = params.toString();
    return request(`/templates${qs ? `?${qs}` : ""}`);
  },
  template: (id: string) => request(`/templates/${id}`),
  previewApp: (data: any) => request("/applications/preview", "POST", data),
  downloadApp: (data: any) => request("/applications/download", "POST", data),
  history: () => request("/applications/history"),
  wallet: () => request("/wallet"),
  purchase: (plan_id: string) => request("/purchase/mock", "POST", { plan_id }),
  transactions: () => request("/transactions"),
  referral: () => request("/referral/me"),
  saveDraft: (data: any) => request("/drafts", "POST", data),
  drafts: () => request("/drafts"),
  search: (q: string) => request(`/search?q=${encodeURIComponent(q)}`),
};

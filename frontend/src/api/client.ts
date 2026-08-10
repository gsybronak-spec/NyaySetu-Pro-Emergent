import { storage } from "@/src/utils/storage";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL || "https://nyaysetu-backend-nwp2.onrender.com";
const TOKEN_KEY = "nyaysetu_token";

export async function setToken(t: string | null) {
  if (t) await storage.secureSet(TOKEN_KEY, t);
  else await storage.secureRemove(TOKEN_KEY);
}

export async function getToken(): Promise<string | null> {
  return storage.secureGet(TOKEN_KEY, null as any);
}

const REQUEST_TIMEOUT_MS = 30000;

export function describeNetworkError(e: unknown): string {
  // User-friendly copy for fetch-level failures; technical detail goes to console.
  if (e instanceof Error && e.name === "AbortError") {
    return "The server took too long to respond. Please check your connection and try again.";
  }
  return "Network error — could not reach the server. Please check your connection and try again.";
}

async function request(path: string, method = "GET", body?: any) {
  const token = await getToken();
  const headers: any = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    res = await fetch(`${BASE}/api${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (e) {
    console.warn("[api] fetch failed", path, e);
    throw new Error(describeNetworkError(e));
  } finally {
    clearTimeout(timer);
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
      setToken(null);
    }
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
  lookupClient: (mobile: string) => request(`/clients/lookup?mobile=${encodeURIComponent(mobile)}`),
  caseFormConfig: (id: string) => request(`/catalog/case-forms/${id}`),
  listCaseForms: () => request("/catalog/case-forms"),
  caseTypes: () => request("/catalog/case-types"),
  laws: () => request("/catalog/laws"),
  lawSections: (id: string) => request(`/catalog/laws/${id}/sections`),
  districts: () => request("/catalog/districts"),
  courts: (district_id?: string) => request(`/catalog/courts${district_id ? `?district_id=${district_id}` : ""}`),
  policeStations: (district_id?: string) => request(`/catalog/police-stations${district_id ? `?district_id=${district_id}` : ""}`),
  favCourts: () => request("/favourites/courts"),
  addFavCourt: (id: string) => request(`/favourites/courts/${id}`, "POST"),
  removeFavCourt: (id: string) => request(`/favourites/courts/${id}`, "DELETE"),
  plans: () => request("/catalog/plans"),
  quote: () => request("/catalog/quote"),
  createCase: (data: any) => request("/cases", "POST", data),
  listCases: (params?: { q?: string; status?: string; category?: string; sort?: string }) => {
    const p = new URLSearchParams();
    if (params?.q) p.set("q", params.q);
    if (params?.status) p.set("status", params.status);
    if (params?.category) p.set("category", params.category);
    if (params?.sort) p.set("sort", params.sort);
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

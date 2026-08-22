import { storage } from "@/src/utils/storage";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL || "https://backend-gold-iota-nyngopebeg.vercel.app";
const TOKEN_KEY = "nyaysetu_token";
const REFRESH_TOKEN_KEY = "nyaysetu_refresh_token";

export async function setTokens(accessToken: string | null, refreshToken?: string | null) {
  if (accessToken) {
    await storage.secureSet(TOKEN_KEY, accessToken);
  } else {
    await storage.secureRemove(TOKEN_KEY);
  }
  if (refreshToken !== undefined) {
    if (refreshToken) {
      await storage.secureSet(REFRESH_TOKEN_KEY, refreshToken);
    } else {
      await storage.secureRemove(REFRESH_TOKEN_KEY);
    }
  }
}

export async function setToken(t: string | null) {
  await setTokens(t);
}

export async function getToken(): Promise<string | null> {
  return storage.secureGet(TOKEN_KEY, null as any);
}

export async function getRefreshToken(): Promise<string | null> {
  return storage.secureGet(REFRESH_TOKEN_KEY, null as any);
}

// C4: called when any API definitively rejects authentication (revoked/expired refresh),
// so the auth context can clear the session and route guards can redirect to login.
let onUnauthorized: (() => void) | null = null;
export function setOnUnauthorized(cb: (() => void) | null) {
  onUnauthorized = cb;
}

const REQUEST_TIMEOUT_MS = 30000;

// Mutex and subscriber queue for concurrent silent token renewal
let isRefreshing = false;
let refreshSubscribers: Array<(token: string | null, err?: any) => void> = [];

function subscribeTokenRefresh(cb: (token: string | null, err?: any) => void) {
  refreshSubscribers.push(cb);
}

function onTokenRefreshed(token: string | null, err?: any) {
  const subscribers = [...refreshSubscribers];
  refreshSubscribers = [];
  subscribers.forEach((cb) => cb(token, err));
}

export async function performSilentRefresh(): Promise<string> {
  const refreshToken = await getRefreshToken();
  if (!refreshToken) {
    throw new Error("No refresh token available");
  }

  let res: Response;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    res = await fetch(`${BASE}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      signal: controller.signal,
    });
  } catch (e) {
    // Network error or timeout — DO NOT purge credentials.
    console.warn("[api] silent refresh network error (preserving session)", e);
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
    // If refresh definitively fails with 401/403 (revoked/expired session), purge local credentials
    if (res.status === 401 || res.status === 403) {
      console.warn("[api] session refresh definitively rejected, clearing credentials");
      await setTokens(null, null);
      onUnauthorized?.();
    }
    const msg = json?.detail || json?.message || describeStatusError(res.status) || `HTTP ${res.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }

  if (!json?.token) {
    throw new Error("Invalid refresh response from server");
  }

  await setTokens(json.token, json.refresh_token || refreshToken);
  return json.token;
}

export function describeNetworkError(e: unknown): string {
  // User-friendly copy for fetch-level failures; technical detail goes to console.
  if (e instanceof Error && e.name === "AbortError") {
    return "Server is taking longer than expected. Please try again.";
  }
  return "Network error — could not reach the server. Please check your connection and try again.";
}

// Maps backend status codes to safe, readable user copy (used when the backend
// did not return a JSON body). Backend-provided `detail` messages are preferred.
export function describeStatusError(status: number): string | null {
  if (status === 429) return "Too many attempts. Please wait before trying again.";
  if (status === 503) return "Service is temporarily unavailable. Please try again shortly.";
  if (status === 401) return "Invalid mobile/email or password.";
  return null;
}

// Paths that bypass automatic 401 silent refresh
const AUTH_BYPASS_PATHS = [
  "/auth/login",
  "/auth/register",
  "/auth/verify-otp",
  "/auth/send-otp",
  "/auth/forgot-password",
  "/auth/reset-password",
  "/auth/google",
  "/auth/firebase",
  "/auth/refresh",
  "/auth/logout",
];

async function request(path: string, method = "GET", body?: any, timeoutMs: number = REQUEST_TIMEOUT_MS, isRetry = false): Promise<any> {
  const token = await getToken();
  const headers: any = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
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

  // Handle 401 on protected endpoints with silent token renewal
  const isAuthBypass = AUTH_BYPASS_PATHS.some((p) => path.startsWith(p));
  if (res.status === 401 && !isAuthBypass && !isRetry) {
    const refreshToken = await getRefreshToken();
    if (refreshToken) {
      if (isRefreshing) {
        // Wait for active refresh to complete, then retry
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh((newToken, err) => {
            if (err || !newToken) {
              reject(err || new Error("Unauthorized"));
            } else {
              request(path, method, body, timeoutMs, true).then(resolve).catch(reject);
            }
          });
        });
      }

      isRefreshing = true;
      try {
        const newToken = await performSilentRefresh();
        onTokenRefreshed(newToken, null);
        isRefreshing = false;
        // Retry original request with newly issued access token
        return request(path, method, body, timeoutMs, true);
      } catch (refreshErr) {
        onTokenRefreshed(null, refreshErr);
        isRefreshing = false;
        throw refreshErr;
      }
    }
  }

  const text = await res.text();
  let json: any = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = { raw: text };
  }

  if (!res.ok) {
    const msg = json?.detail || json?.message || describeStatusError(res.status) || `HTTP ${res.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return json;
}

export const api = {
  sendOtp: (mobile: string) => request("/auth/send-otp", "POST", { mobile }),
  verifyOtp: (mobile: string, otp: string, referral_code?: string) =>
    request("/auth/verify-otp", "POST", { mobile, otp, referral_code }),
  register: (data: { mobile: string; otp: string; password: string; name?: string; email?: string; referral_code?: string }) =>
    request("/auth/register", "POST", data),
  login: (identifier: string, password: string, referral_code?: string) =>
    request("/auth/login", "POST", { identifier, password, referral_code }),
  forgotPassword: (mobile: string) => request("/auth/forgot-password", "POST", { mobile }),
  resetPassword: (mobile: string, otp: string, new_password: string) =>
    request("/auth/reset-password", "POST", { mobile, otp, new_password }),
  setPassword: (new_password: string) => request("/auth/set-password", "POST", { new_password }),
  googleSession: (session_id: string, referral_code?: string) =>
    request("/auth/google-session", "POST", { session_id, referral_code }),
  // Firebase Auth: exchange a VERIFIED Firebase ID token for the NyaySetu JWT + session.
  firebaseAuth: (id_token: string, referral_code?: string) =>
    request("/auth/firebase", "POST", { id_token, referral_code }),
  // Native Google OAuth: exchange the authorization code server-side.
  googleExchange: (code: string, redirect_uri: string, referral_code?: string) =>
    request("/auth/google", "POST", { code, redirect_uri, referral_code }),
  refreshSession: () => performSilentRefresh(),
  logout: (refresh_token?: string) => request("/auth/logout", "POST", { refresh_token }),
  me: () => request("/profile/me"),
  updateProfile: (data: any) => request("/profile/update", "PUT", data),
  lookupClient: (mobile: string) => request(`/clients/lookup?mobile=${encodeURIComponent(mobile)}`),
  caseFormConfig: (id: string) => request(`/catalog/case-forms/${id}`),
  listCaseForms: () => request("/catalog/case-forms"),
  caseTypes: () => request("/catalog/case-types"),
  templateBaseFields: () => request("/catalog/template-base-fields"),
  laws: () => request("/catalog/laws"),
  lawSections: (id: string) => request(`/catalog/laws/${id}/sections`),
  districts: () => request("/catalog/districts"),
  talukas: (district_id?: string) => request(`/catalog/talukas${district_id ? `?district_id=${district_id}` : ""}`),
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
  favTemplates: () => request("/favourites/templates"),
  addFavTemplate: (id: string) => request(`/favourites/templates/${id}`, "POST"),
  removeFavTemplate: (id: string) => request(`/favourites/templates/${id}`, "DELETE"),
  templatePreferences: () => request("/user/template-preferences"),
  updateTemplateOrder: (template_order: string[]) => request("/user/template-order", "PUT", { template_order }),
  template: (id: string) => request(`/templates/${id}`),
  previewApp: (data: any) => request("/applications/preview", "POST", data),
  // Downloads may need longer: document generation + a cold Render instance can
  // exceed the 30s default timeout for large legal PDFs. 90s keeps the request
  // from being aborted mid-generation while still failing fast on hangs.
  downloadApp: (data: any) => request("/applications/download", "POST", data, 90000),
  history: () => request("/applications/history"),
  wallet: () => request("/wallet"),
  purchase: (plan_id: string) => request("/purchase/mock", "POST", { plan_id }),
  // Razorpay production payment path (enabled via EXPO_PUBLIC_RAZORPAY_ENABLED=1)
  razorpayCreateOrder: (plan_id: string) =>
    request("/payments/razorpay/create-order", "POST", { plan_id }),
  razorpayVerify: (data: { plan_id: string; order_id: string; payment_id: string; signature: string }) =>
    request("/payments/razorpay/verify", "POST", data),
  transactions: () => request("/transactions"),
  referral: () => request("/referral/me"),
  saveDraft: (data: any) => request("/drafts", "POST", data),
  drafts: () => request("/drafts"),
  search: (q: string) => request(`/search?q=${encodeURIComponent(q)}`),
};

import { storage } from "@/src/utils/storage";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL || "https://backend-gold-iota-nyngopebeg.vercel.app";
const TOKEN_KEY = "nyaysetu_token";
const REFRESH_TOKEN_KEY = "nyaysetu_refresh_token";

interface CacheEntry {
  data: any;
  timestamp: number;
}

const apiGetCache = new Map<string, CacheEntry>();
const apiInFlightGet = new Map<string, Promise<any>>();

const CACHEABLE_GET_PREFIXES = [
  "/catalog/",
  "/templates",
  "/favourites/templates",
  "/user/template-preferences",
  "/wallet",
  "/cases",
  "/drafts",
];

const CACHE_TTL_MS = 60000; // 60 seconds
const FAST_CACHE_TTL_MS = 15000; // 15 seconds for dynamic user data (cases, wallet, drafts)

export function invalidateApiCache(prefix?: string) {
  if (!prefix) {
    apiGetCache.clear();
    apiInFlightGet.clear();
    return;
  }
  for (const key of apiGetCache.keys()) {
    if (key.includes(prefix)) {
      apiGetCache.delete(key);
    }
  }
  for (const key of apiInFlightGet.keys()) {
    if (key.includes(prefix)) {
      apiInFlightGet.delete(key);
    }
  }
}

export async function setTokens(accessToken: string | null, refreshToken?: string | null) {
  invalidateApiCache();
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
      credentials: "include",
      signal: controller.signal,
    });
  } catch (e) {
    // Attempt 1 retry for cold starts / transient blips
    try {
      await new Promise((r) => setTimeout(r, 1000));
      const retryController = new AbortController();
      const retryTimer = setTimeout(() => retryController.abort(), REQUEST_TIMEOUT_MS);
      try {
        res = await fetch(`${BASE}/api/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
          credentials: "include",
          signal: retryController.signal,
        });
      } finally {
        clearTimeout(retryTimer);
      }
    } catch (retryErr) {
      // Network error or timeout — DO NOT purge credentials.
      console.warn("[api] silent refresh network error (preserving session)", retryErr);
      throw new Error(describeNetworkError(retryErr));
    }
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
    const msg = formatApiErrorMessage(res.status, json);
    throw new Error(msg);
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
    return "Server is taking longer than expected to respond. Please try again.";
  }
  if (typeof navigator !== "undefined" && navigator.onLine === false) {
    return "You appear to be offline. Please check your internet connection and try again.";
  }
  return "Unable to connect to the server. Please check your internet connection or try again shortly.";
}

// Maps backend status codes to safe, readable user copy (used when the backend
// did not return a JSON body). Backend-provided `detail` messages are preferred.
export function describeStatusError(status: number): string {
  switch (status) {
    case 400:
      return "Invalid request. Please check the entered details and try again.";
    case 401:
      return "Invalid mobile/email or password.";
    case 403:
      return "Access denied. You do not have permission for this action.";
    case 404:
      return "The requested information or endpoint was not found.";
    case 409:
      return "This record or mobile number is already registered.";
    case 422:
      return "Some required fields are missing or invalid. Please check your inputs.";
    case 429:
      return "Too many requests. Please wait a moment before trying again.";
    case 500:
      return "Server encountered a temporary issue. Please try again shortly.";
    case 502:
      return "Server gateway error. The server is temporarily restarting, please retry.";
    case 503:
      return "Service is temporarily unavailable. Please try again shortly.";
    case 504:
      return "Server response timed out. Please try again shortly.";
    default:
      return `Request failed with status ${status}. Please try again.`;
  }
}

export function formatApiErrorMessage(status: number, json: any): string {
  if (json?.detail) {
    if (typeof json.detail === "string") {
      return json.detail;
    }
    if (Array.isArray(json.detail)) {
      const parsed = json.detail
        .map((item: any) => {
          if (typeof item === "string") return item;
          const loc = Array.isArray(item.loc) ? item.loc.filter((p: any) => p !== "body").join(".") : "";
          const msg = item.msg || item.message || "invalid value";
          return loc ? `${loc}: ${msg}` : msg;
        })
        .filter(Boolean);
      if (parsed.length > 0) return parsed.join(", ");
    }
    if (typeof json.detail === "object") {
      return JSON.stringify(json.detail);
    }
  }
  if (json?.message && typeof json.message === "string") {
    return json.message;
  }
  if (json?.error && typeof json.error === "string") {
    return json.error;
  }
  return describeStatusError(status);
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

async function rawRequest(path: string, method = "GET", body?: any, timeoutMs: number = REQUEST_TIMEOUT_MS, isRetry = false): Promise<any> {
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
      credentials: "include",
      signal: controller.signal,
    });
  } catch (e) {
    console.warn("[api] fetch failed", path, e);
    // 1-time automatic retry for transient network / cold-start hiccups
    if (!isRetry) {
      console.info("[api] Retrying failed request once...", path);
      await new Promise((r) => setTimeout(r, 1000));
      return rawRequest(path, method, body, timeoutMs, true);
    }
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
              rawRequest(path, method, body, timeoutMs, true).then(resolve).catch(reject);
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
        return rawRequest(path, method, body, timeoutMs, true);
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
    const msg = formatApiErrorMessage(res.status, json);
    throw new Error(msg);
  }
  return json;
}

async function request(path: string, method = "GET", body?: any, timeoutMs: number = REQUEST_TIMEOUT_MS, isRetry = false): Promise<any> {
  const isCacheable = method === "GET" && CACHEABLE_GET_PREFIXES.some((p) => path.startsWith(p));
  if (!isCacheable) {
    return rawRequest(path, method, body, timeoutMs, isRetry);
  }

  const token = await getToken();
  const cacheKey = `${path}::${token || "anon"}`;

  const isDynamicFast = path.startsWith("/wallet") || path.startsWith("/cases") || path.startsWith("/drafts");
  const ttl = isDynamicFast ? FAST_CACHE_TTL_MS : CACHE_TTL_MS;
  const swrMaxAge = isDynamicFast ? 60000 : 300000;

  const cached = apiGetCache.get(cacheKey);
  if (cached) {
    const age = Date.now() - cached.timestamp;
    if (age < ttl) {
      return cached.data;
    }
    // SWR: return cached data immediately and refresh in background
    if (age < swrMaxAge) {
      if (!apiInFlightGet.has(cacheKey)) {
        const bgPromise = (async () => {
          try {
            const fresh = await rawRequest(path, method, body, timeoutMs, isRetry);
            apiGetCache.set(cacheKey, { data: fresh, timestamp: Date.now() });
          } catch {
            // Keep existing cache on network failure
          } finally {
            apiInFlightGet.delete(cacheKey);
          }
        })();
        apiInFlightGet.set(cacheKey, bgPromise);
      }
      return cached.data;
    }
  }

  const inFlight = apiInFlightGet.get(cacheKey);
  if (inFlight) {
    return inFlight;
  }

  const promise = (async () => {
    try {
      const data = await rawRequest(path, method, body, timeoutMs, isRetry);
      apiGetCache.set(cacheKey, { data, timestamp: Date.now() });
      return data;
    } finally {
      apiInFlightGet.delete(cacheKey);
    }
  })();

  apiInFlightGet.set(cacheKey, promise);
  return promise;
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
  resetPasswordWithFirebase: (id_token: string, new_password: string) =>
    request("/auth/reset-password", "POST", { id_token, new_password }),
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
  updateProfile: async (data: any) => {
    const res = await request("/profile/update", "PUT", data);
    invalidateApiCache("/profile/me");
    return res;
  },
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
  createCase: async (data: any) => {
    const res = await request("/cases", "POST", data);
    invalidateApiCache("/cases");
    return res;
  },
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
  updateCase: async (id: string, data: any) => {
    const res = await request(`/cases/${id}`, "PUT", data);
    invalidateApiCache("/cases");
    return res;
  },
  archiveCase: async (id: string) => {
    const res = await request(`/cases/${id}/archive`, "POST");
    invalidateApiCache("/cases");
    return res;
  },
  restoreCase: async (id: string) => {
    const res = await request(`/cases/${id}/restore`, "POST");
    invalidateApiCache("/cases");
    return res;
  },
  deleteCase: async (id: string) => {
    const res = await request(`/cases/${id}`, "DELETE");
    invalidateApiCache("/cases");
    return res;
  },
  templates: (q?: string, category?: string) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category) params.set("category", category);
    const qs = params.toString();
    return request(`/templates${qs ? `?${qs}` : ""}`);
  },
  favTemplates: () => request("/favourites/templates"),
  addFavTemplate: async (id: string) => {
    const res = await request(`/favourites/templates/${id}`, "POST");
    invalidateApiCache("/favourites/templates");
    return res;
  },
  removeFavTemplate: async (id: string) => {
    const res = await request(`/favourites/templates/${id}`, "DELETE");
    invalidateApiCache("/favourites/templates");
    return res;
  },
  templatePreferences: () => request("/user/template-preferences"),
  updateTemplateOrder: async (template_order: string[]) => {
    const res = await request("/user/template-order", "PUT", { template_order });
    invalidateApiCache("/catalog/template-order");
    return res;
  },
  catalogTemplateOrder: () => request("/catalog/template-order"),
  template: (id: string) => request(`/templates/${id}`),
  previewApp: (data: any) => request("/applications/preview", "POST", data),
  // Downloads may need longer: document generation + a cold Render instance can
  // exceed the 30s default timeout for large legal PDFs. 90s keeps the request
  // from being aborted mid-generation while still failing fast on hangs.
  downloadApp: async (data: any) => {
    const res = await request("/applications/download", "POST", data, 90000);
    invalidateApiCache("/wallet");
    invalidateApiCache("/profile/me");
    return res;
  },
  history: () => request("/applications/history"),
  wallet: () => request("/wallet"),
  purchase: async (plan_id: string) => {
    const res = await request("/purchase/mock", "POST", { plan_id });
    invalidateApiCache("/wallet");
    invalidateApiCache("/profile/me");
    return res;
  },
  // Razorpay Standard Checkout endpoints
  createOrder: (data: { amount: number; currency?: string; receipt?: string; plan_id?: string; notes?: any }) =>
    request("/create-order", "POST", data),
  verifyPayment: async (data: {
    order_id?: string;
    payment_id?: string;
    signature?: string;
    razorpay_order_id?: string;
    razorpay_payment_id?: string;
    razorpay_signature?: string;
    plan_id?: string;
  }) => {
    const res = await request("/verify-payment", "POST", data);
    invalidateApiCache("/wallet");
    invalidateApiCache("/profile/me");
    return res;
  },
  // Razorpay production plan payment path (enabled via EXPO_PUBLIC_RAZORPAY_ENABLED=1)
  razorpayCreateOrder: (plan_id: string) =>
    request("/payments/razorpay/create-order", "POST", { plan_id }),
  razorpayVerify: async (data: { plan_id: string; order_id: string; payment_id: string; signature: string }) => {
    const res = await request("/payments/razorpay/verify", "POST", data);
    invalidateApiCache("/wallet");
    invalidateApiCache("/profile/me");
    return res;
  },
  transactions: () => request("/transactions"),
  referral: () => request("/referral/me"),
  saveDraft: async (data: any) => {
    const res = await request("/drafts", "POST", data);
    invalidateApiCache("/drafts");
    return res;
  },
  drafts: () => request("/drafts"),
  deleteDraft: async (id: string) => {
    const res = await request(`/drafts/${id}`, "DELETE");
    invalidateApiCache("/drafts");
    return res;
  },
  search: (q: string) => request(`/search?q=${encodeURIComponent(q)}`),
  // Notifications
  notifications: () => request("/notifications"),
  markNotificationRead: (id: string) => request(`/notifications/${id}/read`, "POST"),
  markAllNotificationsRead: () => request("/notifications/read-all", "POST"),
  // AI Assistant Services
  aiSuggestTemplate: (prompt: string, language?: string) =>
    request("/ai/suggest-template", "POST", { prompt, language }),
  aiDraftAssistance: (data: any) => request("/ai/draft-assistance", "POST", data),
  aiSummarize: (text: string, language?: string) =>
    request("/ai/summarize", "POST", { text, language }),
  aiChat: (message: string, history?: any[], context?: any) =>
    request("/ai/chat", "POST", { message, history, context }),
};

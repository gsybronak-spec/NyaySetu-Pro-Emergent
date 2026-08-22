import { storage } from "@/src/utils/storage";
import type {
  AdminUser,
  AdminDashboardStats,
  PaginatedResult,
  LawyerUser,
  UserDetailResponse,
  TransactionItem,
  AdminCaseItem,
  CaseDetailResponse,
  AdminApplicationItem,
  ApplicationDetailResponse,
  AdminTemplateItem,
  AdminTemplateRevision,
  CatalogItem,
  CatalogKind,
  AdminPlanItem,
  AdminAuditLogItem,
} from "@/src/types/admin";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL || "https://backend-gold-iota-nyngopebeg.vercel.app";
const ADMIN_TOKEN_KEY = "nyaysetu_admin_token";

export async function setAdminToken(token: string | null) {
  if (token) {
    await storage.secureSet(ADMIN_TOKEN_KEY, token);
  } else {
    await storage.secureRemove(ADMIN_TOKEN_KEY);
  }
}

export async function getAdminToken(): Promise<string | null> {
  return storage.secureGet(ADMIN_TOKEN_KEY, null as any);
}

let onAdminUnauthorized: (() => void) | null = null;
export function setOnAdminUnauthorized(cb: (() => void) | null) {
  onAdminUnauthorized = cb;
}

const REQUEST_TIMEOUT_MS = 30000;

export function describeAdminNetworkError(e: unknown): string {
  if (e instanceof Error && e.name === "AbortError") {
    return "Admin API request timed out. Please try again.";
  }
  return "Unable to connect to NyaySetu Pro Admin API. Please check your connection.";
}

export function describeAdminStatusError(status: number): string | null {
  if (status === 401) return "Session expired or unauthorized. Please sign in again.";
  if (status === 403) return "Access denied. Super Administrator privileges required.";
  if (status === 404) return "Resource not found.";
  if (status === 429) return "Too many requests. Please slow down.";
  if (status === 500) return "Server error occurred. Please contact system support.";
  return null;
}

async function adminRequest<T = any>(
  path: string,
  method = "GET",
  body?: any,
  timeoutMs: number = REQUEST_TIMEOUT_MS
): Promise<T> {
  const token = await getAdminToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;

  try {
    res = await fetch(`${BASE}/api/admin${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (e) {
    console.warn("[adminClient] fetch error", path, e);
    throw new Error(describeAdminNetworkError(e));
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
    if (res.status === 401 && token) {
      await setAdminToken(null);
      onAdminUnauthorized?.();
    }
    const msg =
      json?.detail ||
      json?.message ||
      describeAdminStatusError(res.status) ||
      `Admin API Error (HTTP ${res.status})`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }

  return json as T;
}

function buildQuery(params?: Record<string, any>): string {
  if (!params) return "";
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") {
      q.set(k, String(v));
    }
  }
  const str = q.toString();
  return str ? `?${str}` : "";
}

export const adminApi = {
  // Authentication
  login: (email: string, password: string) =>
    adminRequest<{ token: string; admin: AdminUser }>("/auth/login", "POST", { email, password }),
  me: () => adminRequest<AdminUser>("/auth/me"),
  logout: () => adminRequest<{ success: boolean; message: string }>("/auth/logout", "POST"),

  // Dashboard
  getStats: () => adminRequest<AdminDashboardStats>("/dashboard/stats"),

  // Users Management
  listUsers: (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    q?: string;
    status?: string;
    state?: string;
    district?: string;
    is_verified?: boolean;
    sort_by?: string;
    sort_order?: "asc" | "desc";
  }) => adminRequest<PaginatedResult<LawyerUser>>(`/users${buildQuery(params)}`),

  getUser: (id: string) => adminRequest<UserDetailResponse>(`/users/${id}`),

  updateUser: (
    id: string,
    data: {
      name?: string;
      mobile?: string;
      email?: string;
      bar_council_no?: string;
      state?: string;
      district?: string;
    }
  ) => adminRequest<{ success: boolean; user: LawyerUser }>(`/users/${id}`, "PUT", data),

  suspendUser: (id: string) =>
    adminRequest<{ success: boolean; status: string; user: LawyerUser }>(`/users/${id}/suspend`, "POST"),

  activateUser: (id: string) =>
    adminRequest<{ success: boolean; status: string; user: LawyerUser }>(`/users/${id}/activate`, "POST"),

  banUser: (id: string) =>
    adminRequest<{ success: boolean; status: string; user: LawyerUser }>(`/users/${id}/ban`, "POST"),

  setUserStatus: (id: string, active: boolean) =>
    adminRequest<{ success: boolean; user: LawyerUser }>(`/users/${id}/status`, "PATCH", { active }),

  bulkUserStatus: (data: { user_ids: string[]; action: "suspend" | "activate" | "ban"; reason?: string }) =>
    adminRequest<{ success: boolean; action: string; affected_count: number }>("/users/bulk-status", "POST", data),

  // Wallet Management
  getUserWallet: (userId: string) =>
    adminRequest<{
      user_id: string;
      balance: number;
      free_credits_granted: number;
      total_purchased: number;
      total_used: number;
      recent_transactions: TransactionItem[];
    }>(`/users/${userId}/wallet`),

  getUserTransactions: (
    userId: string,
    params?: { page?: number; page_size?: number; type?: string; status?: string }
  ) => adminRequest<PaginatedResult<TransactionItem>>(`/users/${userId}/wallet/transactions${buildQuery(params)}`),

  adjustUserWallet: (userId: string, data: { amount: number; reason: string }) =>
    adminRequest<{
      success: boolean;
      user_id: string;
      adjustment: number;
      balance_before: number;
      balance_after: number;
      wallet: any;
      reason: string;
    }>(`/users/${userId}/wallet/adjust`, "POST", data),

  // Cases Management
  listCases: (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    status?: string;
    category?: string;
    user_id?: string;
    sort_by?: string;
    sort_order?: "asc" | "desc";
  }) => adminRequest<PaginatedResult<AdminCaseItem>>(`/cases${buildQuery(params)}`),

  getCase: (id: string) => adminRequest<CaseDetailResponse>(`/cases/${id}`),

  archiveCase: (id: string) =>
    adminRequest<{ success: boolean; status: string }>(`/cases/${id}/archive`, "POST"),

  restoreCase: (id: string) =>
    adminRequest<{ success: boolean; status: string }>(`/cases/${id}/restore`, "POST"),

  // Applications (Generated Documents)
  listApplications: (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    user_id?: string;
    case_id?: string;
    template_id?: string;
    language?: string;
    format?: string;
    engine?: string;
    sort_by?: string;
    sort_order?: "asc" | "desc";
  }) => adminRequest<PaginatedResult<AdminApplicationItem>>(`/applications${buildQuery(params)}`),

  getApplication: (id: string) => adminRequest<ApplicationDetailResponse>(`/applications/${id}`),

  // Templates Management
  listTemplates: (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    category?: string;
    status?: string;
    sort_by?: string;
    sort_order?: "asc" | "desc";
  }) =>
    adminRequest<PaginatedResult<AdminTemplateItem>>(
      `/templates${buildQuery({ page: 1, page_size: 50, ...params, format: "paginated" })}`
    ),

  getTemplate: (id: string) => adminRequest<AdminTemplateItem>(`/templates/${id}`),

  getTemplateRevisions: (id: string) =>
    adminRequest<{
      template_id: string;
      total_revisions: number;
      revisions: AdminTemplateRevision[];
    }>(`/templates/${id}/revisions`),

  createTemplate: (data: Partial<AdminTemplateItem>) =>
    adminRequest<{ success: boolean; template: AdminTemplateItem }>("/templates", "POST", data),

  updateTemplate: (id: string, data: Partial<AdminTemplateItem>) =>
    adminRequest<{ success: boolean; template: AdminTemplateItem }>(`/templates/${id}`, "PUT", data),

  publishTemplate: (id: string) =>
    adminRequest<{ success: boolean; template: AdminTemplateItem; new_version: number }>(
      `/templates/${id}/publish`,
      "POST"
    ),

  unpublishTemplate: (id: string) =>
    adminRequest<{ success: boolean; template: AdminTemplateItem }>(`/templates/${id}/unpublish`, "POST"),

  archiveTemplate: (id: string) =>
    adminRequest<{ success: boolean; template: AdminTemplateItem }>(`/templates/${id}/archive`, "POST"),

  restoreTemplate: (id: string) =>
    adminRequest<{ success: boolean; template: AdminTemplateItem }>(`/templates/${id}/restore`, "POST"),

  deleteTemplatePermanent: (id: string) =>
    adminRequest<{ success: boolean; message: string }>(`/templates/${id}`, "DELETE"),

  duplicateTemplate: (id: string, asNewTemplate = true) =>
    adminRequest<{
      success: boolean;
      template: AdminTemplateItem;
      new_template_id: string;
    }>(`/templates/${id}/duplicate`, "POST", { as_new_template: asNewTemplate }),

  bulkTemplateStatus: (data: { template_ids: string[]; action: "archive" | "restore"; reason?: string }) =>
    adminRequest<{ success: boolean; action: string; affected_count: number }>("/templates/bulk-status", "POST", data),

  migrateSeedTemplates: () =>
    adminRequest<{ success: boolean; seed_complete: boolean; revisions: any }>("/templates/migrate-seed", "POST"),

  previewTemplate: (id: string, data?: { values?: Record<string, any>; content_en?: string; content_gu?: string; name_en?: string; name_gu?: string; fields?: any[]; settings?: any }) =>
    adminRequest<{ preview: { en: { content: string; blocks: any[] }; gu: { content: string; blocks: any[] } }; validation: any }>(`/templates/${id}/preview`, "POST", data),

  // Catalogs Management
  listCatalog: (kind: CatalogKind, search?: string) =>
    adminRequest<CatalogItem[]>(`/catalog/${kind}${buildQuery({ search })}`),

  getCatalogItem: (kind: CatalogKind, itemId: string) =>
    adminRequest<CatalogItem>(`/catalog/${kind}/${itemId}`),

  createCatalogItem: (kind: CatalogKind, data: any) =>
    adminRequest<{ success: boolean; item: CatalogItem }>(`/catalog/${kind}`, "POST", data),

  updateCatalogItem: (kind: CatalogKind, itemId: string, data: any) =>
    adminRequest<{ success: boolean; item: CatalogItem }>(`/catalog/${kind}/${itemId}`, "PUT", data),

  setCatalogItemStatus: (kind: CatalogKind, itemId: string, active: boolean) =>
    adminRequest<{ success: boolean; item: CatalogItem }>(`/catalog/${kind}/${itemId}/status`, "POST", { active }),

  deleteCatalogItem: (kind: CatalogKind, itemId: string) =>
    adminRequest<{ success: boolean; message: string }>(`/catalog/${kind}/${itemId}`, "DELETE"),

  // Plans Management
  listPlans: () => adminRequest<AdminPlanItem[]>("/plans"),

  getPlan: (planId: string) => adminRequest<AdminPlanItem>(`/plans/${planId}`),

  createPlan: (data: Partial<AdminPlanItem>) =>
    adminRequest<{ success: boolean; plan: AdminPlanItem }>("/plans", "POST", data),

  updatePlan: (planId: string, data: Partial<AdminPlanItem>) =>
    adminRequest<{ success: boolean; plan: AdminPlanItem }>(`/plans/${planId}`, "PUT", data),

  activatePlan: (planId: string) =>
    adminRequest<{ success: boolean; plan: AdminPlanItem }>(`/plans/${planId}/activate`, "POST"),

  deactivatePlan: (planId: string) =>
    adminRequest<{ success: boolean; plan: AdminPlanItem }>(`/plans/${planId}/deactivate`, "POST"),

  setPlanStatus: (planId: string, active: boolean) =>
    adminRequest<{ success: boolean; plan: AdminPlanItem }>(`/plans/${planId}/status`, "POST", { active }),

  // Audit Logs Management
  listAuditLogs: (params?: {
    page?: number;
    page_size?: number;
    action?: string;
    admin_id?: string;
    entity_type?: string;
    entity_id?: string;
    search?: string;
    start_date?: string;
    end_date?: string;
    sort_by?: string;
    sort_order?: "asc" | "desc";
  }) => adminRequest<PaginatedResult<AdminAuditLogItem>>(`/audit-logs${buildQuery(params)}`),
};

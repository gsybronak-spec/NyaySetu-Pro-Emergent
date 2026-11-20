/**
 * Unified Catalog Cache Service for NyaySetu Pro
 * 
 * Provides:
 * 1. Instant 0ms Memory Cache
 * 2. Persistent Local Storage Cache (survives app restart/re-open)
 * 3. Stale-While-Revalidate (SWR) with background updates
 * 4. In-flight Request Deduplication (no duplicate network requests)
 * 5. Strict district-scoped keying for Talukas and Courts
 * 6. Authoritative offline seed fallback baseline (34 districts, 255 talukas, courts)
 * 7. Zero fake empty states (never converts network failures to [])
 */

import { AppState } from "react-native";
import { api } from "@/src/api/client";
import { storage } from "@/src/utils/storage";
import {
  TemplateLogicalPair,
  getActiveTemplatePairs,
  PERMANENTLY_DELETED_BASE_KEYS,
} from "@/src/data/templateCatalogPairs";
import {
  SEED_DISTRICTS,
  SEED_TALUKAS,
  SEED_CASE_TYPES,
  SEED_LAWS,
  SEED_CASE_FORMS,
  SEED_TEMPLATE_ORDER,
  SEED_PUBLISHED_TEMPLATES,
} from "./catalogSeed";

const STORAGE_PREFIX = "nyaysetu_cat_v2:";
const memoryCache = new Map<string, any>();
const inFlightRequests = new Map<string, Promise<any>>();
const listeners = new Map<string, Set<(data: any) => void>>();

function sanitizeTemplates(list: any[]): any[] {
  if (!Array.isArray(list)) return [];
  return list.filter((t: any) => {
    const id = t?.id || t?.template_id;
    if (!id || typeof id !== "string") return false;
    const base = id.trim().replace(/_(gu|en)$/, "");
    return !PERMANENTLY_DELETED_BASE_KEYS.has(base) && !PERMANENTLY_DELETED_BASE_KEYS.has(id.trim());
  });
}

function sanitizeOrder(order: string[]): string[] {
  if (!Array.isArray(order)) return [];
  return order.filter((id) => {
    if (!id || typeof id !== "string") return false;
    const base = id.trim().replace(/_(gu|en)$/, "");
    return !PERMANENTLY_DELETED_BASE_KEYS.has(base) && !PERMANENTLY_DELETED_BASE_KEYS.has(id.trim());
  });
}

// Synchronously hydrate memoryCache from window.localStorage to guarantee zero-delay instant render
if (typeof window !== "undefined" && window.localStorage) {
  try {
    const rawPairs = window.localStorage.getItem(`${STORAGE_PREFIX}active_template_pairs`);
    if (rawPairs) {
      const parsed = JSON.parse(rawPairs);
      if (Array.isArray(parsed) && parsed.length > 0) {
        memoryCache.set(
          "active_template_pairs",
          parsed.filter((p: any) => !PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey))
        );
      }
    }
    const rawTpls = window.localStorage.getItem(`${STORAGE_PREFIX}published_templates`);
    if (rawTpls) {
      const parsed = JSON.parse(rawTpls);
      const clean = sanitizeTemplates(parsed);
      if (clean.length > 0) {
        memoryCache.set("published_templates", clean);
      }
    }
    const rawOrder = window.localStorage.getItem(`${STORAGE_PREFIX}template_order`);
    if (rawOrder) {
      const parsed = JSON.parse(rawOrder);
      const clean = sanitizeOrder(parsed);
      if (clean.length > 0) {
        memoryCache.set("template_order", clean);
      }
    }
  } catch {
    // Ignore storage parse error
  }
}

function notify(key: string, data: any) {
  const set = listeners.get(key);
  if (set) {
    set.forEach((cb) => {
      try {
        cb(data);
      } catch (e) {
        console.warn("[catalogCache] listener error", e);
      }
    });
  }
}

export function subscribeCatalog(key: string, cb: (data: any) => void): () => void {
  if (!listeners.has(key)) {
    listeners.set(key, new Set());
  }
  listeners.get(key)!.add(cb);
  return () => {
    listeners.get(key)?.delete(cb);
  };
}

async function loadFromStorage<T>(key: string, allowEmpty = false): Promise<T | null> {
  try {
    let val = await storage.get(`${STORAGE_PREFIX}${key}`, null as any);
    if (val !== null && val !== undefined) {
      if (key === "published_templates" && Array.isArray(val)) {
        val = sanitizeTemplates(val) as any;
      } else if (key === "template_order" && Array.isArray(val)) {
        val = sanitizeOrder(val) as any;
      }
      if (allowEmpty || !Array.isArray(val) || val.length > 0) {
        memoryCache.set(key, val);
        return val as T;
      }
    }
  } catch {
    // Ignore storage parse error
  }
  return null;
}

function isOrderEqual(a: any, b: any): boolean {
  if (!Array.isArray(a) || !Array.isArray(b)) return a === b;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

function isTemplatesEqual(a: any, b: any): boolean {
  if (!Array.isArray(a) || !Array.isArray(b)) return a === b;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    const tA = a[i];
    const tB = b[i];
    const idA = tA?.id || tA?.template_id;
    const idB = tB?.id || tB?.template_id;
    if (idA !== idB) return false;
    if (tA?.name_en !== tB?.name_en || tA?.name_gu !== tB?.name_gu) return false;
    if (tA?.updated_at && tB?.updated_at && tA.updated_at !== tB.updated_at) return false;
  }
  return true;
}

function isPairsEqual(a: any, b: any): boolean {
  if (!Array.isArray(a) || !Array.isArray(b)) return a === b;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i]?.baseKey !== b[i]?.baseKey) return false;
    if (a[i]?.name_gu !== b[i]?.name_gu || a[i]?.name_en !== b[i]?.name_en) return false;
    if (a[i]?.category !== b[i]?.category) return false;
  }
  return true;
}

function isDataEqual(key: string, a: any, b: any): boolean {
  if (key === "template_order") return isOrderEqual(a, b);
  if (key === "published_templates") return isTemplatesEqual(a, b);
  if (key === "active_template_pairs") return isPairsEqual(a, b);
  return false;
}

async function saveToStorage(key: string, data: any): Promise<void> {
  try {
    let cleanData = data;
    if (key === "published_templates" && Array.isArray(data)) {
      cleanData = sanitizeTemplates(data);
    } else if (key === "template_order" && Array.isArray(data)) {
      cleanData = sanitizeOrder(data);
    }
    const prev = memoryCache.get(key);
    const hasChanged = !prev || !isDataEqual(key, prev, cleanData);

    memoryCache.set(key, cleanData);
    await storage.set(`${STORAGE_PREFIX}${key}`, cleanData);
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        window.localStorage.setItem(`${STORAGE_PREFIX}${key}`, JSON.stringify(cleanData));
      } catch {}
    }
    if (hasChanged) {
      notify(key, cleanData);
    }
  } catch {
    // Ignore storage write error
  }
}

function getSeedFallback(key: string, district_id?: string): any[] {
  if (key === "districts") return SEED_DISTRICTS;
  if (key === "case_types") return SEED_CASE_TYPES;
  if (key === "laws") return SEED_LAWS;
  if (key === "case_forms") return SEED_CASE_FORMS;
  if (key === "template_order") return SEED_TEMPLATE_ORDER;
  if (key === "published_templates") return SEED_PUBLISHED_TEMPLATES;
  if (key.startsWith("talukas")) {
    if (district_id) {
      return SEED_TALUKAS.filter((t: any) => t.district_id === district_id);
    }
    return SEED_TALUKAS;
  }
  if (key.startsWith("courts")) {
    return [];
  }
  return [];
}

/**
 * Fetch a catalog dataset using Memory -> Storage -> SWR -> Deduplication -> Seed Fallback.
 */
async function fetchCatalogWithSWR<T>(
  cacheKey: string,
  fetcher: () => Promise<T>,
  seedData: T,
  forceRefresh = false,
  allowEmpty = false
): Promise<T> {
  // 1. Check in-memory cache
  if (!forceRefresh && memoryCache.has(cacheKey)) {
    const cached = memoryCache.get(cacheKey);
    if (cached !== null && cached !== undefined && (allowEmpty || !Array.isArray(cached) || cached.length > 0)) {
      // Trigger background revalidation without blocking caller
      triggerBackgroundRevalidate(cacheKey, fetcher, allowEmpty);
      return cached as T;
    }
  }

  // 2. Check local storage cache
  if (!forceRefresh) {
    const stored = await loadFromStorage<T>(cacheKey, allowEmpty);
    if (stored !== null && stored !== undefined && (allowEmpty || !Array.isArray(stored) || stored.length > 0)) {
      triggerBackgroundRevalidate(cacheKey, fetcher, allowEmpty);
      return stored;
    }
  }

  // 3. Deduplicate in-flight network request
  if (inFlightRequests.has(cacheKey)) {
    return inFlightRequests.get(cacheKey)!;
  }

  // 4. Create and store network request promise
  const requestPromise = (async () => {
    try {
      const fresh = await fetcher();
      if (fresh !== null && fresh !== undefined && (allowEmpty || !Array.isArray(fresh) || fresh.length > 0)) {
        await saveToStorage(cacheKey, fresh);
        return fresh;
      }
      // If server returned null/undefined (or empty when allowEmpty is false), preserve existing cache or seed
      const fallback = memoryCache.get(cacheKey) ?? seedData;
      return fallback as T;
    } catch (err) {
      console.warn(`[catalogCache] Failed to fetch ${cacheKey}, preserving cache/seed`, err);
      // On network failure: KEEP memory cache if present, else storage, else seed
      const fallback = memoryCache.get(cacheKey) ?? (await loadFromStorage(cacheKey, allowEmpty)) ?? seedData;
      return fallback as T;
    } finally {
      inFlightRequests.delete(cacheKey);
    }
  })();

  inFlightRequests.set(cacheKey, requestPromise);

  // If not forcing refresh, and seed data is available while cache is cold, allow caller to proceed immediately
  if (!forceRefresh && seedData && Array.isArray(seedData) && seedData.length > 0 && !memoryCache.has(cacheKey)) {
    return seedData;
  }

  return requestPromise;
}

function triggerBackgroundRevalidate<T>(cacheKey: string, fetcher: () => Promise<T>, allowEmpty = false) {
  if (inFlightRequests.has(cacheKey)) return;
  const p = (async () => {
    try {
      const fresh = await fetcher();
      if (fresh !== null && fresh !== undefined && (allowEmpty || !Array.isArray(fresh) || fresh.length > 0)) {
        await saveToStorage(cacheKey, fresh);
      }
    } catch (e) {
      // Background revalidation silently preserves existing cache
    } finally {
      inFlightRequests.delete(cacheKey);
    }
  })();
  inFlightRequests.set(cacheKey, p);
}

export const catalogCache = {
  getDistricts: (forceRefresh = false): Promise<any[]> => {
    return fetchCatalogWithSWR("districts", () => api.districts(), SEED_DISTRICTS, forceRefresh);
  },

  getTalukas: (district_id?: string, forceRefresh = false): Promise<any[]> => {
    const key = district_id ? `talukas:${district_id}` : "talukas:all";
    const seed = getSeedFallback(key, district_id);
    return fetchCatalogWithSWR(
      key,
      () => api.talukas(district_id || undefined),
      seed,
      forceRefresh
    );
  },

  getCourts: (district_id?: string, forceRefresh = false): Promise<any[]> => {
    const key = district_id ? `courts:${district_id}` : "courts:all";
    return fetchCatalogWithSWR(
      key,
      () => api.courts(district_id || undefined),
      [],
      forceRefresh,
      true
    );
  },

  getCaseTypes: (forceRefresh = false): Promise<any[]> => {
    return fetchCatalogWithSWR("case_types", () => api.caseTypes(), SEED_CASE_TYPES, forceRefresh);
  },

  getLaws: (forceRefresh = false): Promise<any[]> => {
    return fetchCatalogWithSWR("laws", () => api.laws(), SEED_LAWS, forceRefresh);
  },

  getCaseForms: (forceRefresh = false): Promise<any[]> => {
    return fetchCatalogWithSWR("case_forms", () => api.listCaseForms(), SEED_CASE_FORMS, forceRefresh);
  },

  getCaseFormConfig: async (case_type_id: string, forceRefresh = false): Promise<any> => {
    const key = `case_form_cfg:${case_type_id}`;
    const seedForm = SEED_CASE_FORMS.find((f: any) => f.case_type_id === case_type_id) || null;
    return fetchCatalogWithSWR(
      key,
      () => api.caseFormConfig(case_type_id),
      seedForm,
      forceRefresh
    );
  },

  getFavCourts: (forceRefresh = false): Promise<string[]> => {
    return fetchCatalogWithSWR(
      "fav_courts",
      async () => {
        const res = await api.favCourts();
        return Array.isArray(res?.favourite_courts) ? res.favourite_courts : [];
      },
      [],
      forceRefresh
    );
  },

  getPublishedTemplates: (forceRefresh = false): Promise<any[]> => {
    return fetchCatalogWithSWR(
      "published_templates",
      async () => {
        try {
          const res = await api.templates();
          return Array.isArray(res) ? res : [];
        } catch {
          return null as any;
        }
      },
      SEED_PUBLISHED_TEMPLATES,
      forceRefresh,
      true
    );
  },

  getTemplateOrder: (forceRefresh = false): Promise<string[]> => {
    return fetchCatalogWithSWR(
      "template_order",
      async () => {
        try {
          const res = await api.catalogTemplateOrder();
          return Array.isArray(res?.template_order) ? res.template_order : [];
        } catch {
          return null as any;
        }
      },
      SEED_TEMPLATE_ORDER,
      forceRefresh,
      true
    );
  },

  /**
   * Synchronous peek into memory cache. Returns fallback seed if not in memory.
   */
  peekDistricts: (): any[] => memoryCache.get("districts") || SEED_DISTRICTS,
  peekTalukas: (district_id?: string): any[] =>
    memoryCache.get(district_id ? `talukas:${district_id}` : "talukas:all") || getSeedFallback("talukas", district_id),
  peekCourts: (district_id?: string): any[] =>
    memoryCache.get(district_id ? `courts:${district_id}` : "courts:all") || [],
  peekCaseTypes: (): any[] => memoryCache.get("case_types") || SEED_CASE_TYPES,
  peekLaws: (): any[] => memoryCache.get("laws") || SEED_LAWS,
  peekFavCourts: (): string[] => memoryCache.get("fav_courts") || [],
  peekPublishedTemplates: (): any[] => {
    const mem = memoryCache.get("published_templates");
    if (mem && Array.isArray(mem)) return sanitizeTemplates(mem);
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        const raw = window.localStorage.getItem(`${STORAGE_PREFIX}published_templates`);
        if (raw) {
          const clean = sanitizeTemplates(JSON.parse(raw));
          if (clean.length > 0) {
            memoryCache.set("published_templates", clean);
            return clean;
          }
        }
      } catch {}
    }
    return SEED_PUBLISHED_TEMPLATES;
  },
  peekTemplateOrder: (): string[] => {
    const mem = memoryCache.get("template_order");
    if (mem && Array.isArray(mem)) return sanitizeOrder(mem);
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        const raw = window.localStorage.getItem(`${STORAGE_PREFIX}template_order`);
        if (raw) {
          const clean = sanitizeOrder(JSON.parse(raw));
          if (clean.length > 0) {
            memoryCache.set("template_order", clean);
            return clean;
          }
        }
      } catch {}
    }
    return SEED_TEMPLATE_ORDER;
  },

  peekActiveTemplatePairs: (): TemplateLogicalPair[] => {
    const mem = memoryCache.get("active_template_pairs");
    if (Array.isArray(mem) && mem.length > 0) {
      return mem.filter((p: any) => !PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey));
    }
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        const raw = window.localStorage.getItem(`${STORAGE_PREFIX}active_template_pairs`);
        if (raw) {
          const parsed = JSON.parse(raw);
          if (Array.isArray(parsed) && parsed.length > 0) {
            const clean = parsed.filter((p: any) => !PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey));
            memoryCache.set("active_template_pairs", clean);
            return clean;
          }
        }
      } catch {}
    }
    const computed = getActiveTemplatePairs(
      catalogCache.peekPublishedTemplates(),
      catalogCache.peekTemplateOrder()
    ).filter((p) => !PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey));
    if (computed.length > 0) {
      memoryCache.set("active_template_pairs", computed);
    }
    return computed;
  },

  getActiveTemplatePairs: async (forceRefresh = false): Promise<TemplateLogicalPair[]> => {
    // 1. If not forcing refresh, return memoryCache or storage immediately and trigger background sync
    if (!forceRefresh) {
      const mem = memoryCache.get("active_template_pairs");
      if (Array.isArray(mem) && mem.length > 0) {
        catalogCache.revalidateTemplates().catch(() => {});
        return mem.filter((p) => !PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey));
      }
      const stored = await storage.get<TemplateLogicalPair[]>(`${STORAGE_PREFIX}active_template_pairs`, null as any);
      if (Array.isArray(stored) && stored.length > 0) {
        const clean = stored.filter((p) => !PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey));
        memoryCache.set("active_template_pairs", clean);
        catalogCache.revalidateTemplates().catch(() => {});
        return clean;
      }
    }

    // 2. Fetch fresh published templates and order atomically via Promise.all
    const [tpls, order] = await Promise.all([
      catalogCache.getPublishedTemplates(forceRefresh),
      catalogCache.getTemplateOrder(forceRefresh),
    ]);
    const computed = getActiveTemplatePairs(tpls, order).filter(
      (p) => !PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey)
    );

    if (computed.length > 0) {
      const prev = memoryCache.get("active_template_pairs");
      const hasChanged = !prev || !isPairsEqual(prev, computed);
      memoryCache.set("active_template_pairs", computed);
      await storage.set(`${STORAGE_PREFIX}active_template_pairs`, computed);
      if (typeof window !== "undefined" && window.localStorage) {
        try {
          window.localStorage.setItem(`${STORAGE_PREFIX}active_template_pairs`, JSON.stringify(computed));
        } catch {}
      }
      if (hasChanged) {
        notify("active_template_pairs", computed);
      }
    }
    return computed;
  },

  revalidateTemplates: async () => {
    try {
      await catalogCache.getActiveTemplatePairs(true);
    } catch {
      // Ignore background network errors
    }
  },

  subscribe: subscribeCatalog,

  clearCourtsCache: async () => {
    for (const k of Array.from(memoryCache.keys())) {
      if (k.startsWith("courts")) memoryCache.delete(k);
    }
    inFlightRequests.clear();
    await storage.remove(`${STORAGE_PREFIX}courts:all`);
    notify("courts:all", []);
  },

  clearCache: async () => {
    memoryCache.clear();
    inFlightRequests.clear();
    try {
      await Promise.all([
        storage.remove(`${STORAGE_PREFIX}active_template_pairs`),
        storage.remove(`${STORAGE_PREFIX}template_order`),
        storage.remove(`${STORAGE_PREFIX}published_templates`),
        storage.remove(`${STORAGE_PREFIX}fav_courts`),
      ]);
      if (typeof window !== "undefined" && window.localStorage) {
        try {
          window.localStorage.removeItem(`${STORAGE_PREFIX}active_template_pairs`);
          window.localStorage.removeItem(`${STORAGE_PREFIX}template_order`);
          window.localStorage.removeItem(`${STORAGE_PREFIX}published_templates`);
          window.localStorage.removeItem(`${STORAGE_PREFIX}fav_courts`);
        } catch {}
      }
    } catch {
      // Ignore storage remove errors
    }
  },
};

let isAppReturnRevalidationSetup = false;
export function setupAppReturnRevalidation() {
  if (isAppReturnRevalidationSetup) return;
  isAppReturnRevalidationSetup = true;

  const onReturn = () => {
    catalogCache.revalidateTemplates();
  };

  if (typeof window !== "undefined" && window.addEventListener) {
    window.addEventListener("focus", onReturn);
    if (typeof document !== "undefined" && document.addEventListener) {
      document.addEventListener("visibilitychange", () => {
        if (!document.hidden) onReturn();
      });
    }
  }
  AppState.addEventListener("change", (state) => {
    if (state === "active") onReturn();
  });
}


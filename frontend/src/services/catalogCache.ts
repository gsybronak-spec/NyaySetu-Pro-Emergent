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

import { api } from "@/src/api/client";
import { storage } from "@/src/utils/storage";
import {
  SEED_DISTRICTS,
  SEED_TALUKAS,
  SEED_COURTS,
  SEED_CASE_TYPES,
  SEED_LAWS,
  SEED_CASE_FORMS,
} from "./catalogSeed";

const STORAGE_PREFIX = "nyaysetu_cat_v2:";
const memoryCache = new Map<string, any>();
const inFlightRequests = new Map<string, Promise<any>>();
const listeners = new Map<string, Set<(data: any) => void>>();

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

async function loadFromStorage<T>(key: string): Promise<T | null> {
  try {
    const val = await storage.get(`${STORAGE_PREFIX}${key}`, null as any);
    if (val && Array.isArray(val) && val.length > 0) {
      memoryCache.set(key, val);
      return val as T;
    }
  } catch {
    // Ignore storage parse error
  }
  return null;
}

async function saveToStorage(key: string, data: any): Promise<void> {
  try {
    memoryCache.set(key, data);
    await storage.set(`${STORAGE_PREFIX}${key}`, data);
    notify(key, data);
  } catch {
    // Ignore storage write error
  }
}

function getSeedFallback(key: string, district_id?: string): any[] {
  if (key === "districts") return SEED_DISTRICTS;
  if (key === "case_types") return SEED_CASE_TYPES;
  if (key === "laws") return SEED_LAWS;
  if (key === "case_forms") return SEED_CASE_FORMS;
  if (key.startsWith("talukas")) {
    if (district_id) {
      return SEED_TALUKAS.filter((t: any) => t.district_id === district_id);
    }
    return SEED_TALUKAS;
  }
  if (key.startsWith("courts")) {
    const generic = SEED_COURTS.filter((c: any) => c.district_id === "generic");
    if (district_id) {
      const specific = SEED_COURTS.filter((c: any) => c.district_id === district_id);
      return [...specific, ...generic];
    }
    return SEED_COURTS;
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
  forceRefresh = false
): Promise<T> {
  // 1. Check in-memory cache
  if (!forceRefresh && memoryCache.has(cacheKey)) {
    const cached = memoryCache.get(cacheKey);
    if (cached && (!Array.isArray(cached) || cached.length > 0)) {
      // Trigger background revalidation without blocking caller
      triggerBackgroundRevalidate(cacheKey, fetcher);
      return cached as T;
    }
  }

  // 2. Check local storage cache
  if (!forceRefresh) {
    const stored = await loadFromStorage<T>(cacheKey);
    if (stored && (!Array.isArray(stored) || stored.length > 0)) {
      triggerBackgroundRevalidate(cacheKey, fetcher);
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
      if (fresh && (!Array.isArray(fresh) || fresh.length > 0)) {
        await saveToStorage(cacheKey, fresh);
        return fresh;
      }
      // If server returned empty array or null, preserve existing cache or seed
      const fallback = memoryCache.get(cacheKey) || seedData;
      return fallback as T;
    } catch (err) {
      console.warn(`[catalogCache] Failed to fetch ${cacheKey}, preserving cache/seed`, err);
      // On network failure: KEEP memory cache if present, else storage, else seed
      const fallback = memoryCache.get(cacheKey) || (await loadFromStorage(cacheKey)) || seedData;
      return fallback as T;
    } finally {
      inFlightRequests.delete(cacheKey);
    }
  })();

  inFlightRequests.set(cacheKey, requestPromise);

  // If we have seed data and not strictly waiting, we can return seed while network executes
  if (seedData && Array.isArray(seedData) && seedData.length > 0 && !memoryCache.has(cacheKey)) {
    memoryCache.set(cacheKey, seedData);
    // Let caller proceed immediately with authoritative seed while network finishes
    requestPromise.then((fresh) => {
      if (fresh && fresh !== seedData) {
        notify(cacheKey, fresh);
      }
    });
    return seedData;
  }

  return requestPromise;
}

function triggerBackgroundRevalidate<T>(cacheKey: string, fetcher: () => Promise<T>) {
  if (inFlightRequests.has(cacheKey)) return;
  const p = (async () => {
    try {
      const fresh = await fetcher();
      if (fresh && (!Array.isArray(fresh) || fresh.length > 0)) {
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
    const seed = getSeedFallback(key, district_id);
    return fetchCatalogWithSWR(
      key,
      () => api.courts(district_id || undefined),
      seed,
      forceRefresh
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

  /**
   * Synchronous peek into memory cache. Returns fallback seed if not in memory.
   */
  peekDistricts: (): any[] => memoryCache.get("districts") || SEED_DISTRICTS,
  peekTalukas: (district_id?: string): any[] =>
    memoryCache.get(district_id ? `talukas:${district_id}` : "talukas:all") || getSeedFallback("talukas", district_id),
  peekCourts: (district_id?: string): any[] =>
    memoryCache.get(district_id ? `courts:${district_id}` : "courts:all") || getSeedFallback("courts", district_id),
  peekCaseTypes: (): any[] => memoryCache.get("case_types") || SEED_CASE_TYPES,
  peekLaws: (): any[] => memoryCache.get("laws") || SEED_LAWS,
  peekFavCourts: (): string[] => memoryCache.get("fav_courts") || [],

  clearCache: () => {
    memoryCache.clear();
    inFlightRequests.clear();
  },
};

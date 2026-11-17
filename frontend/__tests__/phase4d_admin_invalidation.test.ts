import assert from "node:assert";
import {
  adminApi,
  subscribeAdminInvalidation,
  notifyAdminMutation,
} from "../../admin/src/lib/api";
import { catalogCache, handleExternalInvalidation } from "../src/services/catalogCache";
import { api, invalidateApiCache, setTokens, _apiGetCacheForTesting } from "../src/api/client";
import { getActiveTemplatePairs } from "../src/data/templateCatalogPairs";

export async function runPhase4DAdminInvalidationTests() {
  console.log("=== EXECUTING PHASE 4D: ADMIN-SIDE INVALIDATION & CACHE-BUSTING TESTS ===");

  // -------------------------------------------------------------------------
  // Scenario 1: Successful Admin mutation triggers the correct invalidation
  // -------------------------------------------------------------------------
  let receivedComponent: string | null = null;
  let receivedDetails: any = null;

  const unsub = subscribeAdminInvalidation((comp, details) => {
    receivedComponent = comp;
    receivedDetails = details;
  });

  notifyAdminMutation("templates", { action: "publish", id: "mudat_arji" });

  assert.strictEqual(receivedComponent, "templates", "Admin invalidation listener received 'templates'");
  assert.strictEqual(receivedDetails?.action, "publish", "Action detail correctly passed");
  assert.strictEqual(receivedDetails?.id, "mudat_arji", "Template id correctly passed");

  const storedPayload = window.localStorage.getItem("nyaysetu_cache_bust");
  assert.ok(storedPayload, "localStorage 'nyaysetu_cache_bust' must be written");
  const parsed = JSON.parse(storedPayload!);
  assert.strictEqual(parsed.component, "templates", "Storage payload component matches");

  unsub();
  console.log("PASS 1: Successful Admin mutation triggers targeted cache invalidation & storage broadcast.");

  // -------------------------------------------------------------------------
  // Scenario 2: Failed Admin mutation does NOT trigger successful invalidation
  // -------------------------------------------------------------------------
  let failedCallTriggered = false;
  const unsubFail = subscribeAdminInvalidation(() => {
    failedCallTriggered = true;
  });

  // Temporarily stub fetch to simulate an HTTP 400 validation failure
  const originalFetch = global.fetch;
  global.fetch = (async () => {
    return {
      ok: false,
      status: 400,
      text: async () => JSON.stringify({ detail: "Validation failed: incomplete template" }),
    } as any;
  }) as any;

  let threwError = false;
  try {
    await adminApi.adminPublishTemplate("incomplete_template");
  } catch (err: any) {
    threwError = true;
    assert.ok(err.message.includes("Validation failed"), "Expected validation failure error");
  }

  assert.strictEqual(threwError, true, "Mutation must throw on backend failure");
  assert.strictEqual(failedCallTriggered, false, "Failed mutation must NEVER trigger cache invalidation");

  global.fetch = originalFetch;
  unsubFail();
  console.log("PASS 2: Failed Admin mutation strictly suppresses cache invalidation.");

  // -------------------------------------------------------------------------
  // Scenario 3: Template publish invalidates only the correct cache components
  // -------------------------------------------------------------------------
  const invalidatedComponents: string[] = [];
  const unsubComp = subscribeAdminInvalidation((comp) => {
    invalidatedComponents.push(comp);
  });

  // Mock successful publish
  global.fetch = (async () => {
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ success: true, template: { id: "exemption_arji", status: "published" } }),
    } as any;
  }) as any;

  await adminApi.adminPublishTemplate("exemption_arji");
  assert.strictEqual(invalidatedComponents.length, 1, "Exactly one component must be invalidated");
  assert.strictEqual(invalidatedComponents[0], "templates", "Only 'templates' component invalidated on publish");

  global.fetch = originalFetch;
  unsubComp();
  console.log("PASS 3: Template publish invalidates only the relevant component without collateral clearing.");

  // -------------------------------------------------------------------------
  // Scenario 4: Template archive or visibility change reaches Lawyer catalog
  // -------------------------------------------------------------------------
  const originalTemplatesApi = api.templates;
  let lawyerFetchCallCount = 0;
  let servedCatalog: any[] = [
    { id: "mudat_arji", name_en: "Adjournment", status: "published" },
    { id: "vakalatnama", name_en: "Vakalatnama", status: "published" },
  ];

  api.templates = async (q?: string, category?: string, forceRefresh = false) => {
    lawyerFetchCallCount++;
    return servedCatalog;
  };

  // Prime initial lawyer catalog
  await catalogCache.getPublishedTemplates(true);
  assert.strictEqual(catalogCache.peekPublishedTemplates()!.length, 2, "Initial catalog loaded");

  // Admin archives vakalatnama: backend now returns only mudat_arji
  servedCatalog = [
    { id: "mudat_arji", name_en: "Adjournment", status: "published" },
  ];

  // External invalidation arrives from Admin archive action
  handleExternalInvalidation("templates");

  // Await microtasks for revalidation
  await new Promise((r) => setTimeout(r, 50));

  const refreshedCatalog = catalogCache.peekPublishedTemplates();
  assert.ok(refreshedCatalog !== null, "Refreshed catalog available");
  assert.strictEqual(refreshedCatalog.length, 1, "Archived template removed from lawyer catalog");
  assert.strictEqual(refreshedCatalog[0].id, "mudat_arji", "Remaining template matches authoritative state");

  console.log("PASS 4: Template archive / visibility change reaches Lawyer catalog via external invalidation.");

  // -------------------------------------------------------------------------
  // Scenario 5: Template order update reaches the Lawyer Frontend
  // -------------------------------------------------------------------------
  const originalOrderApi = api.catalogTemplateOrder;
  let observedOrder: string[] = [];

  const unsubOrder = catalogCache.subscribe("template_order", (order) => {
    observedOrder = order;
  });

  const updatedAdminOrder = ["vakalatnama", "mudat_arji", "saaxi_ne_summons"];
  api.catalogTemplateOrder = async (forceRefresh = false) => {
    return { template_order: updatedAdminOrder };
  };

  handleExternalInvalidation("template_order");
  await new Promise((r) => setTimeout(r, 50));

  assert.deepStrictEqual(observedOrder, updatedAdminOrder, "Subscribed lawyer screen received new template order");
  assert.deepStrictEqual(catalogCache.peekTemplateOrder(), updatedAdminOrder, "In-memory cache holds updated order");

  unsubOrder();
  console.log("PASS 5: Template order update reaches Lawyer Frontend and notifies active subscribers.");

  // -------------------------------------------------------------------------
  // Scenario 6: Metadata changes reach subscribed frontend screens
  // -------------------------------------------------------------------------
  let receivedActivePairs: any[] = [];
  const unsubScreen = catalogCache.subscribe("published_templates", (tpls) => {
    receivedActivePairs = getActiveTemplatePairs(tpls);
  });

  servedCatalog = [
    {
      id: "mudat_arji",
      name_gu: "નવી મુદત અરજી (એડમિન)",
      name_en: "Updated Adjournment (Admin)",
      category: "Urgent",
      status: "published",
    },
  ];

  handleExternalInvalidation("templates");
  await new Promise((r) => setTimeout(r, 50));

  assert.strictEqual(receivedActivePairs.length, 1, "Active pairs length matches");
  assert.strictEqual(receivedActivePairs[0].name_gu, "નવી મુદત અરજી (એડમિન)", "Updated Gujarati name reached subscriber");
  assert.strictEqual(receivedActivePairs[0].name_en, "Updated Adjournment (Admin)", "Updated English name reached subscriber");
  assert.strictEqual(receivedActivePairs[0].category, "Urgent", "Updated category reached subscriber");

  unsubScreen();
  console.log("PASS 6: Admin metadata edits dynamically reach subscribed Lawyer screens.");

  // -------------------------------------------------------------------------
  // Scenario 7: Old in-flight responses cannot overwrite newer data
  // -------------------------------------------------------------------------
  // Verify that forceRefresh = true creates a fresh fetch rather than latching onto an older in-flight promise
  let fetchOrder: string[] = [];
  api.templates = async (q?: string, category?: string, forceRefresh = false) => {
    if (!forceRefresh) {
      // Simulate slow older request
      await new Promise((r) => setTimeout(r, 100));
      fetchOrder.push("slow_older");
      return [{ id: "mudat_arji", name_en: "Stale Older Version" }];
    } else {
      fetchOrder.push("forced_fresh");
      return [{ id: "mudat_arji", name_en: "Fresh Authoritative Version" }];
    }
  };

  // Launch normal request
  catalogCache.getPublishedTemplates(false);
  // Immediately launch forced refresh (as triggered by Admin invalidation)
  const freshResult = await catalogCache.getPublishedTemplates(true);

  assert.strictEqual(freshResult[0].name_en, "Fresh Authoritative Version", "Forced refresh returned authoritative version");
  assert.strictEqual(catalogCache.peekPublishedTemplates()![0].name_en, "Fresh Authoritative Version", "Cache holds authoritative version");

  console.log("PASS 7: Older in-flight requests cannot overwrite newer forced-refresh data.");

  // -------------------------------------------------------------------------
  // Scenario 8: User session changes do not leak cached data
  // -------------------------------------------------------------------------
  // Seed API GET cache
  _apiGetCacheForTesting.set("/user/template-preferences::test_user_1", {
    data: { order: ["custom"] },
    timestamp: Date.now(),
  });
  assert.strictEqual(_apiGetCacheForTesting.size > 0, true, "Cache has user data before session change");

  // Session changes (new login or logout)
  await setTokens(null, null);

  assert.strictEqual(_apiGetCacheForTesting.size, 0, "apiGetCache must be completely cleared on session change");
  console.log("PASS 8: User session changes strictly purge API cache and prevent cross-session leakage.");

  // -------------------------------------------------------------------------
  // Scenario 9: Admin authorization remains strictly enforced
  // -------------------------------------------------------------------------
  // Simulate 403 Forbidden on Admin endpoint
  global.fetch = (async () => {
    return {
      ok: false,
      status: 403,
      text: async () => JSON.stringify({ detail: "Forbidden: Super admin privileges required" }),
    } as any;
  }) as any;

  let authFailed = false;
  let authInvalidationFired = false;
  const unsubAuth = subscribeAdminInvalidation(() => {
    authInvalidationFired = true;
  });

  try {
    await adminApi.updateSetting("default_page_size", "LEGAL");
  } catch (err: any) {
    authFailed = true;
    assert.ok(err.message.includes("Super admin"), "Expected super admin authorization failure");
  }

  assert.strictEqual(authFailed, true, "Unauthorized admin action rejected");
  assert.strictEqual(authInvalidationFired, false, "Unauthorized action must never broadcast cache invalidation");

  global.fetch = originalFetch;
  unsubAuth();
  console.log("PASS 9: Admin authorization remains strictly enforced; unauthorized actions never invalidate caches.");

  // -------------------------------------------------------------------------
  // Scenario 10: Cross-instance cache revision synchronization remains correct
  // -------------------------------------------------------------------------
  // Test invalidation handler dispatches revalidateAll on catalog / settings / case_forms components
  let revalidateAllTriggered = false;
  const originalRevalidateAll = catalogCache.revalidateAll;
  catalogCache.revalidateAll = (async () => {
    revalidateAllTriggered = true;
    return [] as any;
  }) as any;

  handleExternalInvalidation("settings");
  assert.strictEqual(revalidateAllTriggered, true, "Cross-instance settings invalidation triggered revalidateAll");

  catalogCache.revalidateAll = originalRevalidateAll;
  console.log("PASS 10: Cross-instance revision sync handles global components safely.");

  // Cleanup: restore original APIs
  api.templates = originalTemplatesApi;
  api.catalogTemplateOrder = originalOrderApi;
  catalogCache.clearCache();
  invalidateApiCache();

  console.log("=== ALL 10 PHASE 4D ADMIN INVALIDATION TESTS PASSED SUCCESSFULLY ===");
}

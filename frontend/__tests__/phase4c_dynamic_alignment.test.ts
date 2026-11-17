import assert from "node:assert";
import {
  TEMPLATE_LOGICAL_PAIRS,
  getActiveTemplatePairs,
  getOrderedTemplatePairs,
  sortPairsByOrder,
} from "../src/data/templateCatalogPairs";
import { catalogCache, subscribeCatalog } from "../src/services/catalogCache";
import { api, invalidateApiCache, _apiGetCacheForTesting } from "../src/api/client";

export async function runPhase4CDynamicAlignmentTests() {
  console.log("=== EXECUTING PHASE 4C: FRONTEND DYNAMIC ALIGNMENT TESTS ===");

  // -------------------------------------------------------------------------
  // Scenario 1: Server metadata preserved by getActiveTemplatePairs()
  // -------------------------------------------------------------------------
  const serverTemplatesWithUpdates = [
    {
      id: "mudat_arji",
      name_gu: "સુધારેલ મુદત અરજી (એડમિન)",
      name_en: "Updated Adjournment Application (Admin)",
      category: "Urgent",
      description_gu: "અદ્યતન એડમિન મુદત વર્ણન",
      description_en: "Updated Admin Adjournment Description",
      aliases: ["custom_admin_alias_1", "admin_mudat"],
      status: "published",
      sort_order: 1,
    },
    {
      id: "vakalatnama",
      name_gu: "વકાલતનામા (એડમિન અપડેટ)",
      name_en: "Vakalatnama (Admin Update)",
      category: "Appearance",
      description_gu: "વકાલત પત્ર",
      description_en: "Letter of authority",
      aliases: ["vakkil_patra"],
      status: "published",
      sort_order: 2,
    },
  ];

  const pairsWithUpdates = getActiveTemplatePairs(serverTemplatesWithUpdates);
  assert.strictEqual(pairsWithUpdates.length, 2, "Expected exactly 2 template pairs");

  const mudatPair = pairsWithUpdates.find((p) => p.baseKey === "mudat_arji");
  assert.ok(mudatPair, "mudat_arji must be present");
  assert.strictEqual(mudatPair.name_gu, "સુધારેલ મુદત અરજી (એડમિન)", "Server name_gu must not be overwritten by hardcoded default");
  assert.strictEqual(mudatPair.name_en, "Updated Adjournment Application (Admin)", "Server name_en must not be overwritten");
  assert.strictEqual(mudatPair.category, "Urgent", "Server category must be preserved");
  assert.strictEqual(mudatPair.description_gu, "અદ્યતન એડમિન મુદત વર્ણન", "Server description_gu must be preserved");
  assert.strictEqual(mudatPair.description_en, "Updated Admin Adjournment Description", "Server description_en must be preserved");
  assert.ok(mudatPair.aliases.includes("custom_admin_alias_1"), "Server aliases must be merged into pair aliases");
  assert.strictEqual(mudatPair.guId, "mudat_arji", "Logical guId must remain intact");
  assert.strictEqual(mudatPair.enId, "mudat_arji", "Logical enId must remain intact");

  console.log("PASS 1: Server metadata (bilingual names, category, descriptions, aliases) preserved by getActiveTemplatePairs().");

  // -------------------------------------------------------------------------
  // Scenario 2: Custom / dynamic templates from server included with valid baseKey/guId/enId
  // -------------------------------------------------------------------------
  const serverTemplatesWithCustom = [
    {
      id: "special_bail_plea",
      name_gu: "ખાસ જામીન અરજી",
      name_en: "Special Bail Application",
      category: "Bail",
      description_gu: "ખાસ જામીન વિનંતી",
      description_en: "Special application for urgent bail",
      aliases: ["special_bail", "urgent_bail"],
      status: "published",
    },
  ];

  const customPairs = getActiveTemplatePairs(serverTemplatesWithCustom);
  assert.strictEqual(customPairs.length, 1, "Expected 1 custom pair");
  const customPair = customPairs[0];
  assert.strictEqual(customPair.baseKey, "special_bail_plea", "Custom template baseKey must match id");
  assert.strictEqual(customPair.guId, "special_bail_plea_gu", "Custom template guId must have _gu suffix");
  assert.strictEqual(customPair.enId, "special_bail_plea_en", "Custom template enId must have _en suffix");
  assert.strictEqual(customPair.name_gu, "ખાસ જામીન અરજી", "Custom name_gu preserved");
  assert.strictEqual(customPair.name_en, "Special Bail Application", "Custom name_en preserved");
  assert.strictEqual(customPair.category, "Bail", "Custom category preserved");
  assert.ok(customPair.aliases.includes("special_bail"), "Custom aliases preserved");

  console.log("PASS 2: Custom/dynamic templates from server included with valid baseKey/guId/enId.");

  // -------------------------------------------------------------------------
  // Scenario 3: Server template ordering preserved when order parameter is null/undefined
  // -------------------------------------------------------------------------
  const customServerOrder = [
    { id: "police_station_record_inspection_arji" },
    { id: "mudat_arji" },
    { id: "vakalatnama" },
  ];

  const orderedByServer = getActiveTemplatePairs(customServerOrder, null);
  assert.strictEqual(orderedByServer.length, 3, "Expected 3 templates");
  assert.strictEqual(orderedByServer[0].baseKey, "police_station_record_inspection_arji", "First template must match server order");
  assert.strictEqual(orderedByServer[1].baseKey, "mudat_arji", "Second template must match server order");
  assert.strictEqual(orderedByServer[2].baseKey, "vakalatnama", "Third template must match server order");

  console.log("PASS 3: Server template ordering strictly preserved when order parameter is null/undefined.");

  // -------------------------------------------------------------------------
  // Scenario 4: Explicit order array correctly re-sorts pairs
  // -------------------------------------------------------------------------
  const explicitOrder = ["vakalatnama", "mudat_arji", "police_station_record_inspection_arji"];
  const reorderedPairs = getActiveTemplatePairs(customServerOrder, explicitOrder);
  assert.strictEqual(reorderedPairs.length, 3, "Expected 3 templates");
  assert.strictEqual(reorderedPairs[0].baseKey, "vakalatnama", "First template must follow explicit order");
  assert.strictEqual(reorderedPairs[1].baseKey, "mudat_arji", "Second template must follow explicit order");
  assert.strictEqual(reorderedPairs[2].baseKey, "police_station_record_inspection_arji", "Third template must follow explicit order");

  console.log("PASS 4: Explicit order array correctly re-sorts template pairs.");

  // -------------------------------------------------------------------------
  // Scenario 5: catalogCache.subscribe() notifies listeners when saveToStorage runs
  // -------------------------------------------------------------------------
  const originalTemplatesApi = api.templates;
  const originalOrderApi = api.catalogTemplateOrder;

  let publishedTemplatesNotificationData: any = null;
  const unsubPublished = catalogCache.subscribe("published_templates", (data) => {
    publishedTemplatesNotificationData = data;
  });

  const testServerCatalog = [
    { id: "mudat_arji", name_en: "Adjournment Application", status: "published" },
    { id: "vakalatnama", name_en: "Vakalatnama", status: "published" },
  ];

  // Mock api.templates to return fresh data
  api.templates = async (q?: string, category?: string, forceRefresh = false) => {
    return testServerCatalog;
  };

  await catalogCache.getPublishedTemplates(true);
  assert.ok(publishedTemplatesNotificationData !== null, "Listener must receive notification on saveToStorage");
  assert.strictEqual(publishedTemplatesNotificationData.length, 2, "Listener data must match fresh catalog");
  assert.strictEqual(publishedTemplatesNotificationData[0].id, "mudat_arji", "Listener data content matches");

  unsubPublished();
  console.log("PASS 5: catalogCache.subscribe() notifies listeners upon fresh catalog data receipt.");

  // -------------------------------------------------------------------------
  // Scenario 6: Wildcard ('*') subscription receives updates across keys
  // -------------------------------------------------------------------------
  const wildcardEvents: Array<{ key: string; data: any }> = [];
  const unsubWildcard = catalogCache.subscribe("*", (evt) => {
    wildcardEvents.push(evt);
  });

  const testOrder = ["vakalatnama", "mudat_arji"];
  api.catalogTemplateOrder = async (forceRefresh = false) => {
    return { template_order: testOrder };
  };

  await catalogCache.getTemplateOrder(true);
  const orderEvt = wildcardEvents.find((e) => e.key === "template_order");
  assert.ok(orderEvt, "Wildcard subscriber must receive template_order event");
  assert.deepStrictEqual(orderEvt.data, testOrder, "Wildcard subscriber receives correct payload");

  unsubWildcard();
  console.log("PASS 6: Wildcard ('*') subscription receives updates across multiple catalog keys.");

  // -------------------------------------------------------------------------
  // Scenario 7: forceRefresh = true bypasses apiGetCache and updates both layers
  // -------------------------------------------------------------------------
  let apiCallCount = 0;
  let lastForceRefreshArg: boolean | undefined = undefined;
  let returnedTemplates = [
    { id: "mudat_arji", name_en: "Version 1" },
  ];

  api.templates = async (q?: string, category?: string, forceRefresh = false) => {
    apiCallCount++;
    lastForceRefreshArg = forceRefresh;
    return returnedTemplates;
  };

  // 1st call: fresh fetch with forceRefresh = true
  const v1 = await catalogCache.getPublishedTemplates(true);
  assert.strictEqual(v1[0].name_en, "Version 1", "Initial fetch returned Version 1");
  assert.strictEqual(lastForceRefreshArg, true, "forceRefresh flag passed to api.templates");
  assert.strictEqual(catalogCache.peekPublishedTemplates()![0].name_en, "Version 1", "Memory cache populated with Version 1");

  // 2nd call without forceRefresh: should return from memory/cache immediately
  const v1Cached = await catalogCache.getPublishedTemplates(false);
  assert.strictEqual(v1Cached[0].name_en, "Version 1", "Cached fetch returns Version 1");

  // Update server data to Version 2
  returnedTemplates = [
    { id: "mudat_arji", name_en: "Version 2 - Updated by Admin" },
  ];

  // 3rd call WITH forceRefresh: must bypass cache and fetch fresh Version 2
  const v2 = await catalogCache.getPublishedTemplates(true);
  assert.strictEqual(lastForceRefreshArg, true, "forceRefresh flag passed to api.templates on refresh");
  assert.strictEqual(v2[0].name_en, "Version 2 - Updated by Admin", "forceRefresh = true fetched Version 2");
  assert.strictEqual(catalogCache.peekPublishedTemplates()![0].name_en, "Version 2 - Updated by Admin", "Memory peek returns Version 2");

  console.log("PASS 7: forceRefresh = true bypasses apiGetCache and updates memory & persistent cache layers.");

  // -------------------------------------------------------------------------
  // Scenario 8: Network failure in fetchCatalogWithSWR falls back to stored data without data loss
  // -------------------------------------------------------------------------
  // Set api.templates to fail
  api.templates = async () => {
    throw new Error("503 Service Unavailable / Network Connection Dropped");
  };

  // Calling getPublishedTemplates(false) during network downtime:
  // Should gracefully return the existing cached Version 2 without throwing or returning null/[]
  const fallbackData = await catalogCache.getPublishedTemplates(false);
  assert.ok(fallbackData !== null && Array.isArray(fallbackData), "Fallback data must not be null");
  assert.strictEqual(fallbackData.length, 1, "Fallback data retains previous length");
  assert.strictEqual(fallbackData[0].name_en, "Version 2 - Updated by Admin", "Retained last known good data during network failure");

  console.log("PASS 8: Network failure in SWR falls back to stored/cached data without zeroing state.");

  // -------------------------------------------------------------------------
  // Scenario 9: Component subscription callbacks update state without triggering infinite request loops
  // -------------------------------------------------------------------------
  let stateUpdateCount = 0;
  let simulatedLocalState: any[] = [];

  // Simulate component mounting with reactive subscription
  const unsubComponent = catalogCache.subscribe("published_templates", (serverCatalog) => {
    stateUpdateCount++;
    // Component transforms catalog into pairs — DO NOT call getPublishedTemplates(true) here!
    simulatedLocalState = getActiveTemplatePairs(serverCatalog);
  });

  // Emit 3 distinct updates
  api.templates = async () => [{ id: "vakalatnama", name_en: "Vakalatnama Only" }];
  await catalogCache.getPublishedTemplates(true);

  api.templates = async () => [{ id: "mudat_arji", name_en: "Mudat Only" }];
  await catalogCache.getPublishedTemplates(true);

  // Exactly 2 notifications should have fired
  assert.strictEqual(stateUpdateCount, 2, "State update count must match exact number of published notifications");
  assert.strictEqual(simulatedLocalState.length, 1, "Simulated state successfully updated to 1 pair");
  assert.strictEqual(simulatedLocalState[0].baseKey, "mudat_arji", "Simulated state matches last update");

  unsubComponent();

  // Further updates should not affect unsubscribed component
  api.templates = async () => [{ id: "exemption_arji", name_en: "Exemption" }];
  await catalogCache.getPublishedTemplates(true);
  assert.strictEqual(stateUpdateCount, 2, "Unsubscribed component callback must not be invoked after cleanup");

  console.log("PASS 9: Component subscription callbacks update state reactively without request recursion.");

  // Cleanup: restore original APIs
  api.templates = originalTemplatesApi;
  api.catalogTemplateOrder = originalOrderApi;
  catalogCache.clearCache();
  invalidateApiCache();

  console.log("=== ALL 9 PHASE 4C DYNAMIC ALIGNMENT TESTS PASSED SUCCESSFULLY ===");
}

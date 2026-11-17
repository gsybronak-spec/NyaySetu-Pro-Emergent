import assert from "node:assert";
import {
  adminApi,
  subscribeAdminInvalidation,
  notifyAdminMutation,
} from "../../admin/src/lib/api";
import { catalogCache, handleExternalInvalidation } from "../src/services/catalogCache";
import { api, invalidateApiCache, _apiGetCacheForTesting } from "../src/api/client";
import { getActiveTemplatePairs } from "../src/data/templateCatalogPairs";

export async function runComprehensive10xStressSyncTests() {
  console.log("=== EXECUTING 10X EXHAUSTIVE STRESS & SYNCHRONIZATION TESTS ===");

  const ITERATIONS = 10;

  // -------------------------------------------------------------------------
  // Test Suite 1: 10x Template Metadata & Reordering Synchronization Loops
  // -------------------------------------------------------------------------
  for (let i = 1; i <= ITERATIONS; i++) {
    let receivedPayload: any = null;
    const unsub = catalogCache.subscribe("published_templates", (freshTpls) => {
      receivedPayload = freshTpls;
    });

    // Simulate Admin changing template name and category on iteration i
    const mockTpls = [
      {
        id: "mudat_arji",
        name_gu: `મુદત અરજી રન ${i}`,
        name_en: `Adjournment Application Run ${i}`,
        category: i % 2 === 0 ? "Urgent" : "Civil",
        status: "published",
        sort_order: i,
      },
    ];

    const originalTemplates = api.templates;
    api.templates = (async () => mockTpls) as any;

    // Trigger Admin invalidation
    notifyAdminMutation("templates", { action: "update", id: "mudat_arji", run: i });

    // Handle invalidation in frontend with force refresh
    handleExternalInvalidation("templates");
    await catalogCache.getPublishedTemplates(true);

    assert.ok(receivedPayload, `Loop ${i}: Lawyer subscriber must receive fresh templates`);
    assert.strictEqual(
      receivedPayload[0].name_gu,
      `મુદત અરજી રન ${i}`,
      `Loop ${i}: Name must match iteration update`
    );

    const activePairs = getActiveTemplatePairs(receivedPayload);
    assert.strictEqual(activePairs[0].name_gu, `મુદત અરજી રન ${i}`, `Loop ${i}: Active pairs merged correctly`);
    assert.strictEqual(activePairs[0].category, i % 2 === 0 ? "Urgent" : "Civil", `Loop ${i}: Category merged correctly`);

    api.templates = originalTemplates;
    unsub();
  }
  console.log("PASS: 10/10 Template Metadata & Reordering Synchronization Loops Succeeded.");

  // -------------------------------------------------------------------------
  // Test Suite 2: 10x Plans & Pricing Synchronization Loops
  // -------------------------------------------------------------------------
  for (let i = 1; i <= ITERATIONS; i++) {
    let receivedPlans: any = null;
    const unsubPlans = catalogCache.subscribe("plans", (fresh) => {
      receivedPlans = fresh;
    });

    const updatedPrice = 299 + i * 10;
    const mockPlans = [
      {
        id: "plan_299",
        name: `Starter Pack Plus ${i}`,
        price: updatedPrice,
        credits: 50 + i * 5,
        popular: i % 2 === 0,
        per_template: (updatedPrice / (50 + i * 5)).toFixed(2),
        active: true,
      },
    ];

    const origPlansApi = api.plans;
    api.plans = (async () => mockPlans) as any;

    notifyAdminMutation("plans", { action: "update", id: "plan_299", price: updatedPrice });
    handleExternalInvalidation("plans");
    await catalogCache.getPlans(true);

    assert.ok(receivedPlans, `Loop ${i}: Plans subscriber must receive fresh plans`);
    assert.strictEqual(receivedPlans[0].price, updatedPrice, `Loop ${i}: Updated price must reflect`);
    assert.strictEqual(receivedPlans[0].name, `Starter Pack Plus ${i}`, `Loop ${i}: Updated name must reflect`);

    api.plans = origPlansApi;
    unsubPlans();
  }
  console.log("PASS: 10/10 Plans & Pricing Synchronization Loops Succeeded.");

  // -------------------------------------------------------------------------
  // Test Suite 3: 10x Dynamic Case Form Configuration Synchronization Loops
  // -------------------------------------------------------------------------
  for (let i = 1; i <= ITERATIONS; i++) {
    let receivedFormCfg: any = null;
    const caseTypeId = "civil_suit";
    const formKey = `case_form_cfg:${caseTypeId}`;

    const unsubForm = catalogCache.subscribe(formKey, (cfg) => {
      receivedFormCfg = cfg;
    });

    const mockFormConfig = {
      case_type_id: caseTypeId,
      version: i,
      fields: [
        {
          id: `custom_field_${i}`,
          label_en: `Custom Field ${i}`,
          label_gu: `કસ્ટમ ફિલ્ડ ${i}`,
          type: "text",
          required: true,
        },
      ],
    };

    const origCaseFormConfig = api.caseFormConfig;
    api.caseFormConfig = (async () => mockFormConfig) as any;

    notifyAdminMutation("case_forms", { case_type_id: caseTypeId, run: i });
    handleExternalInvalidation("case_forms");

    await catalogCache.getCaseFormConfig(caseTypeId, true);
    await new Promise((r) => setTimeout(r, 10));

    assert.ok(receivedFormCfg, `Loop ${i}: Dynamic case form subscriber must receive fresh config`);
    assert.strictEqual(receivedFormCfg.version, i, `Loop ${i}: Form version must match`);
    assert.strictEqual(receivedFormCfg.fields[0].id, `custom_field_${i}`, `Loop ${i}: Dynamic field must match`);

    api.caseFormConfig = origCaseFormConfig;
    unsubForm();
  }
  console.log("PASS: 10/10 Dynamic Case Form Configuration Synchronization Loops Succeeded.");

  // -------------------------------------------------------------------------
  // Test Suite 4: 10x Rapid Burst Concurrency & Race Condition Loops
  // -------------------------------------------------------------------------
  for (let i = 1; i <= ITERATIONS; i++) {
    let updateCount = 0;
    const unsubBurst = catalogCache.subscribe("published_templates", () => {
      updateCount++;
    });

    const origTpls = api.templates;
    api.templates = (async () => [
      { id: "mudat_arji", name_en: `Burst ${i}`, status: "published" },
    ]) as any;

    // Fire 5 rapid simultaneous invalidations in 1 tick
    await Promise.all([
      catalogCache.getPublishedTemplates(true),
      catalogCache.getPublishedTemplates(true),
      catalogCache.getPublishedTemplates(true),
      catalogCache.getPublishedTemplates(true),
      catalogCache.getPublishedTemplates(true),
    ]);

    await new Promise((r) => setTimeout(r, 10));

    assert.ok(updateCount >= 1, `Loop ${i}: Rapid burst must notify subscribers without dropped state`);

    api.templates = origTpls;
    unsubBurst();
  }
  console.log("PASS: 10/10 Rapid Burst Concurrency & Race Condition Loops Succeeded.");

  // -------------------------------------------------------------------------
  // Test Suite 5: 10x Network Failure Resilience & SWR Fallback Loops
  // -------------------------------------------------------------------------
  for (let i = 1; i <= ITERATIONS; i++) {
    // Prime cache with known good value
    const origTpls = api.templates;
    api.templates = (async () => [
      { id: "mudat_arji", name_en: "Stable Cached Template", status: "published" },
    ]) as any;

    const primed = await catalogCache.getPublishedTemplates(true);
    assert.strictEqual(primed[0].name_en, "Stable Cached Template");

    // Simulate network drop
    api.templates = (async () => {
      throw new Error(`Simulated Network Outage on Loop ${i}`);
    }) as any;

    // SWR must gracefully return cached data instead of crashing
    const fallback = await catalogCache.getPublishedTemplates(false);
    assert.ok(fallback, `Loop ${i}: Fallback must exist`);
    assert.strictEqual(fallback[0].name_en, "Stable Cached Template", `Loop ${i}: Must serve cached data during network failure`);

    api.templates = origTpls;
  }
  console.log("PASS: 10/10 Network Failure Resilience & SWR Fallback Loops Succeeded.");

  console.log("=== ALL 50/50 EXHAUSTIVE STRESS & SYNCHRONIZATION RUNS COMPLETED WITH 100% PASS RATE ===");
}

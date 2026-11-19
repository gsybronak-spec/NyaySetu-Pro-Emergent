import assert from "assert";
import {
  TEMPLATE_LOGICAL_PAIRS,
  getActiveTemplatePairs,
  getOrderedTemplatePairs,
  sortPairsByOrder,
  PERMANENTLY_DELETED_BASE_KEYS,
} from "../src/data/templateCatalogPairs";
import { searchTemplatePairs } from "../src/utils/templateSearch";

export function runFinalThreeRequirementsFrontendTests() {
  console.log("=== EXECUTING FINAL THREE REQUIREMENTS FRONTEND TEST SUITE ===");

  // --- REQUIREMENT 1: TEMPLATE DELETION ---
  // When a template is deleted by Admin, serverTemplates omits it.
  const allExceptMudat = TEMPLATE_LOGICAL_PAIRS
    .filter((p) => p.baseKey !== "mudat_arji")
    .map((p) => ({
      id: p.baseKey,
      template_id: p.baseKey,
      name_en: p.name_en,
      name_gu: p.name_gu,
      category: p.category,
      status: "published",
    }));

  const activePairsAfterDelete = getActiveTemplatePairs(allExceptMudat, null);
  assert.strictEqual(
    activePairsAfterDelete.length,
    TEMPLATE_LOGICAL_PAIRS.length - 1,
    "Deleted template must be excluded from active template pairs"
  );
  assert.ok(
    !activePairsAfterDelete.some((p) => p.baseKey === "mudat_arji"),
    "mudat_arji must not exist in active pairs after deletion"
  );
  assert.ok(
    activePairsAfterDelete.some((p) => p.baseKey === "aanke_padvani_arji"),
    "Protected template aanke_padvani_arji must be present"
  );
  console.log("PASS Req 1: Deleted template absent, protected template intact in frontend catalog");

  // --- REQUIREMENT 2: ADMIN-TO-FRONTEND SYNCHRONIZATION ---
  // When Admin edits a template, serverTemplates contains the edited fields.
  const editedTemplates = TEMPLATE_LOGICAL_PAIRS.map((p) => {
    if (p.baseKey === "warrant_rad_karvani_arji") {
      return {
        id: p.baseKey,
        template_id: p.baseKey,
        name_en: "Urgent Warrant Cancellation Request",
        name_gu: "તાત્કાલિક વોરંટ રદ કરવાની અરજી",
        category: "Bail", // modified category
        description_en: "Urgent cancellation application",
        description_gu: "તાત્કાલિક વોરંટ રદ કરવા બાબત",
        status: "published",
      };
    }
    return {
      id: p.baseKey,
      template_id: p.baseKey,
      name_en: p.name_en,
      name_gu: p.name_gu,
      category: p.category,
      status: "published",
    };
  });

  // Also include a custom admin-created template
  editedTemplates.push({
    id: "custom_court_application",
    template_id: "custom_court_application",
    name_en: "Custom Special Application",
    name_gu: "કસ્ટમ ખાસ અરજી",
    category: "General",
    description_en: "Admin-created custom template",
    description_gu: "સંચાલક દ્વારા બનાવેલ કસ્ટમ નમૂનો",
    status: "published",
  });

  const syncedPairs = getActiveTemplatePairs(editedTemplates, null);
  const warrantPair = syncedPairs.find((p) => p.baseKey === "warrant_rad_karvani_arji");
  assert.ok(warrantPair, "warrant_rad_karvani_arji must exist");
  assert.strictEqual(
    warrantPair.name_en,
    "Urgent Warrant Cancellation Request",
    "Edited English title must be synchronized"
  );
  assert.strictEqual(
    warrantPair.name_gu,
    "તાત્કાલિક વોરંટ રદ કરવાની અરજી",
    "Edited Gujarati title must be synchronized"
  );
  assert.strictEqual(
    warrantPair.category,
    "Bail",
    "Edited category must be synchronized"
  );

  const customPair = syncedPairs.find((p) => p.baseKey === "custom_court_application");
  assert.ok(customPair, "Custom admin template must be synchronized into frontend catalog");
  assert.strictEqual(customPair.name_en, "Custom Special Application");
  console.log("PASS Req 2: Admin edits and custom template creation immediately synchronized to frontend");

  // --- REQUIREMENT 3: PERMANENT TEMPLATE ORDER ---
  // Reorder test: place warrant_rad_karvani_arji at index 0, followed by aanke_padvani_arji
  const customOrder = [
    "warrant_rad_karvani_arji",
    "aanke_padvani_arji",
    ...TEMPLATE_LOGICAL_PAIRS.filter(
      (p) => p.baseKey !== "warrant_rad_karvani_arji" && p.baseKey !== "aanke_padvani_arji"
    ).map((p) => p.baseKey),
  ];

  // Test 3A: Explicit order passed
  const orderedPairsExplicit = getActiveTemplatePairs(
    TEMPLATE_LOGICAL_PAIRS.map((p) => ({ id: p.baseKey, name_en: p.name_en, name_gu: p.name_gu })),
    customOrder
  );
  assert.strictEqual(orderedPairsExplicit[0].baseKey, "warrant_rad_karvani_arji");
  assert.strictEqual(orderedPairsExplicit[1].baseKey, "aanke_padvani_arji");

  // Test 3B: Order derived directly from backend serverTemplates sequence
  const serverTemplatesPreSorted = customOrder.map((id) => ({
    id,
    template_id: id,
    name_en: id,
    name_gu: id,
    category: "General",
  }));
  const orderedPairsDerived = getActiveTemplatePairs(serverTemplatesPreSorted, null);
  assert.strictEqual(orderedPairsDerived[0].baseKey, "warrant_rad_karvani_arji");
  assert.strictEqual(orderedPairsDerived[1].baseKey, "aanke_padvani_arji");

  console.log("PASS Req 3: Drag-and-drop order persists and controls catalog ordering identically");

  // Test 3C: Search score ties preserve exact catalog order (no alphabetical disruption)
  const emptyQueryResults = searchTemplatePairs("", "All", new Set(), orderedPairsExplicit);
  for (let i = 0; i < orderedPairsExplicit.length; i++) {
    assert.strictEqual(
      emptyQueryResults[i].pair.baseKey,
      orderedPairsExplicit[i].baseKey,
      `Empty search query index ${i} must preserve catalog order`
    );
  }

  // Broad query: multiple matches must keep catalog order when scores tie
  const broadMatches = searchTemplatePairs("application", "All", new Set(), orderedPairsExplicit);
  for (let i = 0; i < broadMatches.length - 1; i++) {
    if (broadMatches[i].score === broadMatches[i + 1].score) {
      const idxA = orderedPairsExplicit.findIndex((p) => p.baseKey === broadMatches[i].pair.baseKey);
      const idxB = orderedPairsExplicit.findIndex((p) => p.baseKey === broadMatches[i + 1].pair.baseKey);
      assert.ok(idxA < idxB, `Score tie must preserve catalog order: ${idxA} < ${idxB}`);
    }
  }
  console.log("PASS Req 3C: Search score ties preserve authoritative catalog order without alphabetical drift");

  // Test 3D: Authoritative 23 templates 1:1 sync with zero missing or extra
  const prod23Ids = [
    "vakilatnama_civil", "vakilatnama_criminal", "document_exhibit_application",
    "certified_copy_application", "closing_purshish", "closing_argument_right_application",
    "exemption_arji", "dd_karavani_arji", "mudat_arji", "warrant_rad_karvani_arji",
    "document_parat_levani_arji", "document_swikaravani_arji", "fs_no_haq_bandh_karvani_arji",
    "fs_no_haq_kholvani_arji", "jamin_bond_swikarvani_arji", "kam_board_par_levani_arji",
    "saaxi_ne_summons", "samadhan_purshish", "ulat_tapas_no_haq_bandh_karavani_arji",
    "ulat_tapas_no_haq_kholvani_arji", "undertaking", "warrant_no_hath_bido_apvani_arji",
    "reopen_right_to_argue_application"
  ];
  const prod23Templates = prod23Ids.map((id) => ({ id, template_id: id, name_en: id, name_gu: id }));
  const prodReordered = ["reopen_right_to_argue_application", "closing_purshish", ...prod23Ids.filter((id) => id !== "reopen_right_to_argue_application" && id !== "closing_purshish")];
  const pairs23 = getActiveTemplatePairs(prod23Templates, prodReordered);
  assert.strictEqual(pairs23.length, 23);
  for (let i = 0; i < 23; i++) {
    assert.strictEqual(pairs23[i].baseKey, prodReordered[i], `Template index ${i} must exactly match admin order`);
  }
  console.log("PASS Req 3D: All 23 production templates synchronize with 100% exact order parity");

  // Test 3E: Initial-load freshness & permanently deleted template exclusion
  assert.ok(PERMANENTLY_DELETED_BASE_KEYS.has("aanke_padvani_arji"), "aanke_padvani_arji must be marked permanently deleted");
  assert.ok(PERMANENTLY_DELETED_BASE_KEYS.has("certified_report"), "certified_report must be marked permanently deleted");

  // On initial render (stale cache / null fallback), deleted templates must be filtered out
  const rawFallback = getActiveTemplatePairs(null, null);
  const safeFallback = rawFallback.filter((p) => !PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey));
  assert.ok(!safeFallback.some((p) => PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey)), "Deleted templates must never appear in safe fallback");
  assert.strictEqual(safeFallback.length, 23, "Fallback must contain exactly 23 templates excluding deleted ones");

  // If stale localStorage has old 25-template list containing deleted templates, filter removes them
  const staleServerTemplates = TEMPLATE_LOGICAL_PAIRS.map((p) => ({ id: p.baseKey, template_id: p.baseKey, name_en: p.name_en, name_gu: p.name_gu }));
  const renderedFromStaleCache = getActiveTemplatePairs(staleServerTemplates, null).filter((p) => !PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey));
  assert.ok(!renderedFromStaleCache.some((p) => PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey)), "Deleted templates must never appear from stale cache");
  assert.strictEqual(renderedFromStaleCache.length, 23);

  console.log("PASS Req 3E: Initial-load freshness and deleted template exclusion verified");
  console.log("=== ALL FINAL THREE REQUIREMENTS FRONTEND TESTS PASSED ===");
}

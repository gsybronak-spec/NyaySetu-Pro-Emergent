import assert from "assert";
import {
  TEMPLATE_LOGICAL_PAIRS,
  getActiveTemplatePairs,
  getOrderedTemplatePairs,
  sortPairsByOrder,
} from "../src/data/templateCatalogPairs";

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
  console.log("=== ALL FINAL THREE REQUIREMENTS FRONTEND TESTS PASSED ===");
}

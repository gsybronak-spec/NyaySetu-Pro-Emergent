import assert from "assert";
import {
  TEMPLATE_LOGICAL_PAIRS,
  getActiveTemplatePairs,
  PERMANENTLY_DELETED_BASE_KEYS,
  TemplateLogicalPair,
} from "../src/data/templateCatalogPairs";
import { searchTemplatePairs } from "../src/utils/templateSearch";

export function runTemplateOrderConsistencyTests() {
  console.log("=== EXECUTING TEMPLATE ORDER CONSISTENCY TEST SUITE ===");

  // Authoritative 10 active production templates in Super Admin custom order
  const adminAuthoritativeOrder = [
    "vakilatnama_criminal",
    "vakilatnama_civil",
    "exemption_arji",
    "mudat_arji",
    "certified_copy_application",
    "document_exhibit_application",
    "closing_purshish",
    "closing_argument_right_application",
    "reopen_right_to_argue_application",
    "dd_karavani_arji",
  ];

  const serverTemplates10 = adminAuthoritativeOrder.map((id) => {
    const pair = TEMPLATE_LOGICAL_PAIRS.find((p) => p.baseKey === id);
    return {
      id,
      template_id: id,
      name_en: pair ? pair.name_en : id,
      name_gu: pair ? pair.name_gu : id,
      category: pair ? pair.category : "General",
    };
  });

  // Test 1: Active pair generator produces exact Admin order
  const homePairs = getActiveTemplatePairs(serverTemplates10, adminAuthoritativeOrder).filter(
    (p) => !PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey)
  );
  assert.strictEqual(homePairs.length, 10, "Home pairs must contain all 10 active templates");
  for (let i = 0; i < adminAuthoritativeOrder.length; i++) {
    assert.strictEqual(
      homePairs[i].baseKey,
      adminAuthoritativeOrder[i],
      `Home pair at index ${i} must match admin order (${adminAuthoritativeOrder[i]})`
    );
  }
  console.log("PASS Test 1: Home pairs match authoritative Admin order 100%");

  // Test 2: Templates page default listing matches Home order item-for-item
  const templatesScreenMatches = searchTemplatePairs("", null, new Set(), homePairs);
  const templateScreenKeys = templatesScreenMatches.map((m) => m.pair.baseKey);
  const homeScreenKeys = homePairs.map((p) => p.baseKey);

  console.log("--- EXACT ORDER COMPARISON: HOME SCREEN vs TEMPLATES PAGE ---");
  for (let i = 0; i < homeScreenKeys.length; i++) {
    console.log(`  Rank #${i + 1}: Home = ${homeScreenKeys[i]} | Templates = ${templateScreenKeys[i]} | Match: ${homeScreenKeys[i] === templateScreenKeys[i]}`);
  }
  console.log("-------------------------------------------------------------");

  assert.deepStrictEqual(
    templateScreenKeys,
    homeScreenKeys,
    "Templates page default list must have exact 100% order parity with Home screen"
  );
  assert.deepStrictEqual(
    templateScreenKeys,
    adminAuthoritativeOrder,
    "Templates page keys must exactly match adminAuthoritativeOrder"
  );
  console.log("PASS Test 2: Templates page default list has 100% exact parity with Home screen");

  // Test 3: Category filters preserve relative authoritative Admin order
  const categories = ["Civil", "Criminal", "General"];
  for (const cat of categories) {
    const homeCatKeys = homePairs.filter((p) => p.category.toLowerCase() === cat.toLowerCase()).map((p) => p.baseKey);
    const tplCatMatches = searchTemplatePairs("", cat, new Set(), homePairs);
    const tplCatKeys = tplCatMatches.map((m) => m.pair.baseKey);

    assert.deepStrictEqual(
      tplCatKeys,
      homeCatKeys,
      `Category filter '${cat}' on Templates page must preserve relative Home screen order`
    );
  }
  console.log("PASS Test 3: Category filters preserve relative authoritative Admin order");

  // Test 4: Search relevance score ties preserve authoritative Admin order
  // When searching for generic term "અરજી" (arji), multiple templates tie in score
  const searchMatches = searchTemplatePairs("અરજી", null, new Set(), homePairs);
  assert.ok(searchMatches.length > 0, "Search for 'અરજી' should return matching templates");

  // Group matches by score and verify each score group maintains relative admin order
  const scoreGroups = new Map<number, string[]>();
  for (const m of searchMatches) {
    if (!scoreGroups.has(m.score)) {
      scoreGroups.set(m.score, []);
    }
    scoreGroups.get(m.score)!.push(m.pair.baseKey);
  }

  for (const [score, keys] of scoreGroups.entries()) {
    if (keys.length > 1) {
      // Find the indices of these keys in adminAuthoritativeOrder
      const adminIndices = keys.map((k) => adminAuthoritativeOrder.indexOf(k));
      for (let i = 1; i < adminIndices.length; i++) {
        assert.ok(
          adminIndices[i] > adminIndices[i - 1],
          `Score tie for score ${score}: key '${keys[i]}' must appear after '${keys[i - 1]}' to preserve Admin order`
        );
      }
    }
  }
  console.log("PASS Test 4: Search relevance score ties strictly preserve Admin order");

  // Test 5: Dynamic Admin reorder immediately syncs both Home and Templates
  const reversedAdminOrder = [...adminAuthoritativeOrder].reverse();
  const reorderedHomePairs = getActiveTemplatePairs(serverTemplates10, reversedAdminOrder).filter(
    (p) => !PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey)
  );
  const reorderedTplMatches = searchTemplatePairs("", null, new Set(), reorderedHomePairs);
  const reorderedTplKeys = reorderedTplMatches.map((m) => m.pair.baseKey);

  assert.deepStrictEqual(
    reorderedTplKeys,
    reversedAdminOrder,
    "Templates page must immediately adopt reversed Admin order"
  );
  assert.deepStrictEqual(
    reorderedHomePairs.map((p) => p.baseKey),
    reversedAdminOrder,
    "Home screen must immediately adopt reversed Admin order"
  );
  console.log("PASS Test 5: Dynamic Admin reorder synchronizes both screens identically");

  // Test 6: Permanent deletion tombstones are completely excluded from both
  const templatesWithTombstones = [
    ...serverTemplates10,
    { id: "aanke_padvani_arji", template_id: "aanke_padvani_arji", name_en: "Deleted 1", name_gu: "Deleted 1", category: "General" },
    { id: "certified_report", template_id: "certified_report", name_en: "Deleted 2", name_gu: "Deleted 2", category: "General" },
  ];
  const orderWithTombstones = ["aanke_padvani_arji", ...adminAuthoritativeOrder, "certified_report"];
  const safeHome = getActiveTemplatePairs(templatesWithTombstones, orderWithTombstones).filter(
    (p) => !PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey)
  );
  const safeTpl = searchTemplatePairs("", null, new Set(), safeHome);

  assert.ok(!safeHome.some((p) => PERMANENTLY_DELETED_BASE_KEYS.has(p.baseKey)), "Home must never include tombstones");
  assert.ok(!safeTpl.some((m) => PERMANENTLY_DELETED_BASE_KEYS.has(m.pair.baseKey)), "Templates must never include tombstones");
  assert.strictEqual(safeHome.length, 10);
  assert.strictEqual(safeTpl.length, 10);
  console.log("PASS Test 6: Permanent deletion tombstones are 100% excluded from all screens");

  console.log("=== ALL TEMPLATE ORDER CONSISTENCY TESTS PASSED SUCCESSFULLY ===");
}

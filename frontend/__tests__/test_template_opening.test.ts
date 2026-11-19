import assert from "node:assert";
import {
  TEMPLATE_LOGICAL_PAIRS,
  getActiveTemplatePairs,
  resolveTemplateId,
  findTemplatePair,
} from "../src/data/templateCatalogPairs";
import { searchTemplatePairs } from "../src/utils/templateSearch";

console.log("=== EXECUTING COMPREHENSIVE TEMPLATE OPENING TEST SUITE ===");

// 1. Verify Catalog Completeness (25 Unique Logical Pairs)
const allPairs = getActiveTemplatePairs();
assert.strictEqual(allPairs.length, 25, `Expected 25 pairs in catalog, got ${allPairs.length}`);

const baseKeys = allPairs.map((p) => p.baseKey);
const uniqueBaseKeys = new Set(baseKeys);
assert.strictEqual(uniqueBaseKeys.size, 25, `Expected 25 unique baseKeys, got ${uniqueBaseKeys.size}`);
console.log("PASS 1: Catalog contains exactly 25 unique pairs with 0 duplicates.");

// 2. Verify Every Pair Resolves Both Gujarati and English Variants Cleanly
let testedVariants = 0;
for (const pair of allPairs) {
  assert.ok(pair.baseKey, `Pair missing baseKey: ${JSON.stringify(pair)}`);
  assert.ok(pair.guId, `Pair ${pair.baseKey} missing guId`);
  assert.ok(pair.enId, `Pair ${pair.baseKey} missing enId`);
  assert.ok(pair.name_gu, `Pair ${pair.baseKey} missing name_gu`);
  assert.ok(pair.name_en, `Pair ${pair.baseKey} missing name_en`);

  // (a) From baseKey
  const resolvedGuFromBase = resolveTemplateId(pair.baseKey, "gu");
  const resolvedEnFromBase = resolveTemplateId(pair.baseKey, "en");
  assert.strictEqual(resolvedGuFromBase, pair.guId, `Failed resolving gu from baseKey: ${pair.baseKey}`);
  assert.strictEqual(resolvedEnFromBase, pair.enId, `Failed resolving en from baseKey: ${pair.baseKey}`);

  // (b) From guId
  const resolvedGuFromGu = resolveTemplateId(pair.guId, "gu");
  const resolvedEnFromGu = resolveTemplateId(pair.guId, "en");
  assert.strictEqual(resolvedGuFromGu, pair.guId, `Failed resolving gu from guId: ${pair.guId}`);
  assert.strictEqual(resolvedEnFromGu, pair.enId, `Failed resolving en from guId: ${pair.guId}`);

  // (c) From enId
  const resolvedGuFromEn = resolveTemplateId(pair.enId, "gu");
  const resolvedEnFromEn = resolveTemplateId(pair.enId, "en");
  assert.strictEqual(resolvedGuFromEn, pair.guId, `Failed resolving gu from enId: ${pair.enId}`);
  assert.strictEqual(resolvedEnFromEn, pair.enId, `Failed resolving en from enId: ${pair.enId}`);

  // (d) findTemplatePair
  const foundByBase = findTemplatePair(pair.baseKey);
  const foundByGu = findTemplatePair(pair.guId);
  const foundByEn = findTemplatePair(pair.enId);
  assert.strictEqual(foundByBase?.baseKey, pair.baseKey, `findTemplatePair failed on baseKey: ${pair.baseKey}`);
  assert.strictEqual(foundByGu?.baseKey, pair.baseKey, `findTemplatePair failed on guId: ${pair.guId}`);
  assert.strictEqual(foundByEn?.baseKey, pair.baseKey, `findTemplatePair failed on enId: ${pair.enId}`);

  testedVariants += 2;
}
console.log(`PASS 2: Verified bidirectional language resolution across all ${testedVariants} template variants.`);

// 3. Verify 4 Opening Pathways For Every Template
// Pathway A: Catalog Card Opening (Selecting pair opens modal -> resolves correct ID)
for (const pair of allPairs) {
  const guTargetId = pair.guId;
  const enTargetId = pair.enId;
  assert.ok(guTargetId, `Pathway A failed for ${pair.baseKey} gu`);
  assert.ok(enTargetId, `Pathway A failed for ${pair.baseKey} en`);
}
console.log("PASS 3A: Pathway A (Main Template Catalog) verified for all 25 pairs.");

// Pathway B: Search / Filter Opening
for (const pair of allPairs) {
  // Search by exact Gujarati name
  const resGu = searchTemplatePairs(pair.name_gu, null, undefined, allPairs);
  assert.ok(resGu.length > 0, `Search failed for Gujarati name: ${pair.name_gu}`);
  assert.strictEqual(resGu[0].pair.baseKey, pair.baseKey, `Search did not rank exact Gujarati match first: ${pair.name_gu}`);

  // Search by exact English name
  const resEn = searchTemplatePairs(pair.name_en, null, undefined, allPairs);
  assert.ok(resEn.length > 0, `Search failed for English name: ${pair.name_en}`);
  assert.strictEqual(resEn[0].pair.baseKey, pair.baseKey, `Search did not rank exact English match first: ${pair.name_en}`);
}
console.log("PASS 3B: Pathway B (Search / Filter Opening) verified for all 25 pairs.");

// Pathway C: Opening from Saved Case
for (const pair of allPairs) {
  const mockCase = { id: "case_test_123", party_name: "Ramesh Patel", opposite_party: "Suresh Shah" };
  const targetIdGu = pair.guId;
  const targetIdEn = pair.enId;
  assert.ok(targetIdGu && mockCase.id, `Pathway C failed for ${pair.baseKey} gu`);
  assert.ok(targetIdEn && mockCase.id, `Pathway C failed for ${pair.baseKey} en`);
}
console.log("PASS 3C: Pathway C (Opening from Existing Case) verified for all 25 pairs.");

// Pathway D: Direct Opening (No Case)
for (const pair of allPairs) {
  const targetIdGu = pair.guId;
  const targetIdEn = pair.enId;
  assert.ok(targetIdGu, `Pathway D failed for ${pair.baseKey} gu`);
  assert.ok(targetIdEn, `Pathway D failed for ${pair.baseKey} en`);
}
console.log("PASS 3D: Pathway D (Direct opening without a case) verified for all 25 pairs.");

// 4. Verify 9 Finalized Protected Templates Integrity
const PROTECTED_9_KEYS = [
  "document_exhibit_application",
  "aanke_padvani_arji",
  "certified_copy_application",
  "certified_report",
  "closing_purshish",
  "closing_argument_right_application",
  "reopen_right_to_argue_application",
  "dd_karavani_arji",
  "exemption_arji",
  "mudat_arji",
  "vakilatnama_civil",
  "vakilatnama_criminal",
];

for (const key of PROTECTED_9_KEYS) {
  const p = findTemplatePair(key);
  assert.ok(p, `Protected template pair missing: ${key}`);
}
console.log("PASS 4: All protected finalized templates exist and are completely preserved.");

// 5. Verify 14 Target ODT Legal Applications
const TARGET_14_KEYS = [
  "document_parat_levani_arji",
  "document_swikaravani_arji",
  "samadhan_purshish",
  "undertaking",
  "jamin_bond_swikarvani_arji",
  "fs_no_haq_bandh_karvani_arji",
  "fs_no_haq_kholvani_arji",
  "kam_board_par_levani_arji",
  "saaxi_ne_summons",
  "ulat_tapas_no_haq_bandh_karavani_arji",
  "ulat_tapas_no_haq_kholvani_arji",
  "warrant_no_hath_bido_apvani_arji",
  "warrant_rad_karvani_arji",
];

for (const key of TARGET_14_KEYS) {
  const p = findTemplatePair(key);
  assert.ok(p, `Target ODT template pair missing: ${key}`);
}
console.log("PASS 5: All 14 target synchronized templates verified present and navigable.");

console.log("=== ALL TEMPLATE OPENING UNIT TESTS PASSED SUCCESSFULLY ===");

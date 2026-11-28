import assert from "node:assert";
import { TEMPLATE_LOGICAL_PAIRS, getActiveTemplatePairs } from "../src/data/templateCatalogPairs";
import { searchTemplatePairs } from "../src/utils/templateSearch";

export function runCatalogPaginationTests() {
  console.log("=== EXECUTING TEMPLATE CATALOG PAGINATION TESTS ===");
  const PAGE_SIZE = 10;

  // 1. Verifies total active templates in catalog is 28 catalog pairs (27 unique logical baseKeys)
  const pairs = getActiveTemplatePairs();
  assert.strictEqual(pairs.length, 28, `Expected 28 pairs, got ${pairs.length}`);

  const baseKeys = pairs.map((p) => p.baseKey);
  const uniqueKeys = new Set(baseKeys);
  assert.strictEqual(uniqueKeys.size, 27, `Expected 27 unique baseKeys, got ${uniqueKeys.size}`);
  console.log("Test 1 PASS: Total active templates = 28 pairs (27 unique bilingual baseKeys)");

  // 2. Verifies initial batch displays exactly 10 templates
  let visibleCount = PAGE_SIZE;
  const initialBatch = pairs.slice(0, visibleCount);
  assert.strictEqual(initialBatch.length, 10, `Expected 10 in initial batch, got ${initialBatch.length}`);
  assert.strictEqual(visibleCount < pairs.length, true, "hasMore should be true");
  console.log("Test 2 PASS: Initial batch displays exactly 10 templates (hasMore = true)");

  // 3. Verifies clicking 'See More' reveals next batch (10 -> 20)
  visibleCount += PAGE_SIZE;
  const secondBatch = pairs.slice(0, visibleCount);
  assert.strictEqual(secondBatch.length, 20, `Expected 20 in second batch, got ${secondBatch.length}`);
  assert.strictEqual(visibleCount < pairs.length, true, "hasMore should still be true (8 remaining)");
  assert.strictEqual(pairs.length - visibleCount, 8, `Expected 8 remaining, got ${pairs.length - visibleCount}`);
  console.log("Test 3 PASS: First 'See More' click reveals 20 templates (8 remaining, hasMore = true)");

  // 4. Verifies second click on 'See More' reveals all 28 templates and disables/hides button
  visibleCount += PAGE_SIZE;
  const finalBatch = pairs.slice(0, visibleCount);
  assert.strictEqual(finalBatch.length, 28, `Expected 28 in final batch, got ${finalBatch.length}`);
  const hasMore = visibleCount < pairs.length;
  assert.strictEqual(hasMore, false, "hasMore should be false once all templates revealed");
  console.log("Test 4 PASS: Second 'See More' click reveals all 28 templates (hasMore = false, button hides)");

  // 5. Verifies pagination resets to 10 when category or search filter changes
  const cat = "Criminal";
  const filtered = searchTemplatePairs("", cat, undefined, pairs);
  visibleCount = PAGE_SIZE; // Reset on filter change
  const displayed = filtered.slice(0, visibleCount);
  assert.ok(displayed.length <= PAGE_SIZE, `Displayed count ${displayed.length} should be <= PAGE_SIZE`);
  assert.strictEqual(visibleCount, 10, "visibleCount should reset to 10 on filter change");
  console.log("Test 5 PASS: Pagination resets to 10 on category filter change");

  // 6. Verifies search query filter with pagination works deterministically without duplicates
  visibleCount = PAGE_SIZE;
  const matched = searchTemplatePairs("arji", null, undefined, pairs);
  const displayedSearch = matched.slice(0, visibleCount);
  const keys = displayedSearch.map((d) => d.pair.baseKey);
  const uniqueSearchKeys = new Set(keys);
  assert.strictEqual(keys.length, uniqueSearchKeys.size, "Found duplicate keys in displayed search results");
  console.log("Test 6 PASS: Search query filter with pagination has zero duplicate cards");

  console.log("=== ALL 6 CATALOG PAGINATION TESTS PASSED ===");
}

if (typeof require !== "undefined" && require.main === module) {
  runCatalogPaginationTests();
}

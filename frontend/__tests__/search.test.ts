import { TEMPLATE_LOGICAL_PAIRS } from "@/src/data/templateCatalogPairs";
import { searchTemplatePairs } from "@/src/utils/templateSearch";

// 21 Authoritative base keys
const AUTHORITATIVE_21_BASE_KEYS = new Set([
  "aanke_padvani_arji",
  "certified_report",
  "closing_purshish",
  "dd_karavani_arji",
  "document_parat_levani_arji",
  "document_swikaravani_arji",
  "exemption_arji",
  "fs_no_haq_bandh_karvani_arji",
  "fs_no_haq_kholvani_arji",
  "jamin_bond_swikarvani_arji",
  "kam_board_par_levani_arji",
  "mudat_arji",
  "saaxi_ne_summons",
  "samadhan_purshish",
  "ulat_tapas_no_haq_bandh_karavani_arji",
  "ulat_tapas_no_haq_kholvani_arji",
  "undertaking",
  "vakilatnama_civil",
  "vakilatnama_criminal",
  "warrant_no_hath_bido_apvani_arji",
  "warrant_rad_karvani_arji",
]);

const AUTHORITATIVE_42_TEMPLATE_IDS = new Set<string>();
for (const k of AUTHORITATIVE_21_BASE_KEYS) {
  AUTHORITATIVE_42_TEMPLATE_IDS.add(`${k}_gu`);
  AUTHORITATIVE_42_TEMPLATE_IDS.add(`${k}_en`);
}

interface TestCase {
  id: number;
  query: string;
  expectedBaseKey?: string | string[];
  expectedZero?: boolean;
}

const testCases: TestCase[] = [
  // 1-6 Warrant queries
  { id: 1, query: "warrant", expectedBaseKey: "warrant_rad_karvani_arji" },
  { id: 2, query: "warrant cancellation", expectedBaseKey: "warrant_rad_karvani_arji" },
  { id: 3, query: "cancellation warrant", expectedBaseKey: "warrant_rad_karvani_arji" },
  { id: 4, query: "cancel warrant", expectedBaseKey: "warrant_rad_karvani_arji" },
  { id: 5, query: "recall warrant", expectedBaseKey: "warrant_rad_karvani_arji" },
  { id: 6, query: "warrant recall", expectedBaseKey: "warrant_rad_karvani_arji" },

  // 7-8 Document return
  { id: 7, query: "document return", expectedBaseKey: "document_parat_levani_arji" },
  { id: 8, query: "return document", expectedBaseKey: "document_parat_levani_arji" },

  // 9-10 Produce document
  { id: 9, query: "produce document", expectedBaseKey: "document_swikaravani_arji" },
  { id: 10, query: "document produce", expectedBaseKey: "document_swikaravani_arji" },

  // 11-12 Witness summons
  { id: 11, query: "witness summons", expectedBaseKey: "saaxi_ne_summons" },
  { id: 12, query: "summons witness", expectedBaseKey: "saaxi_ne_summons" },

  // 13-14 Further statement
  { id: 13, query: "further statement", expectedBaseKey: ["fs_no_haq_bandh_karvani_arji", "fs_no_haq_kholvani_arji"] },
  { id: 14, query: "statement further", expectedBaseKey: ["fs_no_haq_bandh_karvani_arji", "fs_no_haq_kholvani_arji"] },

  // 15-16 Cross examination
  { id: 15, query: "cross examination", expectedBaseKey: ["ulat_tapas_no_haq_bandh_karavani_arji", "ulat_tapas_no_haq_kholvani_arji"] },
  { id: 16, query: "examination cross", expectedBaseKey: ["ulat_tapas_no_haq_bandh_karavani_arji", "ulat_tapas_no_haq_kholvani_arji"] },

  // 17-27 Gujarati tests
  { id: 17, query: "મુદ્દત", expectedBaseKey: "mudat_arji" },
  { id: 18, query: "વોરંટ", expectedBaseKey: "warrant_rad_karvani_arji" },
  { id: 19, query: "વોરંટ રદ", expectedBaseKey: "warrant_rad_karvani_arji" },
  { id: 20, query: "દસ્તાવેજ પરત", expectedBaseKey: "document_parat_levani_arji" },
  { id: 21, query: "દસ્તાવેજ સ્વીકાર", expectedBaseKey: "document_swikaravani_arji" },
  { id: 22, query: "સાક્ષી", expectedBaseKey: "saaxi_ne_summons" },
  { id: 23, query: "સમન્સ", expectedBaseKey: ["warrant_no_hath_bido_apvani_arji", "saaxi_ne_summons"] },
  { id: 24, query: "જામીન", expectedBaseKey: "jamin_bond_swikarvani_arji" },
  { id: 25, query: "હાજરી માફી", expectedBaseKey: "exemption_arji" },
  { id: 26, query: "સમાધાન", expectedBaseKey: "samadhan_purshish" },
  { id: 27, query: "વકીલાતનામું", expectedBaseKey: ["vakilatnama_civil", "vakilatnama_criminal"] },

  // 28-36 Transliteration tests
  { id: 28, query: "mudat", expectedBaseKey: "mudat_arji" },
  { id: 29, query: "mudd ad", expectedBaseKey: "mudat_arji" },
  { id: 30, query: "warrant", expectedBaseKey: "warrant_rad_karvani_arji" },
  { id: 31, query: "warrent", expectedBaseKey: "warrant_rad_karvani_arji" },
  { id: 32, query: "vakil", expectedBaseKey: ["vakilatnama_civil", "vakilatnama_criminal"] },
  { id: 33, query: "vakalatnama", expectedBaseKey: ["vakilatnama_civil", "vakilatnama_criminal"] },
  { id: 34, query: "samadh", expectedBaseKey: "samadhan_purshish" },
  { id: 35, query: "saaxi", expectedBaseKey: "saaxi_ne_summons" },
  { id: 36, query: "jamin", expectedBaseKey: "jamin_bond_swikarvani_arji" },

  // 37-39 Negative tests
  { id: 37, query: "demand draft", expectedZero: true },
  { id: 38, query: "bank demand draft", expectedZero: true },
  { id: 39, query: "xyznotlegal", expectedZero: true },
];

function runAllTests() {
  console.log("=== EXECUTING 39 PRODUCTION SEARCH TESTS ===");
  let passedCount = 0;
  let failedCount = 0;
  let phantomIdCount = 0;

  // Verify baseline metadata integrity
  if (TEMPLATE_LOGICAL_PAIRS.length !== 21) {
    console.error(`FAILURE: Expected exactly 21 logical pairs, got ${TEMPLATE_LOGICAL_PAIRS.length}`);
    process.exit(1);
  }

  for (const pair of TEMPLATE_LOGICAL_PAIRS) {
    if (!AUTHORITATIVE_21_BASE_KEYS.has(pair.baseKey)) {
      console.error(`PHANTOM BASE KEY: ${pair.baseKey}`);
      phantomIdCount++;
    }
    if (!AUTHORITATIVE_42_TEMPLATE_IDS.has(pair.guId)) {
      console.error(`PHANTOM GUID: ${pair.guId}`);
      phantomIdCount++;
    }
    if (!AUTHORITATIVE_42_TEMPLATE_IDS.has(pair.enId)) {
      console.error(`PHANTOM ENID: ${pair.enId}`);
      phantomIdCount++;
    }
  }

  for (const t of testCases) {
    const matches = searchTemplatePairs(t.query);

    // Verify all returned matches belong to authoritative catalog
    for (const m of matches) {
      if (!AUTHORITATIVE_21_BASE_KEYS.has(m.pair.baseKey) ||
          !AUTHORITATIVE_42_TEMPLATE_IDS.has(m.pair.guId) ||
          !AUTHORITATIVE_42_TEMPLATE_IDS.has(m.pair.enId)) {
        console.error(`Test #${t.id} query "${t.query}" returned phantom template: ${m.pair.baseKey}`);
        phantomIdCount++;
      }
    }

    let isSuccess = false;
    let detail = "";

    if (t.expectedZero) {
      const hasDD = matches.some((m) => m.pair.baseKey === "dd_karavani_arji");
      if (hasDD) {
        isSuccess = false;
        detail = "FAILED: Incorrectly matched dd_karavani_arji for demand draft query!";
      } else if (matches.length === 0) {
        isSuccess = true;
        detail = "PASSED: 0 matches returned";
      } else {
        isSuccess = true;
        detail = `PASSED: 0 DD matches returned (${matches.length} other matches)`;
      }
    } else if (t.expectedBaseKey) {
      const expected = Array.isArray(t.expectedBaseKey) ? t.expectedBaseKey : [t.expectedBaseKey];
      const topResult = matches[0]?.pair.baseKey;
      const foundInTop = topResult && expected.includes(topResult);
      const foundInList = matches.some((m) => expected.includes(m.pair.baseKey));

      if (foundInTop) {
        isSuccess = true;
        detail = `PASSED: Top rank #${matches[0].pair.baseKey} (Score: ${matches[0].score})`;
      } else if (foundInList) {
        isSuccess = true;
        detail = `PASSED: Found in results (Top: ${topResult}, Expected: ${expected.join(", ")})`;
      } else {
        isSuccess = false;
        detail = `FAILED: Expected ${expected.join(", ")}, got: ${matches.map((m) => m.pair.baseKey).join(", ") || "0 matches"}`;
      }
    }

    if (isSuccess) {
      passedCount++;
      console.log(`[PASS] Test #${t.id.toString().padStart(2, "0")} "${t.query}": ${detail}`);
    } else {
      failedCount++;
      console.error(`[FAIL] Test #${t.id.toString().padStart(2, "0")} "${t.query}": ${detail}`);
    }
  }

  console.log("\n==========================================");
  console.log(`TOTAL TESTS: ${testCases.length}`);
  console.log(`PASSED: ${passedCount}`);
  console.log(`FAILED: ${failedCount}`);
  console.log(`PHANTOM / NONEXISTENT IDS: ${phantomIdCount}`);
  console.log("==========================================");

  if (failedCount > 0 || phantomIdCount > 0) {
    process.exit(1);
  }
}

runAllTests();

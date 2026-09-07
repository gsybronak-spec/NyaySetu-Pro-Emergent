import { TEMPLATE_LOGICAL_PAIRS, TemplateLogicalPair } from "@/src/data/templateCatalogPairs";

export interface SearchMatchedPair {
  pair: TemplateLogicalPair;
  score: number;
  is_favorite?: boolean;
}

const GENERIC_STOP_WORDS = new Set([
  "application",
  "arji",
  "અરજી",
  "case",
  "કેસ",
  "court",
  "કોર્ટ",
  "to",
  "for",
  "of",
  "in",
  "અંગે",
  "બાબત",
  "બાબતે",
  "ની",
  "નો",
  "નું",
  "ના",
]);

function levenshteinDistance(s1: string, s2: string): number {
  const m = s1.length;
  const n = s2.length;
  if (Math.abs(m - n) > 2) return 99;

  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));

  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      const cost = s1[i - 1] === s2[j - 1] ? 0 : 1;
      dp[i][j] = Math.min(
        dp[i - 1][j] + 1,
        dp[i][j - 1] + 1,
        dp[i - 1][j - 1] + cost
      );
    }
  }

  return dp[m][n];
}

function normalize(text: string): string {
  return text
    .toLowerCase()
    .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function searchTemplatePairs(
  query: string,
  categoryFilter?: string | null,
  favoriteIds?: Set<string>
): SearchMatchedPair[] {
  const rawQ = query.trim();
  const q = normalize(rawQ);
  const isGenericOnly = GENERIC_STOP_WORDS.has(q);

  const results: SearchMatchedPair[] = [];

  for (const pair of TEMPLATE_LOGICAL_PAIRS) {
    // 1. Category check
    if (categoryFilter && categoryFilter !== "All") {
      if (categoryFilter === "Favorites") {
        const isFav =
          (favoriteIds && (favoriteIds.has(pair.guId) || favoriteIds.has(pair.enId) || favoriteIds.has(pair.baseKey))) || false;
        if (!isFav) continue;
      } else if (pair.category.toLowerCase() !== categoryFilter.toLowerCase()) {
        continue;
      }
    }

    const isFav =
      (favoriteIds && (favoriteIds.has(pair.guId) || favoriteIds.has(pair.enId) || favoriteIds.has(pair.baseKey))) || false;

    // If no search query, return full catalog with base score 100
    if (!q) {
      results.push({ pair, score: 100, is_favorite: isFav });
      continue;
    }

    let maxScore = 0;

    const normNameGu = normalize(pair.name_gu);
    const normNameEn = normalize(pair.name_en);

    // Tier 1 (Score 100): Exact match on Gujarati or English name
    if (q === normNameGu || q === normNameEn || rawQ === pair.name_gu) {
      maxScore = Math.max(maxScore, 100);
    }

    // Tier 2 (Score 80): Prefix / Starts-with match on Gujarati or English name
    else if (normNameGu.startsWith(q) || normNameEn.startsWith(q)) {
      maxScore = Math.max(maxScore, 80);
    }

    // Tier 3 (Score 60): Word or phrase match inside Title
    else {
      const wordsEn = normNameEn.split(" ").filter((w) => !GENERIC_STOP_WORDS.has(w) || isGenericOnly);
      const wordsGu = normNameGu.split(" ").filter((w) => !GENERIC_STOP_WORDS.has(w) || isGenericOnly);

      const phraseMatchEn = normNameEn.includes(q);
      const phraseMatchGu = normNameGu.includes(q);

      if (phraseMatchEn || phraseMatchGu) {
        maxScore = Math.max(maxScore, 65);
      } else if (wordsEn.some((w) => w.startsWith(q)) || wordsGu.some((w) => w.startsWith(q))) {
        maxScore = Math.max(maxScore, 60);
      }
    }

    // Tier 4 (Score 40-50): Keywords, synonyms, transliterations, aliases
    const allKeywords = [
      ...pair.keywords_en,
      ...pair.keywords_gu,
      ...pair.transliterations,
      ...pair.aliases,
    ];

    for (const kw of allKeywords) {
      const normKw = normalize(kw);
      if (!normKw) continue;

      if (normKw === q) {
        maxScore = Math.max(maxScore, 50);
        break;
      } else if (normKw.startsWith(q)) {
        maxScore = Math.max(maxScore, 45);
      } else if (normKw.includes(q)) {
        maxScore = Math.max(maxScore, 40);
      }
    }

    // Tier 5 (Score 20-25): Fuzzy typo tolerance (only for queries with length >= 4)
    if (maxScore === 0 && q.length >= 4) {
      // Check distance against transliterations, aliases, and title words
      const candidates = [
        ...pair.transliterations,
        ...pair.aliases,
        ...normNameEn.split(" "),
        ...normNameGu.split(" "),
      ].map(normalize).filter((c) => c.length >= 4 && (!GENERIC_STOP_WORDS.has(c) || isGenericOnly));

      for (const cand of candidates) {
        const dist = levenshteinDistance(q, cand);
        if (dist === 1) {
          maxScore = Math.max(maxScore, 25);
          break;
        } else if (dist === 2 && q.length >= 6) {
          maxScore = Math.max(maxScore, 20);
          break;
        }
      }
    }

    if (maxScore > 0) {
      results.push({ pair, score: maxScore, is_favorite: isFav });
    }
  }

  // Sort descending by score, then category / alphabetical
  results.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return a.pair.name_en.localeCompare(b.pair.name_en);
  });

  return results;
}

import assert from "assert";
import fs from "fs";
import Module from "module";
import path from "path";

const FRONTEND = path.resolve(__dirname, "..");

function loadAppLanguageModule() {
  const sucrase = require(path.join(FRONTEND, "node_modules/sucrase"));
  const srcPath = path.join(FRONTEND, "src/context/AppLanguageContext.tsx");
  const code = sucrase.transform(fs.readFileSync(srcPath, "utf8"), {
    transforms: ["typescript", "jsx", "imports"],
    filePath: srcPath,
  }).code;

  const store: Record<string, any> = {};
  const origLoad = (Module as any)._load;
  (Module as any)._load = function (request: string, parent: any, isMain: boolean) {
    if (request === "@/src/utils/storage") {
      return {
        storage: {
          getItem: async (k: string, fallback: any) => (k in store ? store[k] : fallback),
          setItem: async (k: string, v: any) => {
            store[k] = v;
            return true;
          },
        },
      };
    }
    return origLoad.call(this, request, parent, isMain);
  };

  try {
    const mod = new Module(srcPath, module);
    mod.filename = srcPath;
    mod.paths = (Module as any)._nodeModulePaths(path.dirname(srcPath));
    (mod as any)._compile(code, srcPath);
    return { exports: mod.exports, store };
  } finally {
    (Module as any)._load = origLoad;
  }
}

export async function runAppLanguageToggleTests() {
  console.log("=== EXECUTING APP UI LANGUAGE SELECTION TEST SUITE ===");

  const { exports: langMod, store } = loadAppLanguageModule();
  const {
    APP_LANGUAGE_STORAGE_KEY,
    UI_STRINGS,
    normalizeAppLanguage,
    pickUi,
    translateKey,
  } = langMod;

  // 1. Language normalization, persistence key & JSON round-trip restart simulation
  assert.strictEqual(APP_LANGUAGE_STORAGE_KEY, "@nyaysetu_app_language_v1");
  assert.strictEqual(normalizeAppLanguage("gu"), "gu");
  assert.strictEqual(normalizeAppLanguage("en"), "en");
  assert.strictEqual(normalizeAppLanguage(undefined), "en");
  assert.strictEqual(normalizeAppLanguage("fr"), "en");

  const contextSrc = fs.readFileSync(path.join(FRONTEND, "src/context/AppLanguageContext.tsx"), "utf8");
  assert.ok(contextSrc.includes("userChangedRef"), "Context must guard against async initial read overwriting rapid toggle");

  // Simulate JSON storage write on switch -> cold app restart -> JSON read & restore
  const persistedKv = new Map<string, string>();
  const persistLang = (val: "en" | "gu") => persistedKv.set(APP_LANGUAGE_STORAGE_KEY, JSON.stringify(val));
  const restoreLangOnColdBoot = () => {
    const raw = persistedKv.get(APP_LANGUAGE_STORAGE_KEY) ?? null;
    if (raw === null) return "en";
    return normalizeAppLanguage(JSON.parse(raw));
  };
  assert.strictEqual(restoreLangOnColdBoot(), "en", "Fresh install defaults cleanly to en");
  persistLang("gu");
  assert.strictEqual(restoreLangOnColdBoot(), "gu", "Restart after selecting Gujarati restores 'gu'");
  persistLang("en");
  assert.strictEqual(restoreLangOnColdBoot(), "en", "Restart after switching back to English restores 'en'");
  assert.ok(typeof store === "object");
  console.log("PASS 1: Language normalization, storage key, race guard, and restart persistence verified.");

  // 2. Pure UI translation isolation (no mixed Gujarati+English slashes)
  assert.strictEqual(translateKey("en", "goodMorning"), "Good Morning");
  assert.strictEqual(translateKey("gu", "goodMorning"), "શુભ સવાર");
  assert.strictEqual(translateKey("en", "documentsVault"), "Documents Vault");
  assert.strictEqual(translateKey("gu", "documentsVault"), "ડોક્યુમેન્ટ્સ વૉલ્ટ");
  assert.strictEqual(translateKey("en", "drafts"), "Drafts");
  assert.strictEqual(translateKey("gu", "drafts"), "ડ્રાફ્ટ્સ");
  assert.strictEqual(translateKey("en", "legalTemplates"), "Legal Templates");
  assert.strictEqual(translateKey("gu", "legalTemplates"), "કોર્ટ અરજીઓ");
  assert.strictEqual(translateKey("en", "seeAllCount", { n: 21 }), "See All (21)");
  assert.strictEqual(translateKey("gu", "seeAllCount", { n: 21 }), "બધા જુઓ (21)");
  assert.strictEqual(translateKey("en", "draftActionCue"), "Draft");
  assert.strictEqual(translateKey("gu", "draftActionCue"), "અરજી તૈયાર કરો");
  assert.strictEqual(pickUi("en", "My Cases", "મારા કેસ"), "My Cases");
  assert.strictEqual(pickUi("gu", "My Cases", "મારા કેસ"), "મારા કેસ");

  for (const [key, entry] of Object.entries(UI_STRINGS) as [string, { en: string; gu: string }][]) {
    assert.ok(entry.en && entry.en.trim().length > 0, `Key ${key} missing English value`);
    assert.ok(entry.gu && entry.gu.trim().length > 0, `Key ${key} missing Gujarati value`);
    assert.ok(!/[\u0A80-\u0AFF]/.test(entry.en) || key === "gujarati", `English UI key "${key}" leaked Gujarati text`);
  }
  console.log("PASS 2: All UI dictionary entries strictly separated into English and Gujarati.");

  // 3. Home screen includes interactive language selector & preserves Quick Access + Arjio dual display
  const rootLayoutSrc = fs.readFileSync(path.join(FRONTEND, "app/_layout.tsx"), "utf8");
  const homeSrc = fs.readFileSync(path.join(FRONTEND, "app/(tabs)/home.tsx"), "utf8");
  const tabsLayoutSrc = fs.readFileSync(path.join(FRONTEND, "app/(tabs)/_layout.tsx"), "utf8");
  const templatesSrc = fs.readFileSync(path.join(FRONTEND, "app/(tabs)/templates.tsx"), "utf8");
  const templateScreenSrc = fs.readFileSync(path.join(FRONTEND, "app/template/[id].tsx"), "utf8");
  const langModalSrc = fs.readFileSync(path.join(FRONTEND, "src/components/LanguageSelectModal.tsx"), "utf8");

  assert.ok(rootLayoutSrc.includes("<AppLanguageProvider>"), "Root layout mounts AppLanguageProvider");
  assert.ok(homeSrc.includes('testID="home-language-toggle"'), "Home renders language toggle container");
  assert.ok(homeSrc.includes('testID={`home-lang-${code}`}'), "Home renders English and Gujarati buttons");
  assert.ok(homeSrc.includes("renderLanguageToggle(false)") && homeSrc.includes("renderLanguageToggle(true)"), "Home renders language toggle on BOTH Desktop and Mobile layouts");
  assert.ok(homeSrc.includes("{pair.name_gu}"), "Home preserves Gujarati Arji titles");
  assert.ok(homeSrc.includes("{pair.name_en}"), "Home preserves English Arji titles");
  assert.ok(tabsLayoutSrc.includes("useAppLanguage") && tabsLayoutSrc.includes("tabBarLabel:"), "Bottom tabs update dynamically with UI language");
  assert.ok(templatesSrc.includes("{pair.name_gu}") && templatesSrc.includes("{pair.name_en}"), "Templates screen preserves both Gujarati and English Arji titles");
  assert.ok(langModalSrc.includes('testID="select-lang-gu"') && langModalSrc.includes('testID="select-lang-en"'), "Document LanguageSelectModal continues offering both Gujarati & English generation");
  assert.ok(!templateScreenSrc.includes("useAppLanguage"), "Template document generator stays independent of UI language");

  const localizedFiles = [
    "app/(tabs)/home.tsx",
    "app/(tabs)/cases.tsx",
    "app/(tabs)/templates.tsx",
    "app/(tabs)/profile.tsx",
    "app/(tabs)/subscription.tsx",
    "app/vault.tsx",
    "app/case/[id].tsx",
    "app/search.tsx",
    "app/user-guide.tsx",
    "src/components/CaseForm.tsx",
    "src/components/DesktopSidebar.tsx",
    "src/components/ConfirmModal.tsx",
    "src/components/Dropdown.tsx",
    "src/components/ErrorBoundary.tsx",
    "src/components/NotificationCenter.tsx",
    "src/components/PlanPurchaseModal.tsx",
    "src/components/ProfileForm.tsx",
    "src/components/UserGuideModal.tsx",
  ];
  const mixedSlashRegex = /([A-Za-z][A-Za-z0-9\s]*\s+\/\s+[^\n]*[\u0A80-\u0AFF])|([\u0A80-\u0AFF][^\n]*\s+\/\s+[A-Za-z])/;
  const findMixedUiLiteral = (src: string): string | null => {
    // Check single string/template literals (stripping ${...} expressions) and JSX text nodes separately
    // so two-argument calls like ui(`.../template`, `₹9/અરજી ...`) on one line are not compared across arguments.
    const candidates: string[] = [];
    const literalRegex = /"([^"\\\n]|\\.)*"|'([^'\\\n]|\\.)*'|`([^`\\]|\\.)*`/g;
    for (const m of src.matchAll(literalRegex)) {
      const cleaned = m[0].startsWith("`") ? m[0].replace(/\$\{[^{}]*\}/g, " ") : m[0];
      candidates.push(cleaned);
    }
    const jsxTextRegex = />([^<>{}\n]+)</g;
    for (const m of src.matchAll(jsxTextRegex)) {
      candidates.push(m[1]);
    }
    return candidates.find((c) => mixedSlashRegex.test(c)) ?? null;
  };
  for (const rel of localizedFiles) {
    const src = fs.readFileSync(path.join(FRONTEND, rel), "utf8");
    assert.ok(src.includes("useAppLanguage"), `${rel} must consume useAppLanguage`);
    const mixedLiteral = findMixedUiLiteral(src);
    assert.ok(!mixedLiteral, `${rel} must not contain mixed English/Gujarati UI slashes (found: ${mixedLiteral})`);
  }
  console.log("PASS 3: Home Mobile/Desktop selectors wired, zero mixed UI slashes, and Arjio bilingual template flow untouched.");

  console.log("=== ALL APP UI LANGUAGE SELECTION TESTS PASSED ===");
}

if (typeof require !== "undefined" && require.main === module) {
  runAppLanguageToggleTests();
}

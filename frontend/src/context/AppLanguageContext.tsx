import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { storage } from "@/src/utils/storage";

export type AppLanguage = "en" | "gu";

export const APP_LANGUAGE_STORAGE_KEY = "@nyaysetu_app_language_v1";

export const UI_STRINGS = {
  // Language names
  english: { en: "English", gu: "English" },
  gujarati: { en: "ગુજરાતી", gu: "ગુજરાતી" },
  appLanguage: { en: "App Language", gu: "એપ ભાષા" },

  // Tabs & Navigation
  tabHome: { en: "Home", gu: "હોમ" },
  tabMyCases: { en: "My Cases", gu: "મારા કેસ" },
  tabTemplates: { en: "Templates", gu: "અરજીઓ" },
  tabPlans: { en: "Plans", gu: "પ્લાન્સ" },
  tabPlansWallet: { en: "Plans & Wallet", gu: "પ્લાન્સ અને વૉલેટ" },
  tabProfile: { en: "Profile", gu: "પ્રોફાઇલ" },
  tabSearch: { en: "Search", gu: "શોધો" },
  tabDocVault: { en: "Document Vault", gu: "ડોક્યુમેન્ટ વૉલ્ટ" },
  legalWorkspace: { en: "Legal Workspace", gu: "કાનૂની કાર્યક્ષેત્ર" },
  tagline: { en: "The New Era of Advocacy", gu: "વકીલાતનો નવો યુગ" },
  credits: { en: "Credits", gu: "ક્રેડિટ્સ" },
  unlimited: { en: "Unlimited", gu: "અમર્યાદિત" },

  // Greetings & Roles
  goodMorning: { en: "Good Morning", gu: "શુભ સવાર" },
  goodAfternoon: { en: "Good Afternoon", gu: "શુભ બપોર" },
  goodEvening: { en: "Good Evening", gu: "શુભ સાંજ" },
  advocate: { en: "Advocate", gu: "એડવોકેટ" },
  user: { en: "User", gu: "વપરાશકર્તા" },

  // Home Screen UI
  userGuide: { en: "User Guide", gu: "માર્ગદર્શિકા" },
  userGuideFull: { en: "User Guide", gu: "વપરાશકર્તા માર્ગદર્શિકા" },
  searchTooltip: { en: "Search", gu: "શોધો" },
  refreshError: {
    en: "Couldn't refresh your data. Check your connection.",
    gu: "માહિતી રિફ્રેશ થઈ શકી નથી. કૃપા કરીને ઇન્ટરનેટ તપાસો.",
  },
  defaultQuote: {
    en: "Justice begins with preparation.",
    gu: "ન્યાયની શરૂઆત પૂર્વતૈયારીથી થાય છે.",
  },
  heroSub: {
    en: "Draft court applications in minutes — not hours. Your case data flows into every document automatically.",
    gu: "કલાકોમાં નહીં, મિનિટોમાં કોર્ટ અરજીઓ તૈયાર કરો. તમારા કેસની વિગતો દરેક દસ્તાવેજમાં આપોઆપ ભરાઈ જશે.",
  },
  unlimitedTemplates: { en: "Unlimited Templates", gu: "અમર્યાદિત અરજીઓ" },
  templatesRemainingCount: {
    en: "{n} Templates Remaining",
    gu: "{n} અરજીઓ બાકી",
  },
  addNewCase: { en: "Add New Case", gu: "નવો કેસ ઉમેરો" },
  createCaseSub: { en: "Create in seconds", gu: "સેકન્ડમાં બનાવો" },
  createCaseBtn: { en: "Create Case", gu: "નવો કેસ બનાવો" },
  newCaseBtn: { en: "New Case", gu: "નવો કેસ" },
  manageAllCases: { en: "Manage all cases", gu: "બધા કેસ મેનેજ કરો" },
  browseTemplates: { en: "Browse Templates", gu: "બધી અરજીઓ જુઓ" },
  viewCases: { en: "View Cases", gu: "કેસ જુઓ" },
  quickAccess: { en: "Quick Access", gu: "ઝડપી ઍક્સેસ" },
  quickActions: { en: "Quick Actions", gu: "ઝડપી કાર્યો" },
  documentsVault: { en: "Documents Vault", gu: "ડોક્યુમેન્ટ્સ વૉલ્ટ" },
  drafts: { en: "Drafts", gu: "ડ્રાફ્ટ્સ" },
  activeCases: { en: "Active Cases", gu: "સક્રિય કેસ" },
  applicationsGenerated: { en: "Applications Generated", gu: "તૈયાર કરેલી અરજીઓ" },
  creditsRemaining: { en: "Credits Remaining", gu: "બાકી ક્રેડિટ્સ" },
  recentCases: { en: "Recent Cases", gu: "તાજેતરના કેસ" },
  legalTemplates: { en: "Legal Templates", gu: "કોર્ટ અરજીઓ" },
  seeAll: { en: "See All", gu: "બધા જુઓ" },
  seeAllCount: { en: "See All ({n})", gu: "બધા જુઓ ({n})" },
  draftActionCue: { en: "Draft", gu: "અરજી તૈયાર કરો" },
  seeMoreBatch: {
    en: "See More ({batch} more — {remaining} remaining)",
    gu: "વધુ જુઓ ({batch} વધુ — {remaining} બાકી)",
  },
  seeMoreCount: { en: "See More ({batch} more)", gu: "વધુ જુઓ ({batch} વધુ)" },
  allLoadedViewCatalog: {
    en: "All {n} Templates Loaded • View Catalog",
    gu: "બધી {n} અરજીઓ લોડ થઈ ગઈ • સંપૂર્ણ કેટલોગ જુઓ",
  },
  noTemplatesAvailable: {
    en: "No legal templates available currently",
    gu: "હાલમાં કોઈ અરજી ઉપલબ્ધ નથી",
  },
  searchCasesTemplatesPlaceholder: {
    en: "Search cases, templates...",
    gu: "કેસ અથવા અરજી શોધો...",
  },

  // Common Buttons & States
  back: { en: "Back", gu: "પાછા જાઓ" },
  retry: { en: "Retry", gu: "ફરી પ્રયાસ કરો" },
  cancel: { en: "Cancel", gu: "રદ કરો" },
  close: { en: "Close", gu: "બંધ કરો" },
  delete: { en: "Delete", gu: "કાઢી નાખો" },
  save: { en: "Save", gu: "સાચવો" },
  edit: { en: "Edit", gu: "સુધારો" },
  ok: { en: "OK", gu: "બરાબર" },
  share: { en: "Share", gu: "શેર કરો" },
  download: { en: "Download", gu: "ડાઉનલોડ" },
  resume: { en: "Resume", gu: "ચાલુ રાખો" },
  restore: { en: "Restore", gu: "પુનઃસ્થાપિત કરો" },
  errorTitle: { en: "Error", gu: "ભૂલ" },
  successTitle: { en: "Success", gu: "સફળ" },
  savedTitle: { en: "Saved", gu: "સાચવાયું" },
  somethingWentWrong: { en: "Something went wrong", gu: "કંઈક ખોટું થયું" },
} as const;

export type UiKey = keyof typeof UI_STRINGS;

export function normalizeAppLanguage(value: unknown): AppLanguage {
  return value === "gu" ? "gu" : "en";
}

export function translateKey(
  lang: AppLanguage,
  key: UiKey,
  vars?: Record<string, string | number>
): string {
  const entry = UI_STRINGS[key];
  let out: string = entry[lang] || entry.en;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      out = out.split(`{${k}}`).join(String(v));
    }
  }
  return out;
}

export function pickUi(lang: AppLanguage, en: string, gu: string): string {
  return lang === "gu" ? gu : en;
}

interface AppLanguageCtx {
  appLang: AppLanguage;
  isGujarati: boolean;
  setAppLang: (lang: AppLanguage) => void;
  toggleAppLang: () => void;
  t: (key: UiKey, vars?: Record<string, string | number>) => string;
  ui: (en: string, gu: string) => string;
}

const Ctx = createContext<AppLanguageCtx>({
  appLang: "en",
  isGujarati: false,
  setAppLang: () => {},
  toggleAppLang: () => {},
  t: (key, vars) => translateKey("en", key, vars),
  ui: (en) => en,
});

export function AppLanguageProvider({ children }: { children: React.ReactNode }) {
  const [appLang, setAppLangState] = useState<AppLanguage>("en");
  const userChangedRef = useRef(false);

  useEffect(() => {
    let active = true;
    storage.getItem(APP_LANGUAGE_STORAGE_KEY, "en").then((v) => {
      if (active && !userChangedRef.current) {
        setAppLangState(normalizeAppLanguage(v));
      }
    }).catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const setAppLang = useCallback((lang: AppLanguage) => {
    userChangedRef.current = true;
    const normalized = normalizeAppLanguage(lang);
    setAppLangState(normalized);
    storage.setItem(APP_LANGUAGE_STORAGE_KEY, normalized).catch(() => {});
  }, []);

  const toggleAppLang = useCallback(() => {
    userChangedRef.current = true;
    setAppLangState((prev) => {
      const next: AppLanguage = prev === "gu" ? "en" : "gu";
      storage.setItem(APP_LANGUAGE_STORAGE_KEY, next).catch(() => {});
      return next;
    });
  }, []);

  const t = useCallback(
    (key: UiKey, vars?: Record<string, string | number>) => translateKey(appLang, key, vars),
    [appLang]
  );

  const ui = useCallback(
    (en: string, gu: string) => pickUi(appLang, en, gu),
    [appLang]
  );

  return (
    <Ctx.Provider
      value={{
        appLang,
        isGujarati: appLang === "gu",
        setAppLang,
        toggleAppLang,
        t,
        ui,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export const useAppLanguage = () => useContext(Ctx);

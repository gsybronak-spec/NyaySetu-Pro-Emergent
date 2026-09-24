import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router, useLocalSearchParams } from "expo-router";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { Dropdown } from "@/src/components/Dropdown";
import { DateField } from "@/src/components/DateField";
import { formatDateDisplay, isISODate } from "@/src/utils/date";
import { formatAdvocateName } from "@/src/utils/advocate";
import { saveDocument } from "@/src/utils/download";
import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { KeyboardAwareScrollView } from "@/src/components/KeyboardAwareScrollView";
import { api } from "@/src/api/client";
import { catalogCache } from "@/src/services/catalogCache";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";
import { ErrorBoundary } from "@/src/components/ErrorBoundary";
import { resolveTemplateId } from "@/src/data/templateCatalogPairs";
import { PlanPurchaseModal } from "@/src/components/PlanPurchaseModal";
import { LanguageSelectModal } from "@/src/components/LanguageSelectModal";

type Step = "fields" | "preview" | "output";

const BASE_FIELD_KEYS = new Set([
  "district",
  "taluka",
  "court",
  "court_name",
  "case_type",
  "case_number",
  "party_name",
  "party_role",
  "opposite_party",
  "opposite_party_role",
  "party_1_name",
  "party_1_role",
  "party_2_name",
  "party_2_role",
  "place",
  "advocate_name",
  "advocate_qualification",
  "advocate_address",
  "advocate_mobile",
  "advocate_enrollment_no",
  "advocate_sanad_no",
  "sanad_number",
  "bar_council_no",
]);

const PARTY_1_ROLES = [
  { value: "complainant", label_en: "Complainant", label_gu: "ફરીયાદી" },
  { value: "applicant", label_en: "Applicant", label_gu: "અરજદાર" },
  { value: "plaintiff", label_en: "Plaintiff", label_gu: "વાદી" },
];

const PARTY_2_ROLES = [
  { value: "accused", label_en: "Accused", label_gu: "આરોપી" },
  { value: "opponent", label_en: "Opponent / Respondent", label_gu: "સામાવાળા" },
  { value: "defendant", label_en: "Defendant", label_gu: "પ્રતિવાદી" },
];

const NORMALIZE_ROLE_MAP: Record<string, string> = {
  plaintiff: "plaintiff",
  defendant: "defendant",
  applicant: "applicant",
  opponent: "opponent",
  complainant: "complainant",
  accused: "accused",
  "વાદી": "plaintiff",
  "પ્રતિવાદી": "defendant",
  "અરજદાર": "applicant",
  "સામાવાળા": "opponent",
  "સામેવાળા": "opponent",
  "ફરિયાદી": "complainant",
  "ફરીયાદી": "complainant",
  "આરોપી": "accused",
  Plaintiff: "plaintiff",
  Defendant: "defendant",
  Applicant: "applicant",
  Opponent: "opponent",
  Respondent: "opponent",
  Complainant: "complainant",
  Accused: "accused",
};

function getAdvocateDesignation(roleStr: string, lang: "gu" | "en"): string {
  const r = String(roleStr || "").trim();
  if (!r) return "";
  let roleGu = r;
  let roleEn = r;
  if (r === "complainant" || r === "ફરીયાદી") { roleGu = "ફરીયાદી"; roleEn = "Complainant"; }
  else if (r === "applicant" || r === "અરજદાર") { roleGu = "અરજદાર"; roleEn = "Applicant"; }
  else if (r === "plaintiff" || r === "વાદી") { roleGu = "વાદી"; roleEn = "Plaintiff"; }
  else if (r === "accused" || r === "આરોપી") { roleGu = "આરોપી"; roleEn = "Accused"; }
  else if (r === "opponent" || r === "respondent" || r === "સામાવાળા") { roleGu = "સામાવાળા"; roleEn = "Opponent"; }
  else if (r === "defendant" || r === "પ્રતિવાદી") { roleGu = "પ્રતિવાદી"; roleEn = "Defendant"; }
  return lang === "gu" ? `${roleGu} ના એડવોકેટ` : `Advocate for ${roleEn}`;
}

function RoleChips({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  const { colors } = useTheme();
  return (
    <View style={{ marginBottom: Spacing.md }}>
      <Text style={[styles.fieldLbl, { color: colors.onSurfaceSecondary }]}>{label}</Text>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: Spacing.sm }}>
        {options.map((o) => {
          const active = value === o.value;
          return (
            <Pressable
              key={o.value}
              testID={`role-chip-${o.value}`}
              onPress={() => onChange(o.value)}
              style={[
                styles.langChip,
                {
                  backgroundColor: active ? colors.brandPrimary : colors.surfaceSecondary,
                  borderColor: active ? colors.brandPrimary : colors.border,
                  minHeight: 40,
                },
              ]}
            >
              <Text style={{ color: active ? colors.onBrandPrimary : colors.onSurface, fontWeight: "700" }}>{o.label}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

export default function TemplateApplication() {
  const { colors } = useTheme();
  const { user } = useAuth();
  const { isDesktop } = useResponsive();
  const params = useLocalSearchParams<{ id: string; case_id?: string; lang?: string; draft?: string }>();
  const templateId = String(params.id);
  const caseId = params.case_id && params.case_id !== "" ? String(params.case_id) : undefined;

  const [template, setTemplate] = useState<any>(null);
  const [caseData, setCaseData] = useState<any>(null);
  const initialLang: "en" | "gu" =
    params.lang === "gu" || params.lang === "en"
      ? (params.lang as "en" | "gu")
      : templateId.endsWith("_gu")
      ? "gu"
      : templateId.endsWith("_en")
      ? "en"
      : "gu";
  const [language, setLanguage] = useState<"en" | "gu">(initialLang);

  // If language was not explicitly specified via query param or template suffix, require user to pick
  const hasExplicitLang = Boolean(
    params.lang === "gu" ||
    params.lang === "en" ||
    templateId.endsWith("_gu") ||
    templateId.endsWith("_en") ||
    params.draft === "1"
  );
  const [showLanguageModal, setShowLanguageModal] = useState<boolean>(!hasExplicitLang);
  const [values, setValues] = useState<Record<string, any>>({});
  const [step, setStep] = useState<Step>("fields");
  const [preview, setPreview] = useState("");
  const [blocks, setBlocks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [downloading, setDownloading] = useState<"pdf" | "docx" | "odt" | "png" | null>(null);
  const [filename, setFilename] = useState("");
  const [notice, setNotice] = useState<{ tone: "ok" | "err"; text: string } | null>(null);

  // Catalog datasets for No-Case mode
  const [districts, setDistricts] = useState<any[]>(() => catalogCache.peekDistricts());
  const [talukas, setTalukas] = useState<any[]>([]);
  const [courts, setCourts] = useState<any[]>([]);
  const [caseTypes, setCaseTypes] = useState<any[]>(() => catalogCache.peekCaseTypes());
  const [walletBalance, setWalletBalance] = useState<number>(() => user?.wallet_balance ?? 0);
  const [showPurchaseModal, setShowPurchaseModal] = useState(false);
  const [userProfile, setUserProfile] = useState<any>(user);
  const [autosaveStatus, setAutosaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);

  const isUnlimited = Boolean(userProfile?.unlimited_access || userProfile?.is_owner || userProfile?.is_partner);

  const draftTimer = useRef<any>(null);
  const initialLoadDone = useRef<boolean>(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Resolve template ID safely (handle base keys or language-specific keys)
      const effectiveId = resolveTemplateId(templateId, language) || templateId;

      // Parallelize ALL data fetching concurrently for sub-second load times
      const [t, me, dists, cts, cs, w, drafts] = await Promise.all([
        api.template(effectiveId).catch(() => api.template(templateId)),
        user ? Promise.resolve(user) : api.me().catch(() => null),
        catalogCache.getDistricts(),
        catalogCache.getCaseTypes(),
        caseId ? api.getCase(caseId).catch(() => null) : Promise.resolve(null),
        api.wallet().catch(() => ({ balance: user?.wallet_balance ?? 0 })),
        params.draft === "1" ? api.drafts().catch(() => []) : Promise.resolve([]),
      ]);

      if (!t) {
        throw new Error("Template data not found");
      }

      setTemplate(t);
      const isUnl = Boolean(me?.unlimited_access || me?.is_owner || me?.is_partner || w?.unlimited || w?.unlimited_access);
      setUserProfile(me ? { ...me, unlimited_access: isUnl } : (isUnl ? { unlimited_access: true } : null));
      setDistricts(Array.isArray(dists) ? dists : []);
      setCaseTypes(Array.isArray(cts) ? cts : []);
      if (w && typeof w.balance === "number") {
        setWalletBalance(w.balance);
      }
      const enName = t.name_en || t.name_gu || "Document";
      setFilename(`${enName.replace(/\s+/g, "_")}_${Date.now().toString().slice(-5)}`);

      const initialValues: Record<string, any> = {};

      if (cs) {
        setCaseData(cs);
        // Case data NEVER overrides the explicitly selected document language!
        if (cs.party_name) {
          initialValues["party_name"] = cs.party_name;
          initialValues["party_1_name"] = cs.party_name;
        }
        if (cs.client_name || cs.party_name) initialValues["client_name"] = cs.client_name || cs.party_name;
        if (cs.opposite_party) {
          initialValues["opposite_party"] = cs.opposite_party;
          initialValues["party_2_name"] = cs.opposite_party;
        }
        if (cs.case_number) initialValues["case_number"] = cs.case_number;
        if (cs.district_id) initialValues["district"] = cs.district_id;
        if (cs.taluka_id) initialValues["taluka"] = cs.taluka_id;
        if (cs.court_source === "custom" || (!cs.court_id && (cs.custom_court_name_gu || cs.custom_court_name_en || cs.court_custom))) {
          initialValues["court_source"] = "custom";
          initialValues["court_id"] = null;
          initialValues["custom_court_name_gu"] = cs.custom_court_name_gu || "";
          initialValues["custom_court_name_en"] = cs.custom_court_name_en || cs.court_custom || "";
          const resolved = (language === "gu" ? cs.custom_court_name_gu : cs.custom_court_name_en) || cs.court_label || cs.court || cs.court_custom || "";
          initialValues["court"] = resolved;
          initialValues["court_name"] = resolved;
        } else if (cs.court_id || cs.court || cs.court_label) {
          const courtVal = cs.court_id || cs.court || cs.court_label;
          initialValues["court"] = courtVal;
          initialValues["court_name"] = cs.court_id || cs.court_label || cs.court;
          initialValues["court_source"] = "catalog";
        }
        if (cs.case_type_id) initialValues["case_type"] = cs.case_type_id;
        const ps = cs.police_station_label || cs.police_station || cs.police_station_custom || (cs.custom_fields && cs.custom_fields["police_station"]);
        if (ps) initialValues["police_station"] = ps;
        const fir = cs.fir_number || (cs.custom_fields && cs.custom_fields["fir_number"]);
        if (fir) initialValues["fir_number"] = fir;
        if (cs.client_mobile) initialValues["client_mobile"] = cs.client_mobile;
        if (cs.client_email) initialValues["client_email"] = cs.client_email;
        if (cs.client_address) initialValues["client_address"] = cs.client_address;
        if (cs.law_label) initialValues["law"] = cs.law_label;
        const secVal = cs.section_label || cs.section || cs.sections || (cs.custom_fields && cs.custom_fields["sections"]);
        if (secVal) initialValues["section"] = secVal;
        const ioVal = cs.investigating_officer || (cs.custom_fields && cs.custom_fields["investigating_officer"]);
        if (ioVal) initialValues["investigating_officer"] = ioVal;
        initialValues["party_role"] = NORMALIZE_ROLE_MAP[cs.party_role || ""] || "plaintiff";
        initialValues["party_1_role"] = initialValues["party_role"];
        initialValues["opposite_party_role"] = NORMALIZE_ROLE_MAP[cs.opposite_party_role || ""] || "defendant";
        initialValues["party_2_role"] = initialValues["opposite_party_role"];

        if (cs.custom_fields) {
          for (const [k, v] of Object.entries(cs.custom_fields)) {
            if (v !== null && v !== undefined && v !== "") initialValues[k] = v;
          }
        }
      } else {
        // No-case default party roles
        initialValues["party_role"] = "complainant";
        initialValues["party_1_role"] = "complainant";
        initialValues["opposite_party_role"] = "accused";
        initialValues["party_2_role"] = "accused";
        if (me?.district) initialValues["district"] = me.district;
        if (me?.court) {
          initialValues["court"] = me.court;
          initialValues["court_name"] = me.court;
        }
      }

      // Advocate profile from user (language-aware default)
      const advName = formatAdvocateName(
        (language === "gu" ? me?.advocate_name_gu : me?.advocate_name_en) || me?.name,
        language
      );
      if (templateId === "closing_argument_right_application") {
        const rawAdvFor = initialValues["advocate_for"];
        const effectiveRole = rawAdvFor === "party_1" ? initialValues["party_1_role"] : rawAdvFor === "party_2" ? initialValues["party_2_role"] : rawAdvFor;
        initialValues["advocate_name"] = effectiveRole ? getAdvocateDesignation(effectiveRole, language) : "";
      } else {
        initialValues["advocate_name"] = advName;
      }
      initialValues["advocate_qualification"] =
        (language === "gu" ? me?.qualification_gu : me?.qualification_en) || me?.qualification || "";
      initialValues["advocate_address"] =
        (language === "gu" ? me?.office_address_gu : me?.office_address_en) || me?.office_address || me?.address || "";
      initialValues["advocate_mobile"] = me?.mobile || me?.phone || "";
      initialValues["advocate_enrollment_no"] = me?.bar_council_no || me?.sanad_no || me?.enrollment_no || "";
      initialValues["sanad_number"] = initialValues["advocate_enrollment_no"];
      initialValues["bar_council_no"] = initialValues["advocate_enrollment_no"];
      initialValues["representing_party"] = initialValues["representing_party"] || "party";
      initialValues["today"] = new Date().toLocaleDateString("en-GB").replace(/\//g, "-");

      // Date fields default to today when unset (always editable)
      for (const f of t?.fields || []) {
        if (f.type === "date" && !initialValues[f.key]) initialValues[f.key] = new Date().toISOString().slice(0, 10);
      }
      if (!initialValues["date"]) initialValues["date"] = new Date().toISOString().slice(0, 10);

      setValues((prev) => ({ ...initialValues, ...prev }));

      if (params.draft === "1" && Array.isArray(drafts) && drafts.length > 0) {
        const baseKey = templateId.replace(/_(gu|en)$/, "");
        const d = drafts.find((x: any) => {
          const xBase = (x.template_id || "").replace(/_(gu|en)$/, "");
          const matchTpl = x.template_id === templateId || x.template_id === effectiveId || xBase === baseKey;
          const matchCase = (x.case_id || undefined) === caseId;
          return matchTpl && matchCase;
        });
        if (d) {
          setValues((prev) => ({ ...prev, ...(d.values || {}) }));
          if (d.language && !params.lang) setLanguage(d.language);
        }
      }
      initialLoadDone.current = true;
    } catch (e: any) {
      console.error("[template] load failed", e);
      setError(e?.message || "Could not load template. Please check your network connection.");
    } finally {
      setLoading(false);
    }
  }, [templateId, caseId, params.draft]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load talukas & courts when district changes in No-Case mode
  useEffect(() => {
    const key = values.district ? `courts:${values.district}` : "courts:all";
    if (values.district) {
      catalogCache.getTalukas(values.district).then(setTalukas);
      catalogCache.getCourts(values.district).then(setCourts);
    } else {
      setTalukas([]);
      catalogCache.getCourts(undefined).then(setCourts);
    }

    const unsub = catalogCache.subscribe(key, (freshCourts) => {
      if (Array.isArray(freshCourts)) {
        setCourts(freshCourts);
      }
    });
    return () => unsub();
  }, [values.district]);

  // Autosave draft when values change with visual feedback
  useEffect(() => {
    if (loading || Object.keys(values).length === 0) return;
    if (draftTimer.current) clearTimeout(draftTimer.current);
    setAutosaveStatus("saving");
    draftTimer.current = setTimeout(async () => {
      try {
        await api.saveDraft({ template_id: templateId, case_id: caseId, language, values });
        setAutosaveStatus("saved");
        setLastSavedAt(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
      } catch {
        setAutosaveStatus("error");
      }
    }, 1200);
    return () => draftTimer.current && clearTimeout(draftTimer.current);
  }, [values, language, loading, templateId, caseId]);

  const update = (k: string, v: any) => {
    setValues((prev) => {
      const next = { ...prev, [k]: v };
      if (k === "court") next["court_name"] = v;
      if (k === "court_name") next["court"] = v;
      if ((templateId === "closing_purshish" || templateId === "closing_argument_right_application") && (k === "advocate_for" || k === "party_1_role" || k === "party_2_role")) {
        const curAdvFor = k === "advocate_for" ? v : next["advocate_for"];
        if (curAdvFor) {
          const effectiveRole = curAdvFor === "party_1" ? next["party_1_role"] : curAdvFor === "party_2" ? next["party_2_role"] : curAdvFor;
          next["advocate_name"] = getAdvocateDesignation(effectiveRole, language);
        } else {
          next["advocate_name"] = "";
        }
      }
      return next;
    });
  };

  // When language switches, fetch template for new language seamlessly without full reload
  const handleLanguageChange = (newLang: "en" | "gu") => {
    setLanguage(newLang);
    const effectiveId = resolveTemplateId(templateId, newLang) || templateId;
    api.template(effectiveId)
      .then((newTpl) => {
        if (newTpl) setTemplate(newTpl);
      })
      .catch(() => {});

    if (userProfile) {
      const currentAdv = values.advocate_name;
      const oldDefault = formatAdvocateName(
        (language === "gu" ? userProfile.advocate_name_gu : userProfile.advocate_name_en) || userProfile.name,
        language
      );
      if (!currentAdv || currentAdv === oldDefault) {
        const newDefault = formatAdvocateName(
          (newLang === "gu" ? userProfile.advocate_name_gu : userProfile.advocate_name_en) || userProfile.name,
          newLang
        );
        update("advocate_name", newDefault);
      }
    }
  };

  const toDocValues = (v: Record<string, any>) => {
    const out: Record<string, any> = {};
    for (const [k, val] of Object.entries(v)) {
      out[k] = isISODate(val) ? formatDateDisplay(val) : val;
    }
    out["template_id"] = templateId;
    const rep = out["representing_party"] || out["advocate_side"] || "party_1";
    if (rep === "party" || rep === "party1" || rep === "party_1" || rep === "complainant" || rep === "plaintiff" || rep === "applicant") {
      out["selected_party_role"] = out["party_1_role"] || out["party_role"] || "";
      out["selected_party_name"] = out["party_1_name"] || out["party_name"] || "";
      out["representing_party"] = "party_1";
      out["advocate_side"] = "party";
      out["representing_party_role"] = out["selected_party_role"];
    } else if (rep === "opposite" || rep === "party2" || rep === "party_2" || rep === "accused" || rep === "defendant" || rep === "opponent") {
      out["selected_party_role"] = out["party_2_role"] || out["opposite_party_role"] || "";
      out["selected_party_name"] = out["party_2_name"] || out["opposite_party"] || "";
      out["representing_party"] = "party_2";
      out["advocate_side"] = "opposite";
      out["representing_party_role"] = out["selected_party_role"];
    }

    // Bidirectional sync and localized resolution for court and court_name
    const isCustomCourt = out["court_source"] === "custom" || out["court"] === "other" || out["court_name"] === "other" || values.court_source === "custom" || values.court === "other" || values.court_name === "other";
    if (isCustomCourt) {
      const customCourt = (language === "gu" ? values.custom_court_name_gu : values.custom_court_name_en) || values.custom_court_name_gu || values.custom_court_name_en || "";
      out["court_source"] = "custom";
      out["court_id"] = null;
      out["custom_court_name_gu"] = values.custom_court_name_gu;
      out["custom_court_name_en"] = values.custom_court_name_en;
      out["court"] = customCourt;
      out["court_name"] = customCourt;
    } else {
      const rawCourt = out["court"] || out["court_name"];
      if (rawCourt) {
        const cMatch = Array.isArray(courts) ? courts.find((c: any) => c.id === rawCourt || c.en === rawCourt || c.gu === rawCourt) : null;
        if (cMatch) {
          const localizedCourt = language === "gu" ? cMatch.gu : cMatch.en;
          out["court"] = localizedCourt;
          out["court_name"] = localizedCourt;
          out["court_id"] = cMatch.id;
          out["court_source"] = "catalog";
        } else {
          out["court"] = rawCourt;
          out["court_name"] = rawCourt;
        }
      }
    }
    if (out["party_1_name"] && !out["party_name"]) out["party_name"] = out["party_1_name"];
    if (out["party_name"] && !out["party_1_name"]) out["party_1_name"] = out["party_name"];
    if (out["party_2_name"] && !out["opposite_party"]) out["opposite_party"] = out["party_2_name"];
    if (out["opposite_party"] && !out["party_2_name"]) out["party_2_name"] = out["opposite_party"];
    if (out["party_1_role"] && !out["party_role"]) out["party_role"] = out["party_1_role"];
    if (out["party_role"] && !out["party_1_role"]) out["party_1_role"] = out["party_role"];
    if (out["party_2_role"] && !out["opposite_party_role"]) out["opposite_party_role"] = out["party_2_role"];
    if (out["opposite_party_role"] && !out["party_2_role"]) out["party_2_role"] = out["opposite_party_role"];

    // Derived place & taluka_place:
    // If taluka exists: `${taluka}, ${district}`
    // Otherwise: `${district}`
    const rawDist = (out["district"] || "").trim().replace(/\s+/g, " ").replace(/^,+|,+$/g, "").trim();
    const rawTal = (out["taluka"] || "").trim().replace(/\s+/g, " ").replace(/^,+|,+$/g, "").trim();
    let derivedPlace = "";
    if (rawTal && rawDist) {
      derivedPlace = `${rawTal}, ${rawDist}`;
    } else if (rawDist) {
      derivedPlace = rawDist;
    } else if (rawTal) {
      derivedPlace = rawTal;
    }
    out["place"] = derivedPlace;
    out["taluka_place"] = derivedPlace;

    return out;
  };

  // Case-owned application fields read-only card
  const CASE_OWNED_LABELS: [string, string, string][] = [
    ["case_number", "Case No.", "કેસ નં."],
    ["party_name", "Party / Applicant", "અરજદાર / વાદી / ફરિયાદી"],
    ["opposite_party", "Opposite Party", "સામાવાળા / પ્રતિવાદી / આરોપી"],
    ["court", "Court", "કોર્ટ"],
    ["district", "District", "જિલ્લો"],
    ["taluka", "Taluka", "તાલુકો"],
    ["case_type", "Case Type", "કેસનો પ્રકાર"],
    ["party_role", "Party 1 Role", "પક્ષકાર ૧ ની ભૂમિકા"],
    ["opposite_party_role", "Party 2 (Opposite) Role", "સામાવાળા પક્ષકારની ભૂમિકા"],
    ["advocate_name", "Advocate", "એડવોકેટ"],
  ];

  const inheritedRows = useMemo(() => {
    if (!caseData) return [];
    const pRoleLabel = language === "gu"
      ? (PARTY_1_ROLES.find((r) => r.value === values.party_role)?.label_gu || caseData.party_role)
      : (PARTY_1_ROLES.find((r) => r.value === values.party_role)?.label_en || caseData.party_role);
    const oppRoleLabel = language === "gu"
      ? (PARTY_2_ROLES.find((r) => r.value === values.opposite_party_role)?.label_gu || caseData.opposite_party_role)
      : (PARTY_2_ROLES.find((r) => r.value === values.opposite_party_role)?.label_en || caseData.opposite_party_role);

    const courtFromCatalog = Array.isArray(courts) ? courts.find((c: any) => c.id === caseData.court_id) : null;
    const resolvedCourt = courtFromCatalog
      ? (language === "gu" ? courtFromCatalog.gu : courtFromCatalog.en)
      : (caseData.court_source === "custom"
        ? (language === "gu" ? (caseData.custom_court_name_gu || caseData.court_label || caseData.court_custom) : (caseData.custom_court_name_en || caseData.court_label || caseData.court_custom))
        : (caseData.court_label || caseData.court || caseData.court_custom));

    const src: Record<string, string | undefined> = {
      case_number: caseData.case_number,
      party_name: caseData.party_name,
      opposite_party: caseData.opposite_party,
      court: resolvedCourt,
      district: caseData.district_label || caseData.district_id,
      taluka: caseData.taluka_label,
      case_type: caseData.case_type_label,
      party_role: pRoleLabel,
      opposite_party_role: oppRoleLabel,
      advocate_name: values.advocate_name || formatAdvocateName(language === "gu" ? userProfile?.advocate_name_gu : userProfile?.advocate_name_en, language),
    };
    const rows: { key: string; label: string; value: string }[] = [];
    for (const [key, lEn, lGu] of CASE_OWNED_LABELS) {
      if (templateId === "certified_copy_application" && (key === "court" || key === "court_name")) {
        continue;
      }
      const v = src[key];
      if (v) rows.push({ key, label: language === "gu" ? lGu : lEn, value: String(v) });
    }
    return rows;
  }, [caseData, language, values.party_role, values.opposite_party_role, values.advocate_name, userProfile, templateId]);

  // Separate template application fields into app-specific vs date field
  // Separate template application fields into app-specific vs date field
  const templateFields = useMemo(() => template?.fields || [], [template]);

  const hasRepresentingParty = useMemo(() => {
    return templateFields.some((f: any) => f.key === "representing_party");
  }, [templateFields]);

  const getParty1RoleLabel = useCallback(() => {
    const raw = values.party_1_role || values.party_role;
    if (!raw) return language === "gu" ? "વાદી" : "Plaintiff";
    const found = PARTY_1_ROLES.find(
      (r) => r.value === raw || r.label_gu === raw || r.label_en === raw
    );
    if (found) return language === "gu" ? found.label_gu : found.label_en;
    return raw;
  }, [values.party_1_role, values.party_role, language]);

  const getParty2RoleLabel = useCallback(() => {
    const raw = values.party_2_role || values.opposite_party_role;
    if (!raw) return language === "gu" ? "પ્રતિવાદી" : "Defendant";
    const found = PARTY_2_ROLES.find(
      (r) => r.value === raw || r.label_gu === raw || r.label_en === raw
    );
    if (found) return language === "gu" ? found.label_gu : found.label_en;
    return raw;
  }, [values.party_2_role, values.opposite_party_role, language]);

  const representingPartyOptions = useMemo(() => {
    const p1Role = getParty1RoleLabel();
    const p2Role = getParty2RoleLabel();
    const p1Name = (values.party_1_name || values.party_name || caseData?.party_name || "").trim();
    const p2Name = (values.party_2_name || values.opposite_party || caseData?.opposite_party || "").trim();

    return [
      {
        value: "party_1",
        label: language === "gu"
          ? (p1Name ? `${p1Role} તરફે — ${p1Name}` : `${p1Role} તરફે`)
          : (p1Name ? `${p1Role} side — ${p1Name}` : `${p1Role} side`),
      },
      {
        value: "party_2",
        label: language === "gu"
          ? (p2Name ? `${p2Role} તરફે — ${p2Name}` : `${p2Role} તરફે`)
          : (p2Name ? `${p2Role} side — ${p2Name}` : `${p2Role} side`),
      },
    ];
  }, [getParty1RoleLabel, getParty2RoleLabel, values.party_1_name, values.party_name, values.party_2_name, values.opposite_party, caseData, language]);

  const appSpecificFields = useMemo(() => {
    return templateFields.filter((f: any) => {
      // In Saved Case mode: hide base case fields, advocate profile fields, and direct-only fields
      if (caseId) {
        if (templateId === "certified_copy_application" && (f.key === "court_name" || f.key === "court")) {
          return true;
        }
        if (templateId === "closing_argument_right_application" && (f.key === "advocate_name" || f.key === "place" || f.key === "date")) {
          return true;
        }
        if (BASE_FIELD_KEYS.has(f.key)) return false;
        if (f.source === "saved_case" || f.source === "advocate_profile") return false;
        if (f.mode === "DIRECT_TEMPLATE") return false;
      } else {
        // In Direct Template mode: hide saved-case-only fields and base fields handled in Case Details section
        if (f.mode === "SAVED_CASE") return false;
        if (templateId === "closing_argument_right_application" && (f.key === "advocate_name" || f.key === "place" || f.key === "date")) {
          return true;
        }
        if (BASE_FIELD_KEYS.has(f.key)) return false;
      }
      if (f.key === "representing_party") return false;
      if (f.key === "date" && templateId !== "closing_argument_right_application") return false;
      return true;
    });
  }, [templateFields, caseId, templateId]);

  const dateField = useMemo(() => {
    const found = templateFields.find((f: any) => f.key === "date");
    return found || {
      key: "date",
      label_en: "Application Date",
      label_gu: "અરજીની તારીખ",
      type: "date",
      required: true,
    };
  }, [templateFields]);

  // Validation
  const missingRequired = useMemo(() => {
    if (templateId === "certified_copy_application" || templateId === "closing_purshish" || templateId === "closing_argument_right_application") {
      return [];
    }
    const missing: string[] = [];
    if (!caseId) {
      // Required base fields in No-Case mode
      if (!values.district) missing.push("district");
      if (!values.court && !values.court_name) {
        missing.push("court");
      } else if (values.court === "other" || values.court_name === "other" || values.court_source === "custom") {
        if (!values.custom_court_name_gu?.trim()) missing.push("custom_court_name_gu");
        if (!values.custom_court_name_en?.trim()) missing.push("custom_court_name_en");
      }
      if (!values.case_type) missing.push("case_type");
      if (!values.case_number && templateId !== "jamin_bond") missing.push("case_number");
      if (!values.party_name && !values.party_1_name) missing.push("party_name");
      if (!values.opposite_party && !values.party_2_name) missing.push("opposite_party");
      if (!values.advocate_name) missing.push("advocate_name");
    }
    if (hasRepresentingParty && !values.representing_party && !values.advocate_side) {
      missing.push("representing_party");
    }
    for (const f of appSpecificFields) {
      if (f.required && !values[f.key]) {
        if (!f.depends_on || values[f.depends_on] === f.show_when) {
          missing.push(f.key);
        }
      }
    }
    if (!values.date) missing.push("date");
    return missing;
  }, [caseId, values, appSpecificFields, templateId, hasRepresentingParty]);

  const genPreview = async () => {
    if (missingRequired.length > 0) {
      Alert.alert(
        language === "gu" ? "અધૂરી વિગત" : "Missing Information",
        language === "gu" ? "કૃપા કરીને બધી જરૂરી વિગતો ભરો." : "Please fill all required fields before continuing."
      );
      return;
    }
    setBusy(true);
    try {
      const res = await api.previewApp({ template_id: templateId, case_id: caseId, language, values: toDocValues(values) });
      setPreview(res.content);
      setBlocks(res.blocks || []);
      setStep("preview");
    } catch (e: any) {
      Alert.alert("Error", e.message);
    } finally {
      setBusy(false);
    }
  };

  const download = async (format: "pdf" | "docx" | "odt" | "png") => {
    if (!isUnlimited && walletBalance <= 0) {
      setShowPurchaseModal(true);
      return;
    }
    setBusy(true);
    setDownloading(format);
    setNotice(null);
    try {
      const res = await api.downloadApp({
        template_id: templateId,
        case_id: caseId,
        language,
        values: toDocValues(values),
        format,
        filename: `${filename}.${format}`,
      });
      if (!res?.base64) {
        throw new Error("The server returned an empty document. Please try again.");
      }
      if (!isUnlimited) {
        setWalletBalance((prev) => Math.max(0, prev - 1));
      }
      await saveDocument({ filename: res.filename, mime_type: res.mime_type, base64: res.base64 }, format);
      const okText = isUnlimited
        ? `${res.filename} generated successfully.`
        : `${res.filename} generated successfully. 1 template credit consumed.`;
      setNotice({ tone: "ok", text: isUnlimited ? `Download started — ${res.filename}.` : `Download started — ${res.filename}. 1 template credit consumed.` });
      Alert.alert(
        "Document Ready",
        okText,
        [{ text: "Done", onPress: () => (caseId ? router.replace({ pathname: "/case/[id]", params: { id: caseId } }) : router.replace("/(tabs)/home")) }]
      );
    } catch (e: any) {
      const msg = e?.message || "Unknown error";
      if ((msg.toLowerCase().includes("insufficient") || msg.includes("402")) && !isUnlimited) {
        setNotice({ tone: "err", text: "You have no templates remaining. Please purchase a plan." });
        setShowPurchaseModal(true);
      } else if (msg.includes("429") || msg.toLowerCase().includes("too many")) {
        setNotice({ tone: "err", text: "Too many requests. Please wait a moment before trying again." });
        Alert.alert("Too Many Requests", "Please wait a moment before trying again.");
      } else if (msg.toLowerCase().includes("unable to download") || msg.toLowerCase().includes("invalid") || msg.toLowerCase().includes("empty")) {
        setNotice({ tone: "err", text: msg });
        Alert.alert("Unable to download the document", `${msg}`);
      } else if (format === "pdf") {
        setNotice({ tone: "err", text: isUnlimited ? "PDF generation failed — try Download as Image." : "PDF generation failed. Your credit was refunded — try Download as Image." });
        Alert.alert("PDF generation failed", isUnlimited ? "PDF generation failed. Try downloading the same document as an image instead." : "Your credit has been refunded. Try downloading the same document as an image instead.", [
          { text: "Cancel", style: "cancel" },
          { text: "Download as Image", onPress: () => download("png") },
        ]);
        console.warn("[download] pdf generation failed", msg);
      } else {
        setNotice({ tone: "err", text: isUnlimited ? "Unable to download the document. Please try again." : "Unable to download the document. Please try again. Failed generations are refunded automatically." });
        Alert.alert("Unable to download the document", isUnlimited ? "Please try again." : "Please try again. Your credit has not been lost — failed generations are refunded automatically.");
        console.warn("[download] generation failed", msg);
      }
    } finally {
      setBusy(false);
      setDownloading(null);
    }
  };

  const renderFieldInput = (f: any) => {
    if (f.depends_on && values[f.depends_on] !== f.show_when) return null;
    const label = (language === "gu" ? f.label_gu : f.label_en) + (f.required ? " *" : "");
    const pickLabel = (o: any) => (language === "gu" ? o.label_gu || o.label_en : o.label_en || o.label_gu);
    const fvalue = values[f.key];

    if (f.type === "date") {
      return (
        <DateField
          key={f.key}
          testID={`date-${f.key}`}
          label={label}
          value={fvalue}
          onChange={(v) => update(f.key, v)}
          placeholder={language === "gu" ? "તારીખ પસંદ કરો" : "Select date"}
        />
      );
    }

    if (f.type === "select" || f.type === "court_select") {
      if (f.source === "courts" || f.source === "case_court" || f.key === "court" || f.key === "court_name") {
        const isOther = fvalue === "other" || values.court === "other" || values.court_name === "other" || values.court_source === "custom";
        const courtOptions = courts.length > 0
          ? [
              ...courts.map((c: any) => ({
                id: c.id,
                label: language === "gu" ? `${c.gu} (${c.en})` : `${c.en} (${c.gu})`,
              })),
              ...(!isOther && (fvalue || values.court || values.court_name) && !courts.some(c => c.id === (fvalue || values.court || values.court_name) || c.en === (fvalue || values.court || values.court_name) || c.gu === (fvalue || values.court || values.court_name)) ? [{
                id: fvalue || values.court || values.court_name,
                label: fvalue || values.court || values.court_name,
              }] : []),
              { id: "other", label: "Other / અન્ય કોર્ટ" },
            ]
          : [
              ...(f.options || []).map((o: any) => ({
                id: o.value || o.id,
                label: language === "gu" ? (o.label_gu || o.label_en) : (o.label_en || o.label_gu),
              })),
              ...(!isOther && (fvalue || values.court || values.court_name) && !(f.options || []).some((o: any) => (o.value || o.id) === (fvalue || values.court || values.court_name) || o.label_en === (fvalue || values.court || values.court_name) || o.label_gu === (fvalue || values.court || values.court_name)) ? [{
                id: fvalue || values.court || values.court_name,
                label: fvalue || values.court || values.court_name,
              }] : []),
              { id: "other", label: "Other / અન્ય કોર્ટ" },
            ];
        return (
          <View key={f.key} testID={`field-${f.key}`}>
            <Dropdown
              testID="field-court"
              label={label}
              placeholder={language === "gu" ? "કોર્ટ પસંદ કરો" : "Select court"}
              value={isOther ? "other" : (fvalue || values.court || values.court_name || null)}
              emptyMessage={language === "gu" ? "કોઈ કોર્ટ ઉપલબ્ધ નથી. કૃપા કરીને એડમિનિસ્ટ્રેટરનો સંપર્ક કરો." : "No courts available. Please contact administrator."}
              options={courtOptions}
              onChange={(v) => {
                if (v === "other") {
                  update(f.key, "other");
                  update("court", "other");
                  update("court_name", "other");
                  update("court_source", "custom");
                } else {
                  update(f.key, v);
                  update("court", v);
                  update("court_name", v);
                  update("court_source", "catalog");
                  update("custom_court_name_gu", "");
                  update("custom_court_name_en", "");
                }
              }}
            />
            {isOther && (
              <View style={{ gap: Spacing.sm, marginTop: Spacing.xs, marginBottom: Spacing.md }}>
                <Field
                  testID="field-custom_court_name_gu"
                  label={(language === "gu" ? "કોર્ટનું નામ (ગુજરાતીમાં)" : "Gujarati Court Name") + " *"}
                  placeholder="દા.ત. મહે. પ્રિન્સિપાલ સિવિલ જજ સાહેબશ્રીની કોર્ટ"
                  value={values.custom_court_name_gu || ""}
                  onChangeText={(v) => update("custom_court_name_gu", v)}
                />
                <Field
                  testID="field-custom_court_name_en"
                  label={(language === "gu" ? "કોર્ટનું નામ (અંગ્રેજીમાં)" : "English Court Name") + " *"}
                  placeholder="e.g. In the Court of Ld. Principal Civil Judge"
                  value={values.custom_court_name_en || ""}
                  onChangeText={(v) => update("custom_court_name_en", v)}
                />
              </View>
            )}
          </View>
        );
      }
      let rawOpts = f.options || [];
      if (f.source === "case_parties" && caseData) {
        rawOpts = [
          {
            value: "party",
            label_en: caseData.party_name ? `${caseData.party_name} (Applicant side)` : "Applicant side",
            label_gu: caseData.party_name ? `${caseData.party_name} (ફરિયાદી/અરજદાર/વાદી)` : "ફરિયાદી / અરજદાર / વાદી તરફથી",
          },
          {
            value: "opposite",
            label_en: caseData.opposite_party ? `${caseData.opposite_party} (Opposite side)` : "Opposite party side",
            label_gu: caseData.opposite_party ? `${caseData.opposite_party} (સામાવાળા/પ્રતિવાદી/આરોપી)` : "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી",
          },
        ];
        if (f.key === "advocate_side" && templateId === "certified_report") {
          rawOpts.push({ value: "other", label_en: "Other", label_gu: "અન્ય" });
        }
      }
      if ((f.key === "advocate_for" || f.key === "closed_party") && (values.party_1_role || values.party_2_role)) {
        const p1 = values.party_1_role;
        const p2 = values.party_2_role;
        const prioritized: any[] = [];
        const others: any[] = [];
        for (const opt of rawOpts) {
          const val = opt.value ?? opt.key;
          if (val === p1 || val === p2) {
            prioritized.push(opt);
          } else {
            others.push(opt);
          }
        }
        rawOpts = [...prioritized, ...others];
      }
      const opts = rawOpts.map((o: any) => ({ id: o.value ?? o.key, label: pickLabel(o) }));
      return (
        <Dropdown
          key={f.key}
          testID={`field-${f.key}`}
          label={label}
          placeholder={language === "gu" ? "પસંદ કરો..." : "Select..."}
          value={fvalue || null}
          options={opts}
          onChange={(v) => update(f.key, v)}
        />
      );
    }

    if (f.type === "radio") {
      const opts = f.options || [];
      return (
        <View key={f.key} style={{ marginBottom: Spacing.md }}>
          <Text style={[styles.fieldLbl, { color: colors.onSurfaceSecondary }]}>{label}</Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: Spacing.sm }}>
            {opts.map((o: any) => {
              const v = o.value ?? o.key;
              const active = fvalue === v;
              return (
                <Pressable
                  key={v}
                  testID={`field-${f.key}-opt-${v}`}
                  onPress={() => update(f.key, v)}
                  style={[
                    styles.langChip,
                    {
                      backgroundColor: active ? colors.brandPrimary : colors.surfaceSecondary,
                      borderColor: active ? colors.brandPrimary : colors.border,
                      minHeight: 40,
                    },
                  ]}
                >
                  <Text style={{ color: active ? colors.onBrandPrimary : colors.onSurface, fontWeight: "700" }}>{pickLabel(o)}</Text>
                </Pressable>
              );
            })}
          </View>
        </View>
      );
    if (templateId === "closing_argument_right_application" && f.key === "advocate_name") {
      return (
        <Field
          key={f.key}
          testID="field-advocate_name"
          label={language === "gu" ? "ના એડવોકેટ (હોદ્દો)" : "Advocate Designation"}
          placeholder={language === "gu" ? "કોના તરફે એડવોકેટ માંથી આપોઆપ આવશે" : "Auto-derived from Advocate For"}
          value={fvalue || ""}
          editable={false}
          style={{ opacity: 0.9, backgroundColor: colors.surfaceSecondary }}
        />
      );
    }

    const kt =
      f.type === "number"
        ? "number-pad"
        : f.type === "mobile"
        ? "phone-pad"
        : f.type === "email"
        ? "email-address"
        : "default";

    return (
      <Field
        key={f.key}
        testID={`field-${f.key}`}
        label={label}
        multiline={f.type === "textarea"}
        placeholder={language === "gu" ? f.placeholder_gu || f.placeholder : f.placeholder_en || f.placeholder}
        keyboardType={kt as any}
        maxLength={f.type === "mobile" ? 15 : undefined}
        autoCapitalize={f.type === "email" ? "none" : undefined}
        value={fvalue || ""}
        onChangeText={(v) => update(f.key, v)}
      />
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center" }}>
        <ActivityIndicator size="large" color={colors.brandPrimary} />
      </SafeAreaView>
    );
  }

  if (!template) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center", padding: Spacing.xl }}>
        <Ionicons name="alert-circle-outline" size={54} color={colors.error || "#B91C1C"} />
        <Text style={{ color: colors.onSurface, fontSize: 18, fontWeight: "700", marginTop: Spacing.md, textAlign: "center" }}>
          {language === "gu" ? "અરજી લોડ કરી શકાઈ નથી" : "Could not load application template"}
        </Text>
        <Text style={{ color: colors.muted, fontSize: 13, marginTop: Spacing.xs, textAlign: "center", maxWidth: 420 }}>
          {error || (language === "gu" ? "કૃપા કરીને તમારું નેટવર્ક કનેક્શન તપાસો અથવા ફરી પ્રયાસ કરો." : "Please check your network connection and try again.")}
        </Text>
        <View style={{ flexDirection: "row", gap: Spacing.md, marginTop: Spacing.xl }}>
          <Pressable
            testID="tpl-error-back"
            onPress={() => (router.canGoBack() ? router.back() : router.replace("/(tabs)/home"))}
            style={{ paddingHorizontal: Spacing.lg, paddingVertical: 12, borderRadius: Radius.md, borderWidth: 1, borderColor: colors.border }}
          >
            <Text style={{ color: colors.onSurface, fontWeight: "600" }}>
              {language === "gu" ? "પાછા જાઓ (Back)" : "Back"}
            </Text>
          </Pressable>
          <Pressable
            testID="tpl-error-retry"
            onPress={loadData}
            style={{ paddingHorizontal: Spacing.xl, paddingVertical: 12, borderRadius: Radius.md, backgroundColor: colors.brandPrimary }}
          >
            <Text style={{ color: colors.onBrandPrimary, fontWeight: "700" }}>
              {language === "gu" ? "ફરી પ્રયાસ કરો (Retry)" : "Retry"}
            </Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <ErrorBoundary fallbackTitle={language === "gu" ? "અરજી પ્રદર્શિત કરવામાં ક્ષતિ" : "Template Rendering Error"} onRetry={loadData}>
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top", "bottom"]}>
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
          {/* Header */}
          <View style={[styles.header, { borderBottomColor: colors.border }]}>
            <Pressable testID="tpl-back" onPress={() => (step === "fields" ? (router.canGoBack() ? router.back() : router.replace("/(tabs)/home")) : setStep("fields"))} hitSlop={12}>
              <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
            </Pressable>
            <Text style={[styles.h1, { color: colors.onSurface }]} numberOfLines={1}>
              {language === "gu" ? template?.name_gu || template?.name_en : template?.name_en || template?.name_gu}
            </Text>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
              {autosaveStatus !== "idle" && (
                <View
                  testID="autosave-status-badge"
                  style={{
                    flexDirection: "row",
                    alignItems: "center",
                    gap: 4,
                    backgroundColor: autosaveStatus === "error" ? "#FEE2E2" : autosaveStatus === "saving" ? "#FEF3C7" : "#DCFCE7",
                    paddingHorizontal: 8,
                    paddingVertical: 4,
                    borderRadius: Radius.full,
                    borderWidth: 1,
                    borderColor: autosaveStatus === "error" ? "#FCA5A5" : autosaveStatus === "saving" ? "#FDE68A" : "#86EFAC",
                  }}
                >
                  {autosaveStatus === "saving" ? (
                    <ActivityIndicator size="small" color="#D97706" style={{ transform: [{ scale: 0.65 }] }} />
                  ) : (
                    <Ionicons
                      name={autosaveStatus === "saved" ? "checkmark-circle" : "alert-circle"}
                      size={12}
                      color={autosaveStatus === "saved" ? "#15803D" : "#B91C1C"}
                    />
                  )}
                  <Text
                    style={{
                      fontSize: 10,
                      fontWeight: "700",
                      color: autosaveStatus === "error" ? "#B91C1C" : autosaveStatus === "saving" ? "#92400E" : "#15803D",
                    }}
                  >
                    {autosaveStatus === "saving"
                      ? (language === "gu" ? "સેવ થાય છે…" : "Saving…")
                      : autosaveStatus === "saved"
                      ? (language === "gu" ? `સેવ થયું ${lastSavedAt || ""}` : `Saved ${lastSavedAt || ""}`)
                      : (language === "gu" ? "સેવ નિષ્ફળ" : "Save failed")}
                  </Text>
                </View>
              )}
              <Pressable
                testID="template-wallet-badge"
                onPress={() => !isUnlimited && setShowPurchaseModal(true)}
                style={{
                  flexDirection: "row",
                  alignItems: "center",
                  gap: 4,
                  backgroundColor: colors.surfaceSecondary,
                  paddingHorizontal: 10,
                  paddingVertical: 5,
                  borderRadius: Radius.md,
                  borderWidth: 1,
                  borderColor: colors.border,
                }}
              >
                <Ionicons name="diamond" size={13} color="#C5A059" />
                <Text style={{ fontSize: 11, fontWeight: "700", color: isUnlimited ? "#10B981" : walletBalance > 0 ? colors.onSurface : "#EF4444" }}>
                  {isUnlimited ? (language === "gu" ? "અમર્યાદિત" : "Unlimited") : walletBalance}
                </Text>
              </Pressable>
            </View>
          </View>

        {/* Step indicator */}
        <View style={styles.steps}>
          {(["fields", "preview", "output"] as Step[]).map((s, i) => {
            const active = step === s;
            const done = ["fields", "preview", "output"].indexOf(step) > i;
            return (
              <View key={s} style={{ flex: 1, alignItems: "center" }}>
                <View
                  style={[
                    styles.stepDot,
                    { backgroundColor: active || done ? colors.brandPrimary : colors.surfaceTertiary },
                  ]}
                >
                  {done ? (
                    <Ionicons name="checkmark" size={14} color={colors.onBrandPrimary} />
                  ) : (
                    <Text style={{ color: active ? colors.onBrandPrimary : colors.muted, fontWeight: "700", fontSize: 12 }}>
                      {i + 1}
                    </Text>
                  )}
                </View>
                <Text style={{ color: active ? colors.onSurface : colors.muted, fontSize: 10, marginTop: 4, fontWeight: "600" }}>
                  {s === "fields" ? (language === "gu" ? "વિગતો" : "Details") : s === "preview" ? (language === "gu" ? "પ્રીવ્યૂ" : "Preview") : (language === "gu" ? "ડાઉનલોડ" : "Download")}
                </Text>
              </View>
            );
          })}
        </View>

        {step === "fields" && (
          <KeyboardAwareScrollView
            contentContainerStyle={isDesktop ? { alignItems: "center", padding: Spacing.xl, paddingBottom: 140 } : { padding: Spacing.lg, paddingBottom: 120 }}
            keyboardShouldPersistTaps="handled"
          >
            <View style={isDesktop ? { maxWidth: 1100, width: "100%", flexDirection: "row", gap: Spacing.xxl, alignItems: "flex-start" } : undefined}>
            <View style={isDesktop ? { flex: 1, minWidth: 0 } : undefined}>

            {/* Case Mode: Auto-filled from case — read-only, inherited, never re-entered */}
            {caseId && inheritedRows.length > 0 && (
              <View style={[styles.autofill, { backgroundColor: colors.brandTertiary, borderColor: colors.brandPrimary + "40", marginBottom: Spacing.lg }]}>
                <View style={{ flexDirection: "row", alignItems: "center", marginBottom: Spacing.xs }}>
                  <Ionicons name="sparkles" size={16} color={colors.onBrandTertiary} />
                  <Text style={{ color: colors.onBrandTertiary, fontWeight: "800", fontSize: 12, marginLeft: 6, letterSpacing: 0.5 }}>
                    AUTO-FILLED FROM CASE
                  </Text>
                </View>
                <Text style={{ color: colors.onBrandTertiary, opacity: 0.8, fontSize: 11, marginBottom: Spacing.sm }}>
                  {language === "gu" ? "કેસમાંથી મેળવેલ વિગતો — ફરીથી ભરવાની જરૂર નથી." : "Taken from the linked case — locked, no need to enter again."}
                </Text>
                {inheritedRows.map((r) => (
                  <View
                    key={r.key}
                    style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 3 }}
                  >
                    <Text style={{ color: colors.onBrandTertiary, opacity: 0.85, fontSize: 12 }}>{r.label}</Text>
                    <Text
                      style={{ color: colors.onBrandTertiary, fontWeight: "700", fontSize: 12, flexShrink: 1, marginLeft: Spacing.md, textAlign: "right" }}
                      numberOfLines={2}
                    >
                      {r.value}
                    </Text>
                  </View>
                ))}
              </View>
            )}

            {/* No-Case Mode: Render dynamic Base / Header Fields */}
            {!caseId && (
              <View style={{ marginBottom: Spacing.lg }}>
                <Text style={[styles.lbl, { color: colors.onSurface, marginBottom: Spacing.xs }]}>
                  {language === "gu" ? "કેસ અને કોર્ટ વિગત" : "Case & Court Details"}
                </Text>
                <Text style={{ color: colors.muted, fontSize: 12, marginBottom: Spacing.md }}>
                  {language === "gu" ? "આ અરજી માટે જરૂરી મુખ્ય વિગતો" : "Basic court & party details required for this application"}
                </Text>

                <Dropdown
                  testID="field-district"
                  label={(language === "gu" ? "જિલ્લો" : "District") + " *"}
                  placeholder={language === "gu" ? "જિલ્લો પસંદ કરો" : "Select district"}
                  value={values.district || null}
                  options={districts.map((d: any) => ({
                    id: d.id,
                    label: language === "gu" ? `${d.gu} (${d.en})` : `${d.en} (${d.gu})`,
                  }))}
                  onChange={(v) => {
                    update("district", v);
                    update("taluka", "");
                  }}
                />

                <Dropdown
                  testID="field-taluka"
                  label={language === "gu" ? "તાલુકો (વૈકલ્પિક)" : "Taluka (Optional)"}
                  placeholder={language === "gu" ? "તાલુકો પસંદ કરો" : "Select taluka"}
                  value={values.taluka || null}
                  options={talukas.map((t: any) => ({
                    id: t.id,
                    label: language === "gu" ? `${t.gu} (${t.en})` : `${t.en} (${t.gu})`,
                  }))}
                  onChange={(v) => update("taluka", v)}
                />

                {(() => {
                  const isOther = values.court === "other" || values.court_name === "other" || values.court_source === "custom";
                  return (
                    <View>
                      <Dropdown
                        testID="field-court"
                        label={(language === "gu" ? "કોર્ટનું નામ" : "Court Name") + " *"}
                        placeholder={language === "gu" ? "કોર્ટ પસંદ કરો" : "Select court"}
                        value={isOther ? "other" : (values.court || values.court_name || null)}
                        emptyMessage={language === "gu" ? "કોઈ કોર્ટ ઉપલબ્ધ નથી. કૃપા કરીને એડમિનિસ્ટ્રેટરનો સંપર્ક કરો." : "No courts available. Please contact administrator."}
                        options={[
                          ...courts.map((c: any) => ({
                            id: c.id,
                            label: language === "gu" ? `${c.gu} (${c.en})` : `${c.en} (${c.gu})`,
                          })),
                          { id: "other", label: "Other / અન્ય કોર્ટ" },
                        ]}
                        onChange={(v) => {
                          if (v === "other") {
                            update("court", "other");
                            update("court_name", "other");
                            update("court_source", "custom");
                          } else {
                            update("court", v);
                            update("court_name", v);
                            update("court_source", "catalog");
                            update("custom_court_name_gu", "");
                            update("custom_court_name_en", "");
                          }
                        }}
                      />
                      {isOther && (
                        <View style={{ gap: Spacing.sm, marginTop: Spacing.xs, marginBottom: Spacing.md }}>
                          <Field
                            testID="field-custom_court_name_gu"
                            label={(language === "gu" ? "કોર્ટનું નામ (ગુજરાતીમાં)" : "Gujarati Court Name") + " *"}
                            placeholder="દા.ત. મહે. પ્રિન્સિપાલ સિવિલ જજ સાહેબશ્રીની કોર્ટ"
                            value={values.custom_court_name_gu || ""}
                            onChangeText={(v) => update("custom_court_name_gu", v)}
                          />
                          <Field
                            testID="field-custom_court_name_en"
                            label={(language === "gu" ? "કોર્ટનું નામ (અંગ્રેજીમાં)" : "English Court Name") + " *"}
                            placeholder="e.g. In the Court of Ld. Principal Civil Judge"
                            value={values.custom_court_name_en || ""}
                            onChangeText={(v) => update("custom_court_name_en", v)}
                          />
                        </View>
                      )}
                    </View>
                  );
                })()}

                <Dropdown
                  testID="field-case_type"
                  label={(language === "gu" ? "કેસનો પ્રકાર" : "Case Type") + " *"}
                  placeholder={language === "gu" ? "કેસનો પ્રકાર પસંદ કરો" : "Select case type"}
                  value={values.case_type || null}
                  options={caseTypes.map((ct: any) => ({
                    id: ct.id,
                    label: language === "gu" ? `${ct.gu} (${ct.en})` : `${ct.en} (${ct.gu})`,
                  }))}
                  onChange={(v) => update("case_type", v)}
                />

                <Field
                  testID="field-case_number"
                  label={(language === "gu" ? "કેસ નંબર" : "Case Number") + (templateId === "jamin_bond" ? "" : " *")}
                  placeholder={
                    templateId === "jamin_bond"
                      ? (language === "gu" ? "દા.ત. ૧૨૩૪/૨૦૨૬ અથવા ગુન્હા રજી. નં." : "e.g. 1234/2026 or Crime Reg. No.")
                      : (language === "gu" ? "દા.ત. ૧૨૩૪/૨૦૨૬" : "e.g. 1234/2026")
                  }
                  value={values.case_number || ""}
                  onChangeText={(v) => update("case_number", v)}
                />

                <RoleChips
                  label={language === "gu" ? "પક્ષકાર-૧ની ભૂમિકા" : "Party 1 Role"}
                  options={PARTY_1_ROLES.map((r) => ({
                    value: r.value,
                    label: language === "gu" ? r.label_gu : r.label_en,
                  }))}
                  value={values.party_role || values.party_1_role || "complainant"}
                  onChange={(v) => {
                    update("party_role", v);
                    update("party_1_role", v);
                  }}
                />

                <Field
                  testID="field-party_name"
                  label={(language === "gu" ? "પક્ષકાર - ૧ નું નામ" : "Party 1 Name") + " *"}
                  placeholder={language === "gu" ? "પક્ષકાર-૧નું પૂરું નામ" : "Full Name of Party 1"}
                  value={values.party_name || values.party_1_name || ""}
                  onChangeText={(v) => {
                    update("party_name", v);
                    update("party_1_name", v);
                  }}
                />

                <RoleChips
                  label={language === "gu" ? "પક્ષકાર-૨ની ભૂમિકા" : "Party 2 Role"}
                  options={PARTY_2_ROLES.map((r) => ({
                    value: r.value,
                    label: language === "gu" ? r.label_gu : r.label_en,
                  }))}
                  value={values.opposite_party_role || values.party_2_role || "accused"}
                  onChange={(v) => {
                    update("opposite_party_role", v);
                    update("party_2_role", v);
                  }}
                />

                <Field
                  testID="field-opposite_party"
                  label={(language === "gu" ? "પક્ષકાર - ૨ નું નામ" : "Party 2 Name") + " *"}
                  placeholder={language === "gu" ? "પક્ષકાર-૨નું પૂરું નામ" : "Full Name of Party 2"}
                  value={values.opposite_party || values.party_2_name || ""}
                  onChangeText={(v) => {
                    update("opposite_party", v);
                    update("party_2_name", v);
                  }}
                />

                {templateId !== "closing_argument_right_application" && (
                  <Field
                    testID="field-advocate_name"
                    label={(language === "gu" ? "એડવોકેટનું નામ" : "Advocate Name") + " *"}
                    placeholder={language === "gu" ? "દા.ત. એડવોકેટ રોનક સોલંકી" : "e.g. Adv. Ronak Solanki"}
                    value={values.advocate_name || ""}
                    onChangeText={(v) => update("advocate_name", v)}
                  />
                )}
              </View>
            )}

            {/* Application-Specific Fields */}
            <Text style={[styles.lbl, { color: colors.onSurface, marginTop: Spacing.md }]}>
              {language === "gu" ? "અરજીની વિગત" : "Application Details"}
            </Text>
            <Text style={{ color: colors.muted, fontSize: 12, marginBottom: Spacing.md, marginTop: 4 }}>
              {language === "gu" ? "આ અરજી માટે જરૂરી ચોક્કસ વિગતો" : "Only the fields required specifically for this application."}
            </Text>

            {hasRepresentingParty && (
              <RoleChips
                label={(language === "gu" ? "કોના તરફે એડવોકેટ *" : "Advocate For *")}
                options={representingPartyOptions}
                value={
                  values.representing_party === "party_2" || values.representing_party === "opposite"
                    ? "party_2"
                    : "party_1"
                }
                onChange={(v) => {
                  update("representing_party", v);
                  update("advocate_side", v === "party_2" ? "opposite" : "party");
                }}
              />
            )}

            {appSpecificFields.map((f: any) => renderFieldInput(f))}

            {/* Date Field — ALWAYS THE LAST FIELD (except closing_argument_right_application where date is in template sequence) */}
            {templateId !== "closing_argument_right_application" && (
              <View style={{ marginTop: Spacing.sm }}>
                {renderFieldInput(dateField)}
              </View>
            )}

            </View>

            {/* Desktop summary panel */}
            {isDesktop ? (
              <View style={{ width: 340, flexShrink: 0 }}>
                <View style={[styles.dSummary, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                  <Text style={[styles.lbl, { color: colors.brandPrimary, letterSpacing: 1, fontSize: 11 }]}>
                    DOCUMENT SUMMARY
                  </Text>
                  <Text style={{ color: colors.onSurface, fontWeight: "800", fontSize: 16, fontFamily: "serif", marginTop: Spacing.sm }}>
                    {language === "gu" ? template?.name_gu || template?.name_en : template?.name_en || template?.name_gu}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }} numberOfLines={1}>
                    {language === "gu" ? template?.name_en || template?.name_gu : template?.name_gu || template?.name_en}
                  </Text>

                  <View style={[styles.dSummaryRow, { borderTopColor: colors.divider }]}>
                    <Ionicons name="wallet-outline" size={16} color={colors.brandPrimary} />
                    <Text style={styles.dSummaryLabel}>Cost</Text>
                    <Text style={styles.dSummaryValue}>{isUnlimited ? (language === "gu" ? "મફત / અમર્યાદિત" : "Free / Unlimited") : "1 template credit"}</Text>
                  </View>

                  {caseData ? (
                    <View style={[styles.dSummaryRow, { borderTopColor: colors.divider }]}>
                      <Ionicons name="link-outline" size={16} color={colors.brandPrimary} />
                      <Text style={styles.dSummaryLabel}>Case</Text>
                      <Text style={styles.dSummaryValue} numberOfLines={1}>
                        {caseData.case_number || caseData.nickname || "Linked case"}
                      </Text>
                    </View>
                  ) : null}

                  {inheritedRows.length > 0 ? (
                    <View style={[styles.dSummaryRow, { borderTopColor: colors.divider }]}>
                      <Ionicons name="sparkles-outline" size={16} color={colors.success} />
                      <Text style={styles.dSummaryLabel}>Auto-filled</Text>
                      <Text style={[styles.dSummaryValue, { color: colors.success }]}>
                        {inheritedRows.length} field{inheritedRows.length > 1 ? "s" : ""} from case
                      </Text>
                    </View>
                  ) : null}

                  <View style={[styles.dSummaryRow, { borderTopColor: colors.divider }]}>
                    <Ionicons
                      name={missingRequired.length > 0 ? "alert-circle-outline" : "checkmark-circle-outline"}
                      size={16}
                      color={missingRequired.length > 0 ? colors.warning : colors.success}
                    />
                    <Text style={styles.dSummaryLabel}>Required fields</Text>
                    <Text style={[styles.dSummaryValue, { color: missingRequired.length > 0 ? colors.warning : colors.success }]}>
                      {missingRequired.length > 0 ? `${missingRequired.length} remaining` : "All complete"}
                    </Text>
                  </View>

                  <Text style={{ color: colors.muted, fontSize: 11, marginTop: Spacing.md, lineHeight: 16 }}>
                    Preview button is at the bottom. Drafts autosave every change — nothing is lost if you leave.
                  </Text>
                </View>
              </View>
            ) : null}
            </View>
          </KeyboardAwareScrollView>
        )}

        {step === "preview" && (
          <ScrollView contentContainerStyle={isDesktop ? { alignItems: "center", padding: Spacing.xl, paddingBottom: 140 } : { padding: Spacing.lg, paddingBottom: 120 }}>
            <View
              style={[
                styles.doc,
                isDesktop && styles.docDesktop,
                { backgroundColor: "#FFFFFF", borderColor: colors.border },
              ]}
              testID="preview-doc"
            >
              {blocks.map((b, i) => {
                if (b.section === "table" && Array.isArray(b.rows) && b.rows.length > 0) {
                  const metaCols = b.meta?.cols || [];
                  const totalColWidth = metaCols.reduce((acc: number, val: number) => acc + val, 0) || 100;
                  const defaultAligns = b.meta?.align || [];

                  return (
                    <View
                      key={i}
                      testID={`preview-table-${i}`}
                      style={[
                        styles.previewTable,
                        { borderColor: "#000000" },
                      ]}
                    >
                      {b.rows.map((row: string[], rIdx: number) => {
                        const rMeta = b.row_meta?.[rIdx] || {};
                        const isHeader = !!rMeta.is_header;
                        const isSpan = (row.length === 1 && metaCols.length > 1);

                        return (
                          <View
                            key={rIdx}
                            style={[
                              styles.previewTableRow,
                              isHeader && { backgroundColor: "#F3F4F6" },
                            ]}
                          >
                            {row.map((cellText: string, cIdx: number) => {
                              const cellAlign = (rMeta.align?.[cIdx] || (isHeader ? "center" : defaultAligns[cIdx]) || (isSpan ? (defaultAligns[0] || "right") : "left")) as ("left" | "right" | "center");
                              const cellBold = isHeader || !!rMeta.bold?.[cIdx];

                              let colWidthPercent = "100%";
                              if (!isSpan && metaCols.length > cIdx) {
                                colWidthPercent = `${(metaCols[cIdx] / totalColWidth) * 100}%`;
                              } else if (!isSpan && metaCols.length === 0 && row.length > 0) {
                                colWidthPercent = `${100 / row.length}%`;
                              }

                              return (
                                <View
                                  key={cIdx}
                                  testID={`preview-table-cell-${rIdx}-${cIdx}`}
                                  style={[
                                    styles.previewTableCell,
                                    {
                                      width: colWidthPercent as any,
                                      borderColor: "#000000",
                                      alignItems: cellAlign === "right" ? "flex-end" : cellAlign === "center" ? "center" : "flex-start",
                                      justifyContent: "center",
                                    },
                                  ]}
                                >
                                  <Text
                                    selectable
                                    style={[
                                      styles.docText,
                                      {
                                        textAlign: cellAlign,
                                        fontWeight: cellBold ? "700" : "400",
                                        fontSize: 13,
                                        color: "#111111",
                                        lineHeight: 20,
                                      },
                                    ]}
                                  >
                                    {cellText || " "}
                                  </Text>
                                </View>
                              );
                            })}
                          </View>
                        );
                      })}
                    </View>
                  );
                }

                if (b.section === "page_break") {
                  return (
                    <View
                      key={i}
                      style={{
                        borderBottomWidth: 1,
                        borderBottomColor: "#D1D5DB",
                        borderStyle: "dashed",
                        marginVertical: 14,
                      }}
                    />
                  );
                }

                return (
                  <Text
                    key={i}
                    selectable
                    style={[
                      styles.docText,
                      {
                        textAlign: b.align === "center" ? "center" : b.align === "right" ? "right" : "left",
                        fontWeight: b.bold ? "700" : "400",
                        fontSize: b.bold ? 15 : 13,
                        textDecorationLine: (b.underline || b.section === "title") ? "underline" : "none",
                        marginBottom: b.text ? 6 : 10,
                      },
                    ]}
                  >
                    {b.text || " "}
                  </Text>
                );
              })}
            </View>
            <Pressable
              testID="edit-btn"
              onPress={() => setStep("fields")}
              style={[
                styles.editRow,
                isDesktop && { maxWidth: 780, width: "100%" },
                { borderColor: colors.brandPrimary },
              ]}
            >
              <Ionicons name="create-outline" size={18} color={colors.brandPrimary} />
              <Text style={{ color: colors.brandPrimary, fontWeight: "700", marginLeft: 8 }}>
                {language === "gu" ? "વિગતો સુધારો" : "Edit Details"}
              </Text>
            </Pressable>
          </ScrollView>
        )}

        {step === "output" && (
          <ScrollView
            contentContainerStyle={isDesktop ? { alignItems: "center", padding: Spacing.xl, paddingBottom: 140 } : { padding: Spacing.lg, paddingBottom: 120 }}
            keyboardShouldPersistTaps="handled"
          >
          <View style={isDesktop ? { maxWidth: 780, width: "100%" } : undefined}>
            {notice && (
              <View
                testID="download-notice"
                style={[
                  styles.notice,
                  {
                    backgroundColor: notice.tone === "ok" ? colors.brandTertiary : "#FDE8E8",
                    borderColor: notice.tone === "ok" ? colors.brandPrimary + "55" : "#B3261E",
                  },
                ]}
              >
                <Ionicons
                  name={notice.tone === "ok" ? "checkmark-circle" : "alert-circle"}
                  size={18}
                  color={notice.tone === "ok" ? colors.brandPrimary : "#B3261E"}
                />
                <Text style={{ color: notice.tone === "ok" ? colors.onBrandTertiary : "#7A1C1C", fontSize: 13, flex: 1, marginLeft: 8 }}>
                  {notice.text}
                </Text>
              </View>
            )}
            <Text style={[styles.lbl, { color: colors.onSurface }]}>
              {language === "gu" ? "ફાઇલનું નામ" : "Rename File"}
            </Text>
            <View style={{ height: Spacing.sm }} />
            <Field testID="filename-input" value={filename} onChangeText={setFilename} placeholder="File name" />

            <Text style={[styles.lbl, { color: colors.onSurface, marginTop: Spacing.md }]}>
              {language === "gu" ? "ફોર્મેટ પસંદ કરો" : "Select Format"}
            </Text>
            <View style={{ gap: Spacing.md, marginTop: Spacing.sm, flexDirection: isDesktop ? "row" : "column" }}>
              <Pressable
                testID="download-pdf"
                onPress={() => download("pdf")}
                disabled={busy}
                style={[styles.formatCard, isDesktop && { flex: 1 }, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
              >
                <View style={[styles.formatIcon, { backgroundColor: "#7A1C1C20" }]}>
                  <Ionicons name="document" size={22} color="#7A1C1C" />
                </View>
                <View style={{ flex: 1, marginLeft: Spacing.md }}>
                  <Text style={{ color: colors.onSurface, fontWeight: "700" }}>
                    {downloading === "pdf" ? (language === "gu" ? "PDF બને છે…" : "Generating PDF…") : "PDF Document"}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 12 }}>
                    {language === "gu" ? "પ્રિન્ટ અને ફાઇલિંગ માટે તૈયાર" : "Ready to print & file"}
                  </Text>
                </View>
                {downloading === "pdf" ? (
                  <ActivityIndicator size="small" color={colors.brandPrimary} />
                ) : (
                  <Ionicons name="download-outline" size={20} color={colors.brandPrimary} />
                )}
              </Pressable>
              <Pressable
                testID="download-docx"
                onPress={() => download("docx")}
                disabled={busy}
                style={[styles.formatCard, isDesktop && { flex: 1 }, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
              >
                <View style={[styles.formatIcon, { backgroundColor: "#1D2D5020" }]}>
                  <Ionicons name="document-text" size={22} color="#1D2D50" />
                </View>
                <View style={{ flex: 1, marginLeft: Spacing.md }}>
                  <Text style={{ color: colors.onSurface, fontWeight: "700" }}>
                    {downloading === "docx" ? (language === "gu" ? "Word ફાઇલ બને છે…" : "Generating Word…") : "Word Document"}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 12 }}>
                    {language === "gu" ? "સુધારી શકાય તેવું .docx ફોર્મેટ" : "Editable .docx format"}
                  </Text>
                </View>
                {downloading === "docx" ? (
                  <ActivityIndicator size="small" color={colors.brandPrimary} />
                ) : (
                  <Ionicons name="download-outline" size={20} color={colors.brandPrimary} />
                )}
              </Pressable>
              <Pressable
                testID="download-odt"
                onPress={() => download("odt")}
                disabled={busy}
                style={[styles.formatCard, isDesktop && { flex: 1 }, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
              >
                <View style={[styles.formatIcon, { backgroundColor: "#0B6E4F20" }]}>
                  <Ionicons name="document-outline" size={22} color="#0B6E4F" />
                </View>
                <View style={{ flex: 1, marginLeft: Spacing.md }}>
                  <Text style={{ color: colors.onSurface, fontWeight: "700" }}>
                    {downloading === "odt" ? (language === "gu" ? "Writer ફાઇલ બને છે…" : "Generating Writer…") : "Writer Document"}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 12 }}>LibreOffice .odt format</Text>
                </View>
                {downloading === "odt" ? (
                  <ActivityIndicator size="small" color={colors.brandPrimary} />
                ) : (
                  <Ionicons name="download-outline" size={20} color={colors.brandPrimary} />
                )}
              </Pressable>
              <Pressable
                testID="download-png"
                onPress={() => download("png")}
                disabled={busy}
                style={[styles.formatCard, isDesktop && { flex: 1 }, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
              >
                <View style={[styles.formatIcon, { backgroundColor: "#8A5A0020" }]}>
                  <Ionicons name="image-outline" size={22} color="#8A5A00" />
                </View>
                <View style={{ flex: 1, marginLeft: Spacing.md }}>
                  <Text style={{ color: colors.onSurface, fontWeight: "700" }}>
                    {downloading === "png" ? (language === "gu" ? "Image બને છે…" : "Generating Image…") : "Image Document"}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 12 }}>
                    {language === "gu" ? "PNG ઇમેજ પેજીસ" : "PNG pages — share when PDF unavailable"}
                  </Text>
                </View>
                {downloading === "png" ? (
                  <ActivityIndicator size="small" color={colors.brandPrimary} />
                ) : (
                  <Ionicons name="download-outline" size={20} color={colors.brandPrimary} />
                )}
              </Pressable>
            </View>

            <Text style={{ color: colors.muted, fontSize: 12, marginTop: Spacing.sm }}>
              PDF — print &amp; file · Word — edit · Writer (ODT) — LibreOffice · Image — PNG pages
            </Text>

            <View style={[styles.note, { backgroundColor: colors.surfaceSecondary }]}>
              <Ionicons name="information-circle-outline" size={16} color={colors.muted} />
              <Text style={{ color: colors.muted, fontSize: 11, flex: 1, marginLeft: 6 }}>
                {isUnlimited
                  ? (language === "gu"
                      ? "ઓનર/પાર્ટનર અમર્યાદિત ઍક્સેસ સક્રિય છે. કોઈ ક્રેડિટ કપાશે નહીં."
                      : "Owner/Partner Unlimited Access active. No credits consumed.")
                  : (language === "gu"
                      ? "દસ્તાવેજ બનાવવાથી ૧ ક્રેડિટ વપરાશે. કોર્ટમાં રજૂ કરતા પહેલાં અરજીની ચકાસણી કરવી."
                      : "Generating consumes 1 template credit. Review your document — you remain responsible for its accuracy before filing.")}
              </Text>
            </View>
            {busy && <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: Spacing.lg }} />}
          </View>
          </ScrollView>
        )}

        {/* Footer CTA */}
        {step === "fields" && (
          <View style={[styles.footer, { backgroundColor: colors.surface, borderTopColor: colors.border }]}>
            <View style={isDesktop ? { maxWidth: 780, width: "100%", alignSelf: "center" } : undefined}>
              <Button
                testID="continue-preview-btn"
                title={language === "gu" ? "અરજીનું પ્રીવ્યૂ જુઓ" : "Preview Document"}
                loading={busy}
                onPress={genPreview}
              />
            </View>
          </View>
        )}
        {step === "preview" && (
          <View style={[styles.footer, { backgroundColor: colors.surface, borderTopColor: colors.border }]}>
            <View style={isDesktop ? { maxWidth: 780, width: "100%", alignSelf: "center" } : undefined}>
              <Button
                testID="to-output-btn"
                title={language === "gu" ? "ખાતરી કરો અને ડાઉનલોડ કરો" : "Confirm & Download"}
                onPress={() => setStep("output")}
              />
            </View>
          </View>
        )}
      </KeyboardAvoidingView>
      <PlanPurchaseModal
        visible={showPurchaseModal}
        currentBalance={walletBalance}
        onClose={() => setShowPurchaseModal(false)}
        onSuccess={(newBal) => {
          setWalletBalance(newBal);
          setNotice({ tone: "ok", text: `Credits added successfully. Available balance: ${newBal} templates.` });
        }}
      />
      <LanguageSelectModal
        visible={showLanguageModal}
        onClose={() => setShowLanguageModal(false)}
        templateNameGu={template?.name_gu}
        templateNameEn={template?.name_en}
        category={template?.category}
        onSelect={(lang) => {
          setLanguage(lang);
          setShowLanguageModal(false);
        }}
      />
    </SafeAreaView>
    </ErrorBoundary>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, borderBottomWidth: StyleSheet.hairlineWidth,
  },
  h1: { fontSize: 16, fontWeight: "700", fontFamily: "serif", flex: 1, textAlign: "center", marginHorizontal: 8 },
  steps: { flexDirection: "row", paddingHorizontal: Spacing.xl, paddingVertical: Spacing.md },
  stepDot: { width: 26, height: 26, borderRadius: 13, alignItems: "center", justifyContent: "center" },
  lbl: { fontSize: 14, fontWeight: "800", letterSpacing: 0.3 },
  fieldLbl: { fontSize: 13, fontWeight: "600", marginBottom: Spacing.xs },
  langChip: { flex: 1, height: 46, borderRadius: Radius.md, borderWidth: 1.5, alignItems: "center", justifyContent: "center" },
  autofill: { padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1 },
  autoChip: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8 },
  doc: { padding: Spacing.lg, borderRadius: Radius.md, borderWidth: 1 },
  docText: { color: "#111", fontSize: 13, lineHeight: 22 },
  editRow: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    marginTop: Spacing.md, paddingVertical: Spacing.md, borderRadius: Radius.md, borderWidth: 1.5,
  },
  formatCard: { flexDirection: "row", alignItems: "center", padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1 },
  formatIcon: { width: 42, height: 42, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  notice: { flexDirection: "row", alignItems: "flex-start", padding: Spacing.md, borderRadius: Radius.md, marginBottom: Spacing.lg, borderWidth: 1 },
  note: { flexDirection: "row", alignItems: "flex-start", padding: Spacing.md, borderRadius: Radius.md, marginTop: Spacing.lg },
  footer: { position: "absolute", bottom: 0, left: 0, right: 0, padding: Spacing.lg, borderTopWidth: StyleSheet.hairlineWidth },
  docDesktop: {
    maxWidth: 780,
    width: "100%",
    minHeight: 1000,
    padding: Spacing.xxxl,
    borderRadius: 4,
    shadowColor: "#000",
    shadowOpacity: 0.12,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  },
  dSummary: { padding: Spacing.lg, borderRadius: 14, borderWidth: 1 },
  dSummaryRow: {
    flexDirection: "row", alignItems: "center",
    paddingTop: Spacing.md, marginTop: Spacing.md, borderTopWidth: StyleSheet.hairlineWidth, gap: 8,
  },
  dSummaryLabel: { color: "#6B7280", fontSize: 12, fontWeight: "600", flex: 1 },
  dSummaryValue: { color: "#0B1B3D", fontSize: 13, fontWeight: "700", maxWidth: "60%" },
  previewTable: {
    borderTopWidth: 1,
    borderLeftWidth: 1,
    marginVertical: 10,
    width: "100%",
  },
  previewTableRow: {
    flexDirection: "row",
    width: "100%",
  },
  previewTableCell: {
    borderRightWidth: 1,
    borderBottomWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 6,
  },
});

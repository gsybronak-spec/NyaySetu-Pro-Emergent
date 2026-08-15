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
import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { Dropdown } from "@/src/components/Dropdown";
import { DateField } from "@/src/components/DateField";
import { formatDateDisplay, isISODate } from "@/src/utils/date";
import { formatAdvocateName } from "@/src/utils/advocate";
import { saveDocument } from "@/src/utils/download";
import { useTheme } from "@/src/theme/ThemeContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";

type Step = "fields" | "preview" | "output";

const BASE_FIELD_KEYS = new Set([
  "district",
  "taluka",
  "court",
  "case_type",
  "case_number",
  "party_name",
  "party_role",
  "opposite_party",
  "opposite_party_role",
  "advocate_name",
]);

const PARTY_1_ROLES = [
  { value: "plaintiff", label_en: "Plaintiff", label_gu: "વાદી" },
  { value: "applicant", label_en: "Applicant", label_gu: "અરજદાર" },
  { value: "complainant", label_en: "Complainant", label_gu: "ફરિયાદી" },
];

const PARTY_2_ROLES = [
  { value: "defendant", label_en: "Defendant", label_gu: "પ્રતિવાદી" },
  { value: "opponent", label_en: "Opponent / Respondent", label_gu: "સામાવાળા" },
  { value: "accused", label_en: "Accused", label_gu: "આરોપી" },
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
  const { isDesktop } = useResponsive();
  const params = useLocalSearchParams<{ id: string; case_id?: string; lang?: string; draft?: string }>();
  const templateId = String(params.id);
  const caseId = params.case_id && params.case_id !== "" ? String(params.case_id) : undefined;

  const [template, setTemplate] = useState<any>(null);
  const [caseData, setCaseData] = useState<any>(null);
  const [language, setLanguage] = useState<"en" | "gu">((params.lang as any) || "en");
  const [values, setValues] = useState<Record<string, any>>({});
  const [step, setStep] = useState<Step>("fields");
  const [preview, setPreview] = useState("");
  const [blocks, setBlocks] = useState<{ text: string; align: string; bold: boolean }[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [downloading, setDownloading] = useState<"pdf" | "docx" | "odt" | "png" | null>(null);
  const [filename, setFilename] = useState("");
  const [notice, setNotice] = useState<{ tone: "ok" | "err"; text: string } | null>(null);

  // Catalog datasets for No-Case mode
  const [districts, setDistricts] = useState<any[]>([]);
  const [talukas, setTalukas] = useState<any[]>([]);
  const [courts, setCourts] = useState<any[]>([]);
  const [caseTypes, setCaseTypes] = useState<any[]>([]);
  const [userProfile, setUserProfile] = useState<any>(null);

  const draftTimer = useRef<any>(null);

  useEffect(() => {
    (async () => {
      try {
        const [t, me, dists, cts] = await Promise.all([
          api.template(templateId),
          api.me().catch(() => null),
          api.districts().catch(() => []),
          api.caseTypes().catch(() => []),
        ]);
        setTemplate(t);
        setUserProfile(me);
        setDistricts(Array.isArray(dists) ? dists : []);
        setCaseTypes(Array.isArray(cts) ? cts : []);
        setFilename(`${t.name_en.replace(/\s+/g, "_")}_${Date.now().toString().slice(-5)}`);

        const initialValues: Record<string, any> = {};

        if (caseId) {
          const c = await api.getCase(caseId);
          setCaseData(c);
          if (c.language) setLanguage(c.language);
          if (c.party_name) initialValues["party_name"] = c.party_name;
          if (c.client_name || c.party_name) initialValues["client_name"] = c.client_name || c.party_name;
          if (c.opposite_party) initialValues["opposite_party"] = c.opposite_party;
          if (c.case_number) initialValues["case_number"] = c.case_number;
          if (c.district_id) initialValues["district"] = c.district_id;
          if (c.taluka_id) initialValues["taluka"] = c.taluka_id;
          if (c.court_id) initialValues["court"] = c.court_id;
          if (c.case_type_id) initialValues["case_type"] = c.case_type_id;
          if (c.police_station_label) initialValues["police_station"] = c.police_station_label;
          if (c.client_mobile) initialValues["client_mobile"] = c.client_mobile;
          if (c.client_email) initialValues["client_email"] = c.client_email;
          if (c.client_address) initialValues["client_address"] = c.client_address;
          if (c.law_label) initialValues["law"] = c.law_label;
          if (c.section_label) initialValues["section"] = c.section_label;
          initialValues["party_role"] = NORMALIZE_ROLE_MAP[c.party_role || ""] || "plaintiff";
          initialValues["opposite_party_role"] = NORMALIZE_ROLE_MAP[c.opposite_party_role || ""] || "defendant";

          if (c.custom_fields) {
            for (const [k, v] of Object.entries(c.custom_fields)) {
              if (v !== null && v !== undefined && v !== "") initialValues[k] = v;
            }
          }
        } else {
          // No-case default party roles
          initialValues["party_role"] = "plaintiff";
          initialValues["opposite_party_role"] = "defendant";
          if (me?.district) initialValues["district"] = me.district;
          if (me?.court) initialValues["court"] = me.court;
        }

        // Advocate name from profile (language-aware default)
        const advName = formatAdvocateName(
          (language === "gu" ? me?.advocate_name_gu : me?.advocate_name_en) || me?.name,
          language
        );
        initialValues["advocate_name"] = advName;
        initialValues["today"] = new Date().toLocaleDateString("en-GB").replace(/\//g, "-");

        // Date fields default to today when unset (always editable)
        for (const f of t.fields || []) {
          if (f.type === "date" && !initialValues[f.key]) initialValues[f.key] = new Date().toISOString().slice(0, 10);
        }
        if (!initialValues["date"]) initialValues["date"] = new Date().toISOString().slice(0, 10);

        setValues((prev) => ({ ...initialValues, ...prev }));

        if (params.draft === "1") {
          const drafts = await api.drafts();
          const d = drafts.find((x: any) => x.template_id === templateId && (x.case_id || undefined) === caseId);
          if (d) {
            setValues((prev) => ({ ...prev, ...(d.values || {}) }));
            setLanguage(d.language || "en");
          }
        }
      } catch (e: any) {
        Alert.alert("Error", e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [templateId, caseId]);

  // Load talukas & courts when district changes in No-Case mode
  useEffect(() => {
    if (values.district) {
      api.talukas(values.district).then((t) => setTalukas(Array.isArray(t) ? t : [])).catch(() => setTalukas([]));
      api.courts(values.district).then((c) => setCourts(Array.isArray(c) ? c : [])).catch(() => setCourts([]));
    } else {
      setTalukas([]);
      setCourts([]);
    }
  }, [values.district]);

  // Autosave draft when values change
  useEffect(() => {
    if (loading || Object.keys(values).length === 0) return;
    if (draftTimer.current) clearTimeout(draftTimer.current);
    draftTimer.current = setTimeout(() => {
      api.saveDraft({ template_id: templateId, case_id: caseId, language, values }).catch(() => {});
    }, 1200);
    return () => draftTimer.current && clearTimeout(draftTimer.current);
  }, [values, language, loading]);

  const update = (k: string, v: any) => setValues((prev) => ({ ...prev, [k]: v }));

  // When language switches, update advocate name default if untouched
  const handleLanguageChange = (newLang: "en" | "gu") => {
    setLanguage(newLang);
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
  ];

  const inheritedRows = useMemo(() => {
    if (!caseData) return [];
    const pRoleLabel = language === "gu"
      ? (PARTY_1_ROLES.find((r) => r.value === values.party_role)?.label_gu || caseData.party_role)
      : (PARTY_1_ROLES.find((r) => r.value === values.party_role)?.label_en || caseData.party_role);
    const oppRoleLabel = language === "gu"
      ? (PARTY_2_ROLES.find((r) => r.value === values.opposite_party_role)?.label_gu || caseData.opposite_party_role)
      : (PARTY_2_ROLES.find((r) => r.value === values.opposite_party_role)?.label_en || caseData.opposite_party_role);

    const src: Record<string, string | undefined> = {
      case_number: caseData.case_number,
      party_name: caseData.party_name,
      opposite_party: caseData.opposite_party,
      court: caseData.court_label || caseData.court,
      district: caseData.district_label || caseData.district_id,
      taluka: caseData.taluka_label,
      case_type: caseData.case_type_label,
      party_role: pRoleLabel,
      opposite_party_role: oppRoleLabel,
    };
    const rows: { key: string; label: string; value: string }[] = [];
    for (const [key, lEn, lGu] of CASE_OWNED_LABELS) {
      const v = src[key];
      if (v) rows.push({ key, label: language === "gu" ? lGu : lEn, value: String(v) });
    }
    return rows;
  }, [caseData, language, values.party_role, values.opposite_party_role]);

  // Separate template application fields into app-specific vs date field
  const templateFields = useMemo(() => template?.fields || [], [template]);

  const appSpecificFields = useMemo(() => {
    return templateFields.filter((f: any) => {
      if (caseId && BASE_FIELD_KEYS.has(f.key)) return false;
      if (f.key === "date") return false;
      return true;
    });
  }, [templateFields, caseId]);

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
    const missing: string[] = [];
    if (!caseId) {
      // Required base fields in No-Case mode
      if (!values.district) missing.push("district");
      if (!values.court) missing.push("court");
      if (!values.case_type) missing.push("case_type");
      if (!values.case_number && templateId !== "jamin_bond") missing.push("case_number");
      if (!values.party_name) missing.push("party_name");
      if (!values.opposite_party) missing.push("opposite_party");
      if (!values.advocate_name) missing.push("advocate_name");
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
  }, [caseId, values, appSpecificFields, templateId]);

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
      await saveDocument({ filename: res.filename, mime_type: res.mime_type, base64: res.base64 }, format);
      const okText = `${res.filename} generated successfully. 1 template credit consumed.`;
      setNotice({ tone: "ok", text: `Download started — ${res.filename}. 1 template credit consumed.` });
      Alert.alert(
        "Document Ready",
        okText,
        [{ text: "Done", onPress: () => (caseId ? router.replace({ pathname: "/case/[id]", params: { id: caseId } }) : router.replace("/(tabs)/home")) }]
      );
    } catch (e: any) {
      const msg = e?.message || "Unknown error";
      if (msg.toLowerCase().includes("insufficient") || msg.includes("402")) {
        setNotice({ tone: "err", text: "You have no templates remaining. Please purchase a plan." });
        Alert.alert("No Credits", "You have no templates remaining. Please purchase a plan.", [
          { text: "Cancel", style: "cancel" },
          { text: "View Plans", onPress: () => router.push("/(tabs)/subscription") },
        ]);
      } else if (msg.includes("429") || msg.toLowerCase().includes("too many")) {
        setNotice({ tone: "err", text: "Too many requests. Please wait a moment before trying again." });
        Alert.alert("Too Many Requests", "Please wait a moment before trying again.");
      } else if (msg.toLowerCase().includes("unable to download") || msg.toLowerCase().includes("invalid") || msg.toLowerCase().includes("empty")) {
        setNotice({ tone: "err", text: msg });
        Alert.alert("Unable to download the document", `${msg}`);
      } else if (format === "pdf") {
        setNotice({ tone: "err", text: "PDF generation failed. Your credit was refunded — try Download as Image." });
        Alert.alert("PDF generation failed", "Your credit has been refunded. Try downloading the same document as an image instead.", [
          { text: "Cancel", style: "cancel" },
          { text: "Download as Image", onPress: () => download("png") },
        ]);
        console.warn("[download] pdf generation failed", msg);
      } else {
        setNotice({ tone: "err", text: "Unable to download the document. Please try again. Failed generations are refunded automatically." });
        Alert.alert("Unable to download the document", "Please try again. Your credit has not been lost — failed generations are refunded automatically.");
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

    if (f.type === "select") {
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
        <ActivityIndicator color={colors.brandPrimary} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top", "bottom"]}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        {/* Header */}
        <View style={[styles.header, { borderBottomColor: colors.border }]}>
          <Pressable testID="tpl-back" onPress={() => (step === "fields" ? router.back() : setStep("fields"))} hitSlop={12}>
            <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
          </Pressable>
          <Text style={[styles.h1, { color: colors.onSurface }]} numberOfLines={1}>
            {language === "gu" ? template.name_gu : template.name_en}
          </Text>
          <View style={{ width: 24 }} />
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
          <ScrollView
            contentContainerStyle={isDesktop ? { alignItems: "center", padding: Spacing.xl, paddingBottom: 140 } : { padding: Spacing.lg, paddingBottom: 120 }}
            keyboardShouldPersistTaps="handled"
          >
            <View style={isDesktop ? { maxWidth: 1100, width: "100%", flexDirection: "row", gap: Spacing.xxl, alignItems: "flex-start" } : undefined}>
            <View style={isDesktop ? { flex: 1, minWidth: 0 } : undefined}>
            
            {/* Language toggle if no case */}
            {!caseId && (
              <>
                <Text style={[styles.lbl, { color: colors.onSurface }]}>
                  {language === "gu" ? "દસ્તાવેજની ભાષા" : "Document Language"}
                </Text>
                <View style={{ flexDirection: "row", gap: Spacing.sm, marginBottom: Spacing.lg, marginTop: Spacing.sm }}>
                  {[
                    { id: "en", label: "English" },
                    { id: "gu", label: "ગુજરાતી" },
                  ].map((l) => {
                    const active = language === l.id;
                    return (
                      <Pressable
                        key={l.id}
                        testID={`tpl-lang-${l.id}`}
                        onPress={() => handleLanguageChange(l.id as any)}
                        style={[styles.langChip, { backgroundColor: active ? colors.brandPrimary : colors.surfaceSecondary, borderColor: active ? colors.brandPrimary : colors.border }]}
                      >
                        <Text style={{ color: active ? colors.onBrandPrimary : colors.onSurface, fontWeight: "700" }}>{l.label}</Text>
                      </Pressable>
                    );
                  })}
                </View>
              </>
            )}

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

                <Dropdown
                  testID="field-court"
                  label={(language === "gu" ? "કોર્ટનું નામ" : "Court Name") + " *"}
                  placeholder={language === "gu" ? "કોર્ટ પસંદ કરો" : "Select court"}
                  value={values.court || null}
                  options={courts.map((c: any) => ({
                    id: c.id,
                    label: language === "gu" ? `${c.gu} (${c.en})` : `${c.en} (${c.gu})`,
                  }))}
                  onChange={(v) => update("court", v)}
                />

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
                  label={language === "gu" ? "પક્ષકાર ૧ ની ભૂમિકા" : "Party 1 Role"}
                  options={PARTY_1_ROLES.map((r) => ({
                    value: r.value,
                    label: language === "gu" ? r.label_gu : r.label_en,
                  }))}
                  value={values.party_role || "plaintiff"}
                  onChange={(v) => update("party_role", v)}
                />

                <Field
                  testID="field-party_name"
                  label={(language === "gu" ? "પક્ષકાર ૧ નું પૂરું નામ" : "Party 1 Full Name") + " *"}
                  placeholder={language === "gu" ? "પક્ષકાર ૧ નું પૂરું નામ" : "Full Name of Party 1"}
                  value={values.party_name || ""}
                  onChangeText={(v) => update("party_name", v)}
                />

                <RoleChips
                  label={language === "gu" ? "પક્ષકાર ૨ (સામાવાળા) ની ભૂમિકા" : "Party 2 (Opposite) Role"}
                  options={PARTY_2_ROLES.map((r) => ({
                    value: r.value,
                    label: language === "gu" ? r.label_gu : r.label_en,
                  }))}
                  value={values.opposite_party_role || "defendant"}
                  onChange={(v) => update("opposite_party_role", v)}
                />

                <Field
                  testID="field-opposite_party"
                  label={(language === "gu" ? "પક્ષકાર ૨ (સામાવાળા) નું નામ" : "Party 2 (Opposite) Name") + " *"}
                  placeholder={language === "gu" ? "સામાવાળા પક્ષકારનું પૂરું નામ" : "Full Name of Opposite Party"}
                  value={values.opposite_party || ""}
                  onChangeText={(v) => update("opposite_party", v)}
                />

                <Field
                  testID="field-advocate_name"
                  label={(language === "gu" ? "એડવોકેટનું નામ" : "Advocate Name") + " *"}
                  placeholder={language === "gu" ? "દા.ત. એડવોકેટ રોનક સોલંકી" : "e.g. Adv. Ronak Solanki"}
                  value={values.advocate_name || ""}
                  onChangeText={(v) => update("advocate_name", v)}
                />
              </View>
            )}

            {/* Application-Specific Fields */}
            <Text style={[styles.lbl, { color: colors.onSurface, marginTop: Spacing.md }]}>
              {language === "gu" ? "અરજીની વિગત" : "Application Details"}
            </Text>
            <Text style={{ color: colors.muted, fontSize: 12, marginBottom: Spacing.md, marginTop: 4 }}>
              {language === "gu" ? "આ અરજી માટે જરૂરી ચોક્કસ વિગતો" : "Only the fields required specifically for this application."}
            </Text>

            {appSpecificFields.map((f: any) => renderFieldInput(f))}

            {/* Date Field — ALWAYS THE LAST FIELD */}
            <View style={{ marginTop: Spacing.sm }}>
              {renderFieldInput(dateField)}
            </View>

            </View>

            {/* Desktop summary panel */}
            {isDesktop ? (
              <View style={{ width: 340, flexShrink: 0 }}>
                <View style={[styles.dSummary, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                  <Text style={[styles.lbl, { color: colors.brandPrimary, letterSpacing: 1, fontSize: 11 }]}>
                    DOCUMENT SUMMARY
                  </Text>
                  <Text style={{ color: colors.onSurface, fontWeight: "800", fontSize: 16, fontFamily: "serif", marginTop: Spacing.sm }}>
                    {language === "gu" ? template.name_gu : template.name_en}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }} numberOfLines={1}>
                    {language === "gu" ? template.name_en : template.name_gu}
                  </Text>

                  <View style={[styles.dSummaryRow, { borderTopColor: colors.divider }]}>
                    <Ionicons name="wallet-outline" size={16} color={colors.brandPrimary} />
                    <Text style={styles.dSummaryLabel}>Cost</Text>
                    <Text style={styles.dSummaryValue}>1 template credit</Text>
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
          </ScrollView>
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
              {blocks.map((b, i) => (
                <Text
                  key={i}
                  selectable
                  style={[
                    styles.docText,
                    {
                      textAlign: b.align === "center" ? "center" : "left",
                      fontWeight: b.bold ? "700" : "400",
                      fontSize: b.bold ? 15 : 13,
                      marginBottom: b.text ? 6 : 10,
                    },
                  ]}
                >
                  {b.text || " "}
                </Text>
              ))}
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
                {language === "gu"
                  ? "દસ્તાવેજ બનાવવાથી ૧ ક્રેડિટ વપરાશે. કોર્ટમાં રજૂ કરતા પહેલાં અરજીની ચકાસણી કરવી."
                  : "Generating consumes 1 template credit. Review your document — you remain responsible for its accuracy before filing."}
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
    </SafeAreaView>
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
});

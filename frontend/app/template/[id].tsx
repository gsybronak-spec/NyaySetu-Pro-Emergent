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

type Step = "fields" | "preview" | "output";

export default function TemplateApplication() {
  const { colors } = useTheme();
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
  // Which format is being generated right now (drives the per-button loading
  // copy "Generating PDF…" / "Generating Word…").
  const [downloading, setDownloading] = useState<"pdf" | "docx" | "odt" | null>(null);
  const [filename, setFilename] = useState("");
  // Inline success/error feedback: Alert.alert is a NO-OP on web
  // (react-native-web), so the download result must also be visible in the UI
  // or users would get zero feedback — exactly the reported symptom.
  const [notice, setNotice] = useState<{ tone: "ok" | "err"; text: string } | null>(null);
  const [extraOptions, setExtraOptions] = useState<Record<string, any[]>>({});
  // Page size is template-controlled (admin-configured per template, e.g.
  // affidavit -> Legal). The lawyer does NOT choose it; the backend resolves
  // template settings -> global default. No page_size is sent here.
  const draftTimer = useRef<any>(null);

  useEffect(() => {
    (async () => {
      try {
        const t = await api.template(templateId);
        setTemplate(t);
        setFilename(`${t.name_en.replace(/\s+/g, "_")}_${Date.now().toString().slice(-5)}`);
        const initialValues: Record<string, any> = {};
        if (caseId) {
          const c = await api.getCase(caseId);
          setCaseData(c);
          if (c.language) setLanguage(c.language);
          // Case/party data — catalog selects autofill by catalog id so the dropdowns
          // match and the backend resolves ids to the correct-language labels.
          if (c.party_name) initialValues["party_name"] = c.party_name;
          if (c.client_name || c.party_name) initialValues["client_name"] = c.client_name || c.party_name;
          if (c.opposite_party) initialValues["opposite_party"] = c.opposite_party;
          if (c.case_number) initialValues["case_number"] = c.case_number;
          if (c.district_id) initialValues["district"] = c.district_id;
          if (c.court_id) initialValues["court"] = c.court_id;
          if (c.case_type_id) initialValues["case_type"] = c.case_type_id;
          if (c.police_station_label) initialValues["police_station"] = c.police_station_label;
          if (c.client_mobile) initialValues["client_mobile"] = c.client_mobile;
          if (c.client_email) initialValues["client_email"] = c.client_email;
          if (c.client_address) initialValues["client_address"] = c.client_address;
          if (c.law_label) initialValues["law"] = c.law_label;
          if (c.section_label) initialValues["section"] = c.section_label;
          // Admin-configured custom fields (D2) — merged so templates can reference them
          if (c.custom_fields) {
            for (const [k, v] of Object.entries(c.custom_fields)) {
              if (v !== null && v !== undefined && v !== "") initialValues[k] = v;
            }
          }
          initialValues["today"] = new Date().toLocaleDateString("en-GB").replace(/\//g, "-");
        }
        // Advocate dropdown: single option from the logged-in advocate's profile
        // (the app has no advocate catalog — the logged-in advocate drafts the document).
        const me = await api.me().catch(() => null);
        if (me?.name) {
          // Display and autofill the professional advocate name ("Adv. <Name>",
          // no double prefix) so generated documents carry the same format.
          const advName = formatAdvocateName(me.name);
          setExtraOptions((p) => ({ ...p, advocate_name: [{ value: advName, label_en: advName, label_gu: advName }] }));
          if (!initialValues.advocate_name) initialValues["advocate_name"] = advName;
        }
        // Date fields default to today when unset (still editable).
        for (const f of t.fields || []) {
          if (f.type === "date" && !initialValues[f.key]) initialValues[f.key] = new Date().toISOString().slice(0, 10);
        }
        setValues((prev) => ({ ...initialValues, ...prev }));
        if (params.draft === "1") {
          const drafts = await api.drafts();
          const d = drafts.find((x: any) => x.template_id === templateId && (x.case_id || undefined) === caseId);
          if (d) {
            // Merge draft over defaults so autofilled values (advocate, today's
            // date) survive when the draft does not contain them.
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

  // Dates are stored internally as YYYY-MM-DD; documents render them in the
  // app's existing legal style (DD-MM-YYYY). Convert before preview/download.
  const toDocValues = (v: Record<string, any>) => {
    const out: Record<string, any> = {};
    for (const [k, val] of Object.entries(v)) {
      out[k] = isISODate(val) ? formatDateDisplay(val) : val;
    }
    return out;
  };

  const fields = template?.fields || [];

  const missingRequired = useMemo(
    () => fields.filter((f: any) => f.required && !values[f.key]).map((f: any) => f.key),
    [fields, values]
  );

  const genPreview = async () => {
    if (missingRequired.length > 0) {
      Alert.alert("Missing Information", "Please fill all required fields before continuing.");
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

  const download = async (format: "pdf" | "docx" | "odt") => {
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
      // Delivers the file (real browser download on web, share sheet on
      // native) and VALIDATES the bytes are actually the requested format
      // before we claim success. Throws with a readable message otherwise.
      await saveDocument({ filename: res.filename, mime_type: res.mime_type, base64: res.base64 }, format);
      // Only reachable after the download was actually initiated/saved.
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
        // Delivery/validation failure — the file was not handed to the browser.
        setNotice({ tone: "err", text: msg });
        Alert.alert("Unable to download the document", `${msg}`);
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
                  {s === "fields" ? "Details" : s === "preview" ? "Preview" : "Download"}
                </Text>
              </View>
            );
          })}
        </View>

        {step === "fields" && (
          <ScrollView contentContainerStyle={{ padding: Spacing.lg, paddingBottom: 120 }} keyboardShouldPersistTaps="handled">
            {/* Language toggle if no case */}
            {!caseId && (
              <>
                <Text style={[styles.lbl, { color: colors.onSurface }]}>Document Language</Text>
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
                        onPress={() => setLanguage(l.id as any)}
                        style={[styles.langChip, { backgroundColor: active ? colors.brandPrimary : colors.surfaceSecondary, borderColor: active ? colors.brandPrimary : colors.border }]}
                      >
                        <Text style={{ color: active ? colors.onBrandPrimary : colors.onSurface, fontWeight: "700" }}>{l.label}</Text>
                      </Pressable>
                    );
                  })}
                </View>
              </>
            )}

            {/* Auto-filled info */}
            {caseData && (
              <View style={[styles.autofill, { backgroundColor: colors.brandTertiary, borderColor: colors.brandPrimary + "40" }]}>
                <View style={{ flexDirection: "row", alignItems: "center", marginBottom: Spacing.sm }}>
                  <Ionicons name="sparkles" size={16} color={colors.onBrandTertiary} />
                  <Text style={{ color: colors.onBrandTertiary, fontWeight: "800", fontSize: 12, marginLeft: 6, letterSpacing: 0.5 }}>
                    AUTO-FILLED FROM CASE
                  </Text>
                </View>
                <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
                  {[
                    caseData.case_number && `Case: ${caseData.case_number}`,
                    caseData.party_name && `Party: ${caseData.party_name}`,
                    (caseData.court_label || caseData.court) && `Court: ${caseData.court_label || caseData.court}`,
                    (caseData.district_label || caseData.district_id) && `Dist: ${caseData.district_label || caseData.district_id}`,
                  ].filter(Boolean).map((chip: any) => (
                    <View key={chip} style={[styles.autoChip, { backgroundColor: colors.surface }]}>
                      <Text style={{ color: colors.onSurface, fontSize: 11 }}>{chip}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            <Text style={[styles.lbl, { color: colors.onSurface, marginTop: caseData ? Spacing.lg : 0 }]}>
              Application Details
            </Text>
            <Text style={{ color: colors.muted, fontSize: 12, marginBottom: Spacing.md, marginTop: 4 }}>
              Only the fields required for this application.
            </Text>

            {fields.map((f: any) => {
              const label = (language === "gu" ? f.label_gu : f.label_en) + (f.required ? " *" : "");
              const pickLabel = (o: any) => (language === "gu" ? o.label_gu || o.label_en : o.label_en);
              const fvalue = values[f.key];
              if (f.type === "date") {
                return (
                  <DateField
                    key={f.key}
                    testID={`date-${f.key}`}
                    label={label}
                    value={fvalue}
                    onChange={(v) => update(f.key, v)}
                    placeholder="Select date"
                  />
                );
              }
              if (f.type === "select") {
                const districtVal = values.district;
                const opts = (extraOptions[f.key] || f.options || [])
                  .filter((o: any) => !o.district_id || !districtVal || o.district_id === districtVal)
                  .map((o: any) => ({ id: o.value ?? o.key, label: pickLabel(o) }));
                return (
                  <Dropdown
                    key={f.key}
                    testID={`field-${f.key}`}
                    label={label}
                    placeholder="Select..."
                    value={fvalue || null}
                    options={opts}
                    onChange={(v) => {
                      update(f.key, v);
                      // Keep district <-> taluka association: drop a taluka that does
                      // not belong to the newly selected district.
                      if (f.key === "district" && values.taluka) {
                        const talukaField = fields.find((x: any) => x.key === "taluka");
                        const belongs = (talukaField?.options || []).some(
                          (o: any) => o.value === values.taluka && o.district_id === v
                        );
                        if (!belongs) update("taluka", "");
                      }
                    }}
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
              if (f.type === "checkbox") {
                const opts = f.options || [];
                if (opts.length === 0) {
                  const checked = fvalue === "Yes";
                  return (
                    <Pressable
                      key={f.key}
                      testID={`field-${f.key}`}
                      onPress={() => update(f.key, checked ? "No" : "Yes")}
                      style={[styles.autofill, { borderColor: colors.border, marginBottom: Spacing.md }]}
                    >
                      <Ionicons name={checked ? "checkbox" : "square-outline"} size={20} color={checked ? colors.brandPrimary : colors.muted} />
                      <Text style={{ color: colors.onSurface, fontSize: 14, marginLeft: Spacing.sm, flex: 1 }}>{label}</Text>
                    </Pressable>
                  );
                }
                const selected = (fvalue ? String(fvalue).split(",") : []).filter(Boolean);
                const toggle = (v: string) => {
                  const next = selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v];
                  update(f.key, next.join(","));
                };
                return (
                  <View key={f.key} style={{ marginBottom: Spacing.md }}>
                    <Text style={[styles.fieldLbl, { color: colors.onSurfaceSecondary }]}>{label}</Text>
                    {opts.map((o: any) => {
                      const v = o.value ?? o.key;
                      const on = selected.includes(v);
                      return (
                        <Pressable
                          key={v}
                          testID={`field-${f.key}-opt-${v}`}
                          onPress={() => toggle(v)}
                          style={[styles.autofill, { borderColor: colors.border, marginBottom: Spacing.xs }]}
                        >
                          <Ionicons name={on ? "checkbox" : "square-outline"} size={20} color={on ? colors.brandPrimary : colors.muted} />
                          <Text style={{ color: colors.onSurface, fontSize: 14, marginLeft: Spacing.sm, flex: 1 }}>{pickLabel(o)}</Text>
                        </Pressable>
                      );
                    })}
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
                  placeholder={f.placeholder}
                  keyboardType={kt as any}
                  maxLength={f.type === "mobile" ? 15 : undefined}
                  autoCapitalize={f.type === "email" ? "none" : undefined}
                  value={fvalue || ""}
                  onChangeText={(v) => update(f.key, v)}
                />
              );
            })}

          </ScrollView>
        )}

        {step === "preview" && (
          <ScrollView contentContainerStyle={{ padding: Spacing.lg, paddingBottom: 120 }}>
            <View style={[styles.doc, { backgroundColor: "#FFFFFF", borderColor: colors.border }]} testID="preview-doc">
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
            <Pressable testID="edit-btn" onPress={() => setStep("fields")} style={[styles.editRow, { borderColor: colors.brandPrimary }]}>
              <Ionicons name="create-outline" size={18} color={colors.brandPrimary} />
              <Text style={{ color: colors.brandPrimary, fontWeight: "700", marginLeft: 8 }}>Edit Details</Text>
            </Pressable>
          </ScrollView>
        )}

        {step === "output" && (
          <ScrollView contentContainerStyle={{ padding: Spacing.lg, paddingBottom: 120 }} keyboardShouldPersistTaps="handled">
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
            <Text style={[styles.lbl, { color: colors.onSurface }]}>Rename File</Text>
            <View style={{ height: Spacing.sm }} />
            <Field testID="filename-input" value={filename} onChangeText={setFilename} placeholder="File name" />

            <Text style={[styles.lbl, { color: colors.onSurface, marginTop: Spacing.md }]}>Select Format</Text>
            <View style={{ gap: Spacing.md, marginTop: Spacing.sm }}>
              <Pressable
                testID="download-pdf"
                onPress={() => download("pdf")}
                disabled={busy}
                style={[styles.formatCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
              >
                <View style={[styles.formatIcon, { backgroundColor: "#7A1C1C20" }]}>
                  <Ionicons name="document" size={22} color="#7A1C1C" />
                </View>
                <View style={{ flex: 1, marginLeft: Spacing.md }}>
                  <Text style={{ color: colors.onSurface, fontWeight: "700" }}>
                    {downloading === "pdf" ? "Generating PDF…" : "PDF Document"}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 12 }}>Ready to print & file</Text>
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
                style={[styles.formatCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
              >
                <View style={[styles.formatIcon, { backgroundColor: "#1D2D5020" }]}>
                  <Ionicons name="document-text" size={22} color="#1D2D50" />
                </View>
                <View style={{ flex: 1, marginLeft: Spacing.md }}>
                  <Text style={{ color: colors.onSurface, fontWeight: "700" }}>
                    {downloading === "docx" ? "Generating Word…" : "Word Document"}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 12 }}>Editable .docx format</Text>
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
                style={[styles.formatCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
              >
                <View style={[styles.formatIcon, { backgroundColor: "#0B6E4F20" }]}>
                  <Ionicons name="document-outline" size={22} color="#0B6E4F" />
                </View>
                <View style={{ flex: 1, marginLeft: Spacing.md }}>
                  <Text style={{ color: colors.onSurface, fontWeight: "700" }}>
                    {downloading === "odt" ? "Generating Writer…" : "Writer Document"}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 12 }}>LibreOffice .odt format</Text>
                </View>
                {downloading === "odt" ? (
                  <ActivityIndicator size="small" color={colors.brandPrimary} />
                ) : (
                  <Ionicons name="download-outline" size={20} color={colors.brandPrimary} />
                )}
              </Pressable>
            </View>

            <View style={[styles.note, { backgroundColor: colors.surfaceSecondary }]}>
              <Ionicons name="information-circle-outline" size={16} color={colors.muted} />
              <Text style={{ color: colors.muted, fontSize: 11, flex: 1, marginLeft: 6 }}>
                Generating consumes 1 template credit. Review your document — you remain responsible for its accuracy before filing.
              </Text>
            </View>
            {busy && <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: Spacing.lg }} />}
          </ScrollView>
        )}

        {/* Footer CTA */}
        {step === "fields" && (
          <View style={[styles.footer, { backgroundColor: colors.surface, borderTopColor: colors.border }]}>
            <Button testID="continue-preview-btn" title="Preview Document" loading={busy} onPress={genPreview} />
          </View>
        )}
        {step === "preview" && (
          <View style={[styles.footer, { backgroundColor: colors.surface, borderTopColor: colors.border }]}>
            <Button testID="to-output-btn" title="Confirm & Download" onPress={() => setStep("output")} />
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
});

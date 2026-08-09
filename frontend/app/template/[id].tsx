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
import DateTimePicker from "@react-native-community/datetimepicker";
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
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
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [datePickerFor, setDatePickerFor] = useState<string | null>(null);
  const [filename, setFilename] = useState("");
  const draftTimer = useRef<any>(null);

  useEffect(() => {
    (async () => {
      try {
        const t = await api.template(templateId);
        setTemplate(t);
        setFilename(`${t.name_en.replace(/\s+/g, "_")}_${Date.now().toString().slice(-5)}`);
        if (caseId) {
          const c = await api.getCase(caseId);
          setCaseData(c);
          if (c.language) setLanguage(c.language);
        }
        if (params.draft === "1") {
          const drafts = await api.drafts();
          const d = drafts.find((x: any) => x.template_id === templateId && (x.case_id || undefined) === caseId);
          if (d) {
            setValues(d.values || {});
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
      const res = await api.previewApp({ template_id: templateId, case_id: caseId, language, values });
      setPreview(res.content);
      setStep("preview");
    } catch (e: any) {
      Alert.alert("Error", e.message);
    } finally {
      setBusy(false);
    }
  };

  const download = async (format: "pdf" | "docx") => {
    setBusy(true);
    try {
      const res = await api.downloadApp({
        template_id: templateId,
        case_id: caseId,
        language,
        values,
        format,
        filename: `${filename}.${format}`,
      });
      const path = `${FileSystem.cacheDirectory}${res.filename}`;
      await FileSystem.writeAsStringAsync(path, res.base64, { encoding: "base64" });
      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(path, { mimeType: res.mime_type, dialogTitle: "Save or Share Document" });
      }
      Alert.alert(
        "Document Ready",
        `${res.filename} generated successfully. 1 template credit consumed.`,
        [{ text: "Done", onPress: () => (caseId ? router.replace({ pathname: "/case/[id]", params: { id: caseId } }) : router.replace("/(tabs)/home")) }]
      );
    } catch (e: any) {
      if (e.message?.toLowerCase().includes("insufficient") || e.message?.includes("402")) {
        Alert.alert("No Credits", "You have no templates remaining. Please purchase a plan.", [
          { text: "Cancel", style: "cancel" },
          { text: "View Plans", onPress: () => router.push("/(tabs)/subscription") },
        ]);
      } else {
        Alert.alert("Generation Failed", `${e.message}. Your credit has not been deducted.`);
      }
    } finally {
      setBusy(false);
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
                    caseData.court && `Court: ${caseData.court}`,
                    caseData.district_id && `Dist: ${caseData.district_id}`,
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
              if (f.type === "date") {
                return (
                  <View key={f.key} style={{ marginBottom: Spacing.md }}>
                    <Text style={[styles.fieldLbl, { color: colors.onSurfaceSecondary }]}>{label}</Text>
                    <Pressable
                      testID={`date-${f.key}`}
                      onPress={() => setDatePickerFor(f.key)}
                      style={[styles.dateField, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
                    >
                      <Text style={{ color: values[f.key] ? colors.onSurface : colors.muted }}>
                        {values[f.key] || "Select date"}
                      </Text>
                      <Ionicons name="calendar-outline" size={18} color={colors.muted} />
                    </Pressable>
                  </View>
                );
              }
              return (
                <Field
                  key={f.key}
                  testID={`field-${f.key}`}
                  label={label}
                  multiline={f.type === "textarea"}
                  keyboardType={f.type === "number" ? "number-pad" : "default"}
                  value={values[f.key] || ""}
                  onChangeText={(v) => update(f.key, v)}
                />
              );
            })}

            {datePickerFor && (
              <DateTimePicker
                value={new Date()}
                mode="date"
                display={Platform.OS === "ios" ? "spinner" : "default"}
                onChange={(e, d) => {
                  setDatePickerFor(null);
                  if (d) {
                    const key = datePickerFor;
                    const dd = String(d.getDate()).padStart(2, "0");
                    const mm = String(d.getMonth() + 1).padStart(2, "0");
                    update(key, `${dd}-${mm}-${d.getFullYear()}`);
                  }
                }}
              />
            )}
          </ScrollView>
        )}

        {step === "preview" && (
          <ScrollView contentContainerStyle={{ padding: Spacing.lg, paddingBottom: 120 }}>
            <View style={[styles.doc, { backgroundColor: "#FFFFFF", borderColor: colors.border }]}>
              <Text style={styles.docText} selectable>
                {preview}
              </Text>
            </View>
            <Pressable testID="edit-btn" onPress={() => setStep("fields")} style={[styles.editRow, { borderColor: colors.brandPrimary }]}>
              <Ionicons name="create-outline" size={18} color={colors.brandPrimary} />
              <Text style={{ color: colors.brandPrimary, fontWeight: "700", marginLeft: 8 }}>Edit Details</Text>
            </Pressable>
          </ScrollView>
        )}

        {step === "output" && (
          <ScrollView contentContainerStyle={{ padding: Spacing.lg, paddingBottom: 120 }} keyboardShouldPersistTaps="handled">
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
                  <Text style={{ color: colors.onSurface, fontWeight: "700" }}>PDF Document</Text>
                  <Text style={{ color: colors.muted, fontSize: 12 }}>Ready to print & file</Text>
                </View>
                <Ionicons name="download-outline" size={20} color={colors.brandPrimary} />
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
                  <Text style={{ color: colors.onSurface, fontWeight: "700" }}>Word Document</Text>
                  <Text style={{ color: colors.muted, fontSize: 12 }}>Editable .docx format</Text>
                </View>
                <Ionicons name="download-outline" size={20} color={colors.brandPrimary} />
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
  dateField: {
    minHeight: 50, borderRadius: Radius.md, borderWidth: 1, paddingHorizontal: Spacing.md,
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
  },
  doc: { padding: Spacing.lg, borderRadius: Radius.md, borderWidth: 1 },
  docText: { color: "#111", fontSize: 13, lineHeight: 22 },
  editRow: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    marginTop: Spacing.md, paddingVertical: Spacing.md, borderRadius: Radius.md, borderWidth: 1.5,
  },
  formatCard: { flexDirection: "row", alignItems: "center", padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1 },
  formatIcon: { width: 42, height: 42, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  note: { flexDirection: "row", alignItems: "flex-start", padding: Spacing.md, borderRadius: Radius.md, marginTop: Spacing.lg },
  footer: { position: "absolute", bottom: 0, left: 0, right: 0, padding: Spacing.lg, borderTopWidth: StyleSheet.hairlineWidth },
});

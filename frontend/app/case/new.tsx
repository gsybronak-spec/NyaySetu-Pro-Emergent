import { useEffect, useMemo, useState } from "react";
import { Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { Dropdown } from "@/src/components/Dropdown";
import { useTheme } from "@/src/theme/ThemeContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";

export default function NewCase() {
  const { colors } = useTheme();
  const [language, setLanguage] = useState<"en" | "gu">("en");
  const [step, setStep] = useState(1);
  const [caseTypes, setCaseTypes] = useState<any[]>([]);
  const [laws, setLaws] = useState<any[]>([]);
  const [sections, setSections] = useState<any[]>([]);
  const [districts, setDistricts] = useState<any[]>([]);
  const [form, setForm] = useState<any>({
    nickname: "",
    case_number: "",
    case_type_id: null,
    case_type_custom: "",
    complaint_type: null,
    law_id: null,
    law_custom: "",
    section_id: null,
    party_name: "",
    opposite_party: "",
    court: "",
    district_id: null,
    police_station: "",
    notes: "",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.caseTypes().then(setCaseTypes).catch(() => {});
    api.laws().then(setLaws).catch(() => {});
    api.districts().then(setDistricts).catch(() => {});
  }, []);

  useEffect(() => {
    if (form.law_id && form.law_id !== "other_law") {
      api.lawSections(form.law_id).then(setSections).catch(() => setSections([]));
    } else {
      setSections([]);
    }
  }, [form.law_id]);

  const update = (k: string, v: any) => setForm((f: any) => ({ ...f, [k]: v }));

  const save = async () => {
    setSaving(true);
    try {
      const payload: any = { language, ...form };
      const c = await api.createCase(payload);
      router.replace({ pathname: "/case/[id]", params: { id: c.id } });
    } catch (e: any) {
      Alert.alert("Error", e.message);
    } finally {
      setSaving(false);
    }
  };

  const showComplaint = !!form.case_type_id;
  const showLaw = form.complaint_type === "private";
  const showOther = form.complaint_type === "other";

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top", "bottom"]}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={[styles.header, { borderBottomColor: colors.border }]}>
          <Pressable testID="new-case-back" onPress={() => router.back()} hitSlop={12}>
            <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
          </Pressable>
          <Text style={[styles.h1, { color: colors.onSurface }]}>New Case</Text>
          <View style={{ width: 24 }} />
        </View>

        <ScrollView contentContainerStyle={{ padding: Spacing.lg, paddingBottom: 120 }} keyboardShouldPersistTaps="handled">
          {/* Language toggle */}
          <Text style={[styles.sectionLbl, { color: colors.onSurface }]}>Document Language</Text>
          <View style={styles.langRow}>
            {[
              { id: "en", label: "English", sub: "Please enter the application information in English." },
              { id: "gu", label: "ગુજરાતી", sub: "કૃપા કરીને અરજીની માહિતી ગુજરાતી ભાષામાં ભરો." },
            ].map((l) => {
              const active = language === l.id;
              return (
                <Pressable
                  key={l.id}
                  testID={`lang-${l.id}`}
                  onPress={() => setLanguage(l.id as any)}
                  style={[
                    styles.langCard,
                    {
                      backgroundColor: active ? colors.brandPrimary : colors.surfaceSecondary,
                      borderColor: active ? colors.brandPrimary : colors.border,
                    },
                  ]}
                >
                  <Text style={{ color: active ? colors.onBrandPrimary : colors.onSurface, fontWeight: "800", fontSize: 15 }}>
                    {l.label}
                  </Text>
                  <Text style={{ color: active ? colors.onBrandPrimary : colors.muted, fontSize: 11, marginTop: 4 }} numberOfLines={2}>
                    {l.sub}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          <View style={{ height: Spacing.lg }} />
          <Text style={[styles.sectionLbl, { color: colors.onSurface }]}>Case Information</Text>

          <Field testID="case-nickname" label="Case Nickname (optional)" placeholder="e.g. Patel Matter" value={form.nickname} onChangeText={(v) => update("nickname", v)} />
          <Field testID="case-number" label="Case Number" placeholder="e.g. 12345/2024" value={form.case_number} onChangeText={(v) => update("case_number", v)} />

          <Dropdown
            testID="case-type"
            label="Case Type"
            placeholder="Select case type"
            value={form.case_type_id}
            options={caseTypes.map((c) => ({ id: c.id, label: language === "gu" ? c.gu : c.en, sublabel: c.cat }))}
            onChange={(v) => update("case_type_id", v)}
          />
          {form.case_type_id === "other" && (
            <Field testID="case-type-custom" label="Enter Case Type" value={form.case_type_custom} onChangeText={(v) => update("case_type_custom", v)} />
          )}

          {showComplaint && (
            <Dropdown
              testID="complaint-type"
              label="Complaint Type"
              placeholder="Select complaint type"
              value={form.complaint_type}
              options={[
                { id: "private", label: "Private Complaint" },
                { id: "police", label: "Police Complaint" },
                { id: "other", label: "Other" },
              ]}
              onChange={(v) => update("complaint_type", v)}
            />
          )}

          {showLaw && (
            <>
              <Dropdown
                testID="law"
                label="Applicable Law"
                placeholder="Select law"
                value={form.law_id}
                options={laws.map((l) => ({ id: l.id, label: language === "gu" ? l.gu : l.en }))}
                onChange={(v) => update("law_id", v)}
              />
              {form.law_id === "other_law" && (
                <Field testID="law-custom" label="Specify Law" value={form.law_custom} onChangeText={(v) => update("law_custom", v)} />
              )}
              {sections.length > 0 && (
                <Dropdown
                  testID="section"
                  label="Section / Provision"
                  placeholder="Select section"
                  value={form.section_id}
                  options={sections.map((s: any) => ({ id: s.id, label: s.label }))}
                  onChange={(v) => update("section_id", v)}
                />
              )}
            </>
          )}

          {form.complaint_type === "police" && (
            <Field testID="police-station" label="Police Station" placeholder="e.g. Naranpura P.S." value={form.police_station} onChangeText={(v) => update("police_station", v)} />
          )}

          {showOther && (
            <Field testID="complaint-desc" label="Complaint Description" multiline value={form.notes} onChangeText={(v) => update("notes", v)} />
          )}

          <View style={{ height: Spacing.md }} />
          <Text style={[styles.sectionLbl, { color: colors.onSurface }]}>Parties & Court</Text>
          <Field testID="party-name" label="Primary Party / Client Name" placeholder="Applicant name" value={form.party_name} onChangeText={(v) => update("party_name", v)} />
          <Field testID="opposite-party" label="Opposite Party (optional)" value={form.opposite_party} onChangeText={(v) => update("opposite_party", v)} />
          <Dropdown
            testID="district"
            label="District"
            placeholder="Select district"
            value={form.district_id}
            options={districts.map((d) => ({ id: d.id, label: language === "gu" ? d.gu : d.en, sublabel: language === "gu" ? d.en : d.gu }))}
            onChange={(v) => update("district_id", v)}
          />
          <Field testID="court" label="Court" placeholder="e.g. Ld. Metropolitan Magistrate" value={form.court} onChangeText={(v) => update("court", v)} />
        </ScrollView>

        <View style={[styles.footer, { backgroundColor: colors.surface, borderTopColor: colors.border }]}>
          <Button testID="save-case-btn" title="Save Case" loading={saving} onPress={save} />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  h1: { fontSize: 18, fontWeight: "700", fontFamily: "serif" },
  sectionLbl: { fontSize: 14, fontWeight: "800", marginBottom: Spacing.md, letterSpacing: 0.5 },
  langRow: { flexDirection: "row", gap: Spacing.md },
  langCard: { flex: 1, padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1.5, minHeight: 78 },
  footer: {
    position: "absolute", bottom: 0, left: 0, right: 0,
    padding: Spacing.lg, borderTopWidth: StyleSheet.hairlineWidth,
  },
});

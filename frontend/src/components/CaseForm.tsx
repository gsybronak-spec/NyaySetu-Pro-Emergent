import { useEffect, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { Dropdown } from "@/src/components/Dropdown";
import { useTheme } from "@/src/theme/ThemeContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";

export interface CaseFormValues {
  language: "en" | "gu";
  nickname: string;
  case_number: string;
  case_type_id: string | null;
  case_type_custom: string;
  complaint_type: string | null;
  law_id: string | null;
  law_custom: string;
  section_id: string | null;
  complaint_custom?: string;
  party_name: string;
  opposite_party: string;
  court_id: string | null;
  court_custom: string;
  district_id: string | null;
  police_station_id: string | null;
  police_station_custom: string;
  notes: string;
  custom_fields?: Record<string, any>;
}

const DEFAULTS: CaseFormValues = {
  language: "en",
  nickname: "",
  case_number: "",
  case_type_id: null,
  case_type_custom: "",
  complaint_type: null,
  law_id: null,
  law_custom: "",
  section_id: null,
  complaint_custom: "",
  party_name: "",
  opposite_party: "",
  court_id: null,
  court_custom: "",
  district_id: null,
  police_station_id: null,
  police_station_custom: "",
  notes: "",
  custom_fields: {},
};

interface Props {
  title: string;
  submitLabel: string;
  initial?: Partial<CaseFormValues>;
  saving: boolean;
  onSubmit: (values: CaseFormValues) => void;
}

export function CaseForm({ title, submitLabel, initial, saving, onSubmit }: Props) {
  const { colors } = useTheme();
  const [form, setForm] = useState<CaseFormValues>({ ...DEFAULTS, ...initial });
  const [caseTypes, setCaseTypes] = useState<any[]>([]);
  const [laws, setLaws] = useState<any[]>([]);
  const [sections, setSections] = useState<any[]>([]);
  const [districts, setDistricts] = useState<any[]>([]);
  const [courts, setCourts] = useState<any[]>([]);
  const [policeStations, setPoliceStations] = useState<any[]>([]);
  const [favCourts, setFavCourts] = useState<string[]>([]);

  // Mobile Lookup State
  const [searchMobile, setSearchMobile] = useState<string>("");
  const [lookupLoading, setLookupLoading] = useState<boolean>(false);
  const [lookupStatus, setLookupStatus] = useState<{ type: "success" | "warning" | "error"; message: string } | null>(null);

  // Dynamic Case Form Configuration from Admin API
  const [dynamicFields, setDynamicFields] = useState<any[]>([]);
  const [customValues, setCustomValues] = useState<Record<string, any>>(initial?.custom_fields || {});

  useEffect(() => {
    api.caseTypes().then((r) => setCaseTypes(Array.isArray(r) ? r : [])).catch(() => setCaseTypes([]));
    api.laws().then((r) => setLaws(Array.isArray(r) ? r : [])).catch(() => setLaws([]));
    api.districts().then((r) => setDistricts(Array.isArray(r) ? r : [])).catch(() => setDistricts([]));
    api.favCourts().then((r) => setFavCourts(Array.isArray(r?.favourite_courts) ? r.favourite_courts : [])).catch(() => setFavCourts([]));
  }, []);

  useEffect(() => {
    if (form.case_type_id) {
      api.caseFormConfig(form.case_type_id)
        .then((cfg) => {
          if (cfg && Array.isArray(cfg.fields)) {
            setDynamicFields(cfg.fields);
          } else {
            setDynamicFields([]);
          }
        })
        .catch(() => setDynamicFields([]));
    }
  }, [form.case_type_id]);

  useEffect(() => {
    if (form.law_id && form.law_id !== "other_law") {
      api.lawSections(form.law_id).then(setSections).catch(() => setSections([]));
    } else {
      setSections([]);
    }
  }, [form.law_id]);

  useEffect(() => {
    api.courts(form.district_id || undefined).then((r) => setCourts(r || [])).catch(() => {});
    api.policeStations(form.district_id || undefined).then((r) => setPoliceStations(r || [])).catch(() => {});
  }, [form.district_id]);

  const language = form.language;
  const update = (k: keyof CaseFormValues, v: any) => setForm((f) => ({ ...f, [k]: v }));
  const updateCustom = (k: string, v: any) => setCustomValues((prev) => ({ ...prev, [k]: v }));

  const handleMobileLookup = async () => {
    if (!searchMobile || searchMobile.trim().length < 10) {
      setLookupStatus({ type: "error", message: "Please enter a valid 10-digit mobile number." });
      return;
    }
    setLookupLoading(true);
    setLookupStatus(null);
    try {
      const res = await api.lookupClient(searchMobile.trim());
      if (res.found && res.client) {
        setLookupStatus({
          type: "success",
          message: `Client found: ${res.client.name || "Registered User"} (${res.client.mobile})`,
        });
        // Autofill matching fields
        if (res.client.name) update("party_name", res.client.name);
        if (res.client.district) {
          const matchedDistrict = districts.find((d) => d.en.toLowerCase() === res.client.district.toLowerCase() || d.id === res.client.district);
          if (matchedDistrict) update("district_id", matchedDistrict.id);
        }
      } else {
        setLookupStatus({
          type: "warning",
          message: res.message || `Client with mobile '${searchMobile}' not found. You can enter details manually.`,
        });
      }
    } catch (e: any) {
      setLookupStatus({ type: "error", message: e.message || "Client lookup failed." });
    } finally {
      setLookupLoading(false);
    }
  };

  const toggleFavCourt = (id: string) => {
    const isFav = favCourts.includes(id);
    setFavCourts((prev) => (isFav ? prev.filter((x) => x !== id) : [...prev, id]));
    (isFav ? api.removeFavCourt(id) : api.addFavCourt(id))
      .then((r) => setFavCourts(r.favourite_courts || []))
      .catch(() => {});
  };

  const showComplaint = !!form.case_type_id;
  const showLaw = form.complaint_type === "private";
  const showOther = form.complaint_type === "other";

  const handleFormSubmit = () => {
    onSubmit({
      ...form,
      custom_fields: customValues,
    });
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top", "bottom"]}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={[styles.header, { borderBottomColor: colors.border }]}>
          <Pressable testID="case-form-back" onPress={() => router.back()} hitSlop={12}>
            <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
          </Pressable>
          <Text style={[styles.h1, { color: colors.onSurface }]}>{title}</Text>
          <View style={{ width: 24 }} />
        </View>

        <ScrollView contentContainerStyle={{ padding: Spacing.lg, paddingBottom: 120 }} keyboardShouldPersistTaps="handled">
          {/* Client Mobile Lookup Header */}
          <View style={[styles.lookupCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
            <Text style={[styles.sectionLbl, { color: colors.onSurface }]}>Client Mobile Lookup & Autofill</Text>
            <View style={{ flexDirection: "row", gap: Spacing.sm, alignItems: "center" }}>
              <View style={{ flex: 1 }}>
                <Field
                  testID="client-mobile-search"
                  label=""
                  placeholder="Enter 10-digit Client Mobile Number"
                  value={searchMobile}
                  onChangeText={setSearchMobile}
                />
              </View>
              <Pressable
                testID="lookup-btn"
                onPress={handleMobileLookup}
                disabled={lookupLoading}
                style={[styles.searchBtn, { backgroundColor: colors.brandPrimary }]}
              >
                {lookupLoading ? <ActivityIndicator size="small" color="#fff" /> : <Text style={styles.searchBtnText}>Search</Text>}
              </Pressable>
            </View>
            {lookupStatus && (
              <View
                style={[
                  styles.statusBanner,
                  {
                    backgroundColor:
                      lookupStatus.type === "success" ? "#dcfce7" : lookupStatus.type === "warning" ? "#fef3c7" : "#fee2e2",
                  },
                ]}
              >
                <Text
                  style={{
                    color: lookupStatus.type === "success" ? "#166534" : lookupStatus.type === "warning" ? "#92400e" : "#991b1b",
                    fontSize: 13,
                    fontWeight: "600",
                  }}
                >
                  {lookupStatus.message}
                </Text>
              </View>
            )}
          </View>

          <View style={{ height: Spacing.lg }} />

          {/* Language toggle */}
          <Text style={[styles.sectionLbl, { color: colors.onSurface }]}>Document Language</Text>
          <View style={styles.langRow}>
            {[
              { id: "en", label: "English", sub: "Please enter application details in English." },
              { id: "gu", label: "ગુજરાતી", sub: "કૃપા કરીને વિગતો ગુજરાતીમાં ભરો." },
            ].map((l) => {
              const active = language === l.id;
              return (
                <Pressable
                  key={l.id}
                  testID={`lang-${l.id}`}
                  onPress={() => update("language", l.id)}
                  style={[
                    styles.langCard,
                    { backgroundColor: active ? colors.brandPrimary : colors.surfaceSecondary, borderColor: active ? colors.brandPrimary : colors.border },
                  ]}
                >
                  <Text style={{ color: active ? colors.onBrandPrimary : colors.onSurface, fontWeight: "800", fontSize: 15 }}>{l.label}</Text>
                  <Text style={{ color: active ? colors.onBrandPrimary : colors.muted, fontSize: 11, marginTop: 4 }} numberOfLines={2}>{l.sub}</Text>
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
            searchable
            value={form.case_type_id}
            options={caseTypes.map((c) => ({ id: c.id, label: language === "gu" ? c.gu : c.en, sublabel: c.cat }))}
            onChange={(v) => update("case_type_id", v)}
          />
          {form.case_type_id === "other" && (
            <Field testID="case-type-custom" label="Other Case Type" placeholder="Enter case type" value={form.case_type_custom} onChangeText={(v) => update("case_type_custom", v)} />
          )}

          {/* Dynamic Admin Fields */}
          {dynamicFields.length > 0 && (
            <View style={[styles.dynamicSection, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
              <Text style={[styles.sectionLbl, { color: colors.onSurface }]}>Admin Configured Case Fields</Text>
              {dynamicFields.map((df) => (
                <Field
                  key={df.key}
                  testID={`dynamic-${df.key}`}
                  label={language === "gu" ? df.label_gu || df.label_en : df.label_en}
                  placeholder={df.placeholder || `Enter ${df.label_en}`}
                  value={customValues[df.key] || ""}
                  onChangeText={(v) => updateCustom(df.key, v)}
                />
              ))}
            </View>
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
                searchable
                value={form.law_id}
                options={laws.map((l) => ({ id: l.id, label: language === "gu" ? l.gu : l.en }))}
                onChange={(v) => update("law_id", v)}
              />
              {form.law_id === "other_law" && (
                <Field testID="law-custom" label="Other Law" placeholder="Specify law" value={form.law_custom} onChangeText={(v) => update("law_custom", v)} />
              )}
              {sections.length > 0 && (
                <Dropdown
                  testID="section"
                  label="Section / Provision"
                  placeholder="Select section"
                  searchable
                  value={form.section_id}
                  options={sections.map((s: any) => ({ id: s.id, label: s.label }))}
                  onChange={(v) => update("section_id", v)}
                />
              )}
            </>
          )}

          {form.complaint_type === "police" && (
            <>
              <Dropdown
                testID="police-station"
                label="Police Station"
                placeholder="Select police station"
                searchable
                value={form.police_station_id}
                options={[
                  ...policeStations.map((p) => ({ id: p.id, label: language === "gu" ? p.gu : p.en })),
                  { id: "other", label: "Other (type manually)" },
                ]}
                onChange={(v) => update("police_station_id", v)}
              />
              {form.police_station_id === "other" && (
                <Field testID="police-station-custom" label="Enter Police Station" value={form.police_station_custom} onChangeText={(v) => update("police_station_custom", v)} />
              )}
            </>
          )}

          {showOther && (
            <Field testID="complaint-custom" label="Other Complaint Type" placeholder="Describe complaint type" value={form.complaint_custom} onChangeText={(v) => update("complaint_custom", v)} />
          )}

          <View style={{ height: Spacing.md }} />
          <Text style={[styles.sectionLbl, { color: colors.onSurface }]}>Parties & Court</Text>
          <Field testID="party-name" label="Primary Party / Client Name" placeholder="Applicant name" value={form.party_name} onChangeText={(v) => update("party_name", v)} />
          <Field testID="opposite-party" label="Opposite Party (optional)" value={form.opposite_party} onChangeText={(v) => update("opposite_party", v)} />
          <Dropdown
            testID="district"
            label="District"
            placeholder="Select district"
            searchable
            value={form.district_id}
            options={districts.map((d) => ({ id: d.id, label: language === "gu" ? d.gu : d.en, sublabel: language === "gu" ? d.en : d.gu }))}
            onChange={(v) => update("district_id", v)}
          />
          <Dropdown
            testID="court"
            label="Court"
            placeholder="Select court"
            searchable
            value={form.court_id}
            favouriteIds={favCourts}
            onToggleFavourite={toggleFavCourt}
            options={[
              ...courts.map((c) => ({ id: c.id, label: language === "gu" ? c.gu : c.en })),
              { id: "other", label: "Other (type manually)", pinnable: false },
            ]}
            onChange={(v) => update("court_id", v)}
          />
          {form.court_id === "other" && (
            <Field testID="court-custom" label="Enter Court" placeholder="e.g. Ld. Metropolitan Magistrate" value={form.court_custom} onChangeText={(v) => update("court_custom", v)} />
          )}
        </ScrollView>

        <View style={[styles.footer, { backgroundColor: colors.surface, borderTopColor: colors.border }]}>
          <Button testID="save-case-btn" title={submitLabel} loading={saving} onPress={handleFormSubmit} />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, borderBottomWidth: StyleSheet.hairlineWidth,
  },
  h1: { fontSize: 18, fontWeight: "700", fontFamily: "serif" },
  sectionLbl: { fontSize: 14, fontWeight: "800", marginBottom: Spacing.md, letterSpacing: 0.5 },
  langRow: { flexDirection: "row", gap: Spacing.md },
  langCard: { flex: 1, padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1.5, minHeight: 78 },
  lookupCard: { padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1 },
  searchBtn: { paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, borderRadius: Radius.md, justifyContent: "center", alignItems: "center" },
  searchBtnText: { color: "#ffffff", fontWeight: "700", fontSize: 14 },
  statusBanner: { marginTop: Spacing.sm, padding: Spacing.sm, borderRadius: Radius.sm },
  dynamicSection: { padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1, marginVertical: Spacing.md },
  footer: { position: "absolute", bottom: 0, left: 0, right: 0, padding: Spacing.lg, borderTopWidth: StyleSheet.hairlineWidth },
});

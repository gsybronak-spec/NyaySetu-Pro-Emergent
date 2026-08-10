import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { Dropdown } from "@/src/components/Dropdown";
import { DateField } from "@/src/components/DateField";
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
  // Flat client details (D3) — captured here, stored on the case.
  client_mobile: string;
  client_email: string;
  client_address: string;
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
  client_mobile: "",
  client_email: "",
  client_address: "",
};

// autofill_map resolves against the CLIENT context (D1), not the advocate's user record.
function resolveAutofill(map: string | undefined, ctx: Record<string, string | undefined>): string | undefined {
  if (!map) return undefined;
  const key = (map.split(".").pop() || "").toLowerCase();
  const val = ctx[key];
  return val ? String(val) : undefined;
}

function buildClientContext(form: CaseFormValues, districts: any[]): Record<string, string | undefined> {
  const d = districts.find((x) => x.id === form.district_id);
  return {
    name: form.party_name || undefined,
    mobile: form.client_mobile || undefined,
    email: form.client_email || undefined,
    address: form.client_address || undefined,
    district: (form.language === "gu" ? d?.gu : d?.en) || d?.en || undefined,
  };
}

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
        const c = res.client;
        setLookupStatus({
          type: "success",
          message: `Client found: ${c.name || "Registered User"} (${c.mobile})`,
        });
        // Autofill matching core fields
        if (c.name) update("party_name", c.name);
        if (c.district) {
          const matchedDistrict = districts.find((d) => d.en.toLowerCase() === c.district.toLowerCase() || d.id === c.district);
          if (matchedDistrict) update("district_id", matchedDistrict.id);
        }
        // Flat client details (D3)
        update("client_mobile", c.mobile || searchMobile.trim());
        if (c.email) update("client_email", c.email);
        // Prefill admin-configured fields via autofill_map against CLIENT context (D1)
        const ctx: Record<string, string | undefined> = {
          name: c.name || form.party_name || undefined,
          mobile: c.mobile || searchMobile.trim() || undefined,
          email: c.email || form.client_email || undefined,
          address: form.client_address || undefined,
          district: c.district || undefined,
        };
        setCustomValues((prev) => {
          const next = { ...prev };
          for (const df of dynamicFields) {
            const am = df.autofill_map;
            if (am && (next[df.key] === undefined || next[df.key] === "")) {
              const val = resolveAutofill(am, ctx);
              if (val) next[df.key] = val;
            }
          }
          return next;
        });
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

  // Keep stored custom field keys editable even if the admin form config changed (edit persistence).
  const orphanCustomFields = useMemo(() => {
    if (!initial?.custom_fields) return [];
    const configKeys = new Set(dynamicFields.map((df) => df.key));
    return Object.keys(initial.custom_fields)
      .filter((k) => !configKeys.has(k))
      .map((k) => ({ key: k, label_en: k, label_gu: k, type: "text", required: false, order: 99 }));
  }, [dynamicFields, initial?.custom_fields]);

  const allDynamicFields = useMemo(() => [...dynamicFields, ...orphanCustomFields], [dynamicFields, orphanCustomFields]);

  const handleFormSubmit = () => {
    // 1. Resolve autofill_map against client context for any empty mapped fields (D1).
    const ctx = buildClientContext(form, districts);
    const finalCustom: Record<string, any> = { ...customValues };
    for (const df of dynamicFields) {
      const am = df.autofill_map;
      if (am && (finalCustom[df.key] === undefined || finalCustom[df.key] === "")) {
        const val = resolveAutofill(am, ctx);
        if (val) finalCustom[df.key] = val;
      }
    }
    // 2. Enforce required admin-configured fields.
    const missing = dynamicFields.filter((df) => df.required && (finalCustom[df.key] === undefined || String(finalCustom[df.key]).trim() === ""));
    if (missing.length > 0) {
      const names = missing.map((m) => (form.language === "gu" ? m.label_gu || m.label_en : m.label_en)).join(", ");
      Alert.alert("Missing Information", `Please fill the required field(s): ${names}`);
      return;
    }
    // 3. Flat client fields (D3). client_name/client_district are derived and
    //    stored on the case (the API accepts them; they are not form state).
    const d = districts.find((x) => x.id === form.district_id);
    const payload: CaseFormValues & { client_name?: string; client_district?: string } = {
      ...form,
      client_name: form.party_name || undefined,
      client_district: (form.language === "gu" ? d?.gu : d?.en) || d?.en || undefined,
      custom_fields: finalCustom,
    };
    onSubmit(payload as CaseFormValues);
  };

  const renderDynamicField = (df: any) => {
    const label = (form.language === "gu" ? df.label_gu || df.label_en : df.label_en) + (df.required ? " *" : "");
    const value = customValues[df.key];
    const setVal = (v: any) => updateCustom(df.key, v);
    const pickLabel = (o: any) => (form.language === "gu" ? o.label_gu || o.label_en : o.label_en);
    switch (df.type) {
      case "textarea":
        return <Field key={df.key} testID={`dynamic-${df.key}`} label={label} multiline placeholder={df.placeholder || `Enter ${df.label_en}`} value={value || ""} onChangeText={setVal} />;
      case "number":
        return <Field key={df.key} testID={`dynamic-${df.key}`} label={label} keyboardType="number-pad" placeholder={df.placeholder || `Enter ${df.label_en}`} value={value || ""} onChangeText={setVal} />;
      case "mobile":
        return <Field key={df.key} testID={`dynamic-${df.key}`} label={label} keyboardType="phone-pad" maxLength={15} placeholder={df.placeholder || "10-digit mobile"} value={value || ""} onChangeText={setVal} />;
      case "email":
        return <Field key={df.key} testID={`dynamic-${df.key}`} label={label} keyboardType="email-address" autoCapitalize="none" placeholder={df.placeholder || "you@example.com"} value={value || ""} onChangeText={setVal} />;
      case "date":
        return (
          <DateField
            key={df.key}
            testID={`dynamic-date-${df.key}`}
            label={label}
            value={value}
            onChange={setVal}
            placeholder={df.placeholder || "Select date"}
          />
        );
      case "select": {
        const opts = (df.options || []).map((o: any) => ({ id: o.value ?? o.key, label: pickLabel(o) }));
        return <Dropdown key={df.key} testID={`dynamic-select-${df.key}`} label={label} placeholder="Select..." value={value || null} options={opts} onChange={setVal} />;
      }
      case "radio": {
        const opts = df.options || [];
        return (
          <View key={df.key} style={{ marginBottom: Spacing.md }}>
            <Text style={{ color: colors.onSurfaceSecondary, fontSize: 13, fontWeight: "600", marginBottom: Spacing.xs }}>{label}</Text>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: Spacing.sm }}>
              {opts.map((o: any) => {
                const v = o.value ?? o.key;
                const active = value === v;
                return (
                  <Pressable
                    key={v}
                    testID={`dynamic-radio-${df.key}-${v}`}
                    onPress={() => setVal(v)}
                    style={[styles.chip, { backgroundColor: active ? colors.brandPrimary : colors.surfaceSecondary, borderColor: active ? colors.brandPrimary : colors.border }]}
                  >
                    <Text style={{ color: active ? colors.onBrandPrimary : colors.onSurface, fontSize: 13, fontWeight: "700" }}>{pickLabel(o)}</Text>
                  </Pressable>
                );
              })}
            </View>
          </View>
        );
      }
      case "checkbox": {
        const opts = df.options || [];
        if (opts.length === 0) {
          const checked = value === "Yes";
          return (
            <Pressable
              key={df.key}
              testID={`dynamic-check-${df.key}`}
              onPress={() => setVal(checked ? "No" : "Yes")}
              style={[styles.checkRow, { borderColor: colors.border, backgroundColor: colors.surfaceSecondary }]}
            >
              <Ionicons name={checked ? "checkbox" : "square-outline"} size={20} color={checked ? colors.brandPrimary : colors.muted} />
              <Text style={{ color: colors.onSurface, fontSize: 14, marginLeft: Spacing.sm, flex: 1 }}>{label}</Text>
            </Pressable>
          );
        }
        const selected = (value ? String(value).split(",") : []).filter(Boolean);
        const toggle = (v: string) => {
          const next = selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v];
          setVal(next.join(","));
        };
        return (
          <View key={df.key} style={{ marginBottom: Spacing.md }}>
            <Text style={{ color: colors.onSurfaceSecondary, fontSize: 13, fontWeight: "600", marginBottom: Spacing.xs }}>{label}</Text>
            {opts.map((o: any) => {
              const v = o.value ?? o.key;
              const on = selected.includes(v);
              return (
                <Pressable
                  key={v}
                  testID={`dynamic-check-${df.key}-${v}`}
                  onPress={() => toggle(v)}
                  style={[styles.checkRow, { borderColor: colors.border, backgroundColor: colors.surfaceSecondary, marginBottom: Spacing.xs }]}
                >
                  <Ionicons name={on ? "checkbox" : "square-outline"} size={20} color={on ? colors.brandPrimary : colors.muted} />
                  <Text style={{ color: colors.onSurface, fontSize: 14, marginLeft: Spacing.sm, flex: 1 }}>{pickLabel(o)}</Text>
                </Pressable>
              );
            })}
          </View>
        );
      }
      default:
        return <Field key={df.key} testID={`dynamic-${df.key}`} label={label} placeholder={df.placeholder || `Enter ${df.label_en}`} value={value || ""} onChangeText={setVal} />;
    }
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

          {/* Client Details (flat fields, D3) — autofilled on lookup, editable */}
          <Text style={[styles.sectionLbl, { color: colors.onSurface }]}>Client Details</Text>
          <Text style={{ color: colors.muted, fontSize: 12, marginBottom: Spacing.md, marginTop: -6 }}>
            Auto-filled from client search. Name & district are set under Parties & Court below.
          </Text>
          <Field
            testID="client-mobile"
            label="Client Mobile"
            placeholder="10-digit mobile"
            keyboardType="phone-pad"
            maxLength={15}
            value={form.client_mobile}
            onChangeText={(v) => update("client_mobile", v)}
          />
          <Field
            testID="client-email"
            label="Client Email (optional)"
            placeholder="client@example.com"
            keyboardType="email-address"
            autoCapitalize="none"
            value={form.client_email}
            onChangeText={(v) => update("client_email", v)}
          />
          <Field
            testID="client-address"
            label="Client Address (optional)"
            placeholder="Full address"
            multiline
            value={form.client_address}
            onChangeText={(v) => update("client_address", v)}
          />

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
          {allDynamicFields.length > 0 && (
            <View style={[styles.dynamicSection, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
              <Text style={[styles.sectionLbl, { color: colors.onSurface }]}>Admin Configured Case Fields</Text>
              {allDynamicFields.map((df) => renderDynamicField(df))}
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
  chip: {
    height: 36,
    paddingHorizontal: Spacing.lg,
    borderRadius: 999,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  checkRow: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  footer: { position: "absolute", bottom: 0, left: 0, right: 0, padding: Spacing.lg, borderTopWidth: StyleSheet.hairlineWidth },
});

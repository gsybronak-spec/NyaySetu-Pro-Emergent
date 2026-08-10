import { useEffect, useState } from "react";
import { ActivityIndicator, Alert, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";

import { CaseForm, CaseFormValues } from "@/src/components/CaseForm";
import { useTheme } from "@/src/theme/ThemeContext";
import { api } from "@/src/api/client";

export default function EditCase() {
  const { colors } = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [initial, setInitial] = useState<Partial<CaseFormValues> | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getCase(String(id)).then((c) => {
      setInitial({
        language: c.language || "en",
        nickname: c.nickname || "",
        case_number: c.case_number || "",
        case_type_id: c.case_type_id || null,
        case_type_custom: c.case_type_custom || "",
        complaint_type: c.complaint_type || null,
        law_id: c.law_id || null,
        law_custom: c.law_custom || "",
        section_id: c.section_id || null,
        complaint_custom: c.complaint_custom || "",
        party_name: c.party_name || "",
        opposite_party: c.opposite_party || "",
        court_id: c.court_id || null,
        court_custom: c.court_custom || c.court || "",
        district_id: c.district_id || null,
        police_station_id: c.police_station_id || null,
        police_station_custom: c.police_station_custom || c.police_station || "",
        notes: c.notes || "",
        custom_fields: c.custom_fields || {},
        client_mobile: c.client_mobile || "",
        client_email: c.client_email || "",
        client_address: c.client_address || "",
      });
    }).catch((e) => Alert.alert("Error", e.message));
  }, [id]);

  const save = async (values: CaseFormValues) => {
    setSaving(true);
    try {
      await api.updateCase(String(id), values);
      router.replace({ pathname: "/case/[id]", params: { id: String(id) } });
      setTimeout(() => Alert.alert("Saved", "Case updated successfully."), 300);
    } catch (e: any) {
      Alert.alert("Error", e.message);
    } finally {
      setSaving(false);
    }
  };

  if (!initial) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center" }}>
        <ActivityIndicator color={colors.brandPrimary} />
      </View>
    );
  }

  return <CaseForm title="Edit Case" submitLabel="Update Case" initial={initial} saving={saving} onSubmit={save} />;
}

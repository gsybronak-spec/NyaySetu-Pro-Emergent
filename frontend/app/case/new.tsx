import { useState } from "react";
import { Alert } from "react-native";
import { router } from "expo-router";

import { CaseForm, CaseFormValues } from "@/src/components/CaseForm";
import { api } from "@/src/api/client";

export default function NewCase() {
  const [saving, setSaving] = useState(false);

  const save = async (values: CaseFormValues) => {
    setSaving(true);
    try {
      await api.createCase(values);
      router.replace("/(tabs)/cases");
      setTimeout(() => Alert.alert("Success", "Case created successfully."), 300);
    } catch (e: any) {
      Alert.alert("Error", e.message);
    } finally {
      setSaving(false);
    }
  };

  return <CaseForm title="New Case" submitLabel="Save Case" saving={saving} onSubmit={save} />;
}

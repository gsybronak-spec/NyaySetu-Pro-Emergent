import { useState } from "react";
import { Alert, Platform } from "react-native";
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
      setTimeout(() => {
        if (Platform.OS !== "web") {
          Alert.alert("Success", "Case created successfully.");
        }
      }, 300);
    } catch (e: any) {
      const msg = e?.message || "Failed to create case";
      if (Platform.OS === "web" && typeof window !== "undefined") {
        window.alert(`Error: ${msg}`);
      } else {
        Alert.alert("Error", msg);
      }
    } finally {
      setSaving(false);
    }
  };

  return <CaseForm title="New Case" submitLabel="Save Case" saving={saving} onSubmit={save} />;
}

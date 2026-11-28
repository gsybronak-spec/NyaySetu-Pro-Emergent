import { useState } from "react";
import { Alert, Platform } from "react-native";
import { router } from "expo-router";

import { CaseForm, CaseFormValues } from "@/src/components/CaseForm";
import { api } from "@/src/api/client";
import { useAppLanguage } from "@/src/context/AppLanguageContext";

export default function NewCase() {
  const { t, ui } = useAppLanguage();
  const [saving, setSaving] = useState(false);

  const save = async (values: CaseFormValues) => {
    setSaving(true);
    try {
      await api.createCase(values);
      router.replace("/(tabs)/cases");
      setTimeout(() => {
        if (Platform.OS !== "web") {
          Alert.alert(t("successTitle"), ui("Case created successfully.", "કેસ સફળતાપૂર્વક બની ગયો છે."));
        }
      }, 300);
    } catch (e: any) {
      const msg = e?.message || ui("Failed to create case", "કેસ બનાવવામાં નિષ્ફળતા");
      if (Platform.OS === "web" && typeof window !== "undefined") {
        window.alert(`${t("errorTitle")}: ${msg}`);
      } else {
        Alert.alert(t("errorTitle"), msg);
      }
    } finally {
      setSaving(false);
    }
  };

  return <CaseForm title={t("newCaseBtn")} submitLabel={ui("Save Case", "કેસ સાચવો")} saving={saving} onSubmit={save} />;
}

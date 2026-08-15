import { useEffect, useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { Dropdown } from "@/src/components/Dropdown";
import { useAuth } from "@/src/context/AuthContext";
import { useTheme } from "@/src/theme/ThemeContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";

export default function Onboarding() {
  const { colors, isDark } = useTheme();
  const { user, refresh } = useAuth();
  const [nameEn, setNameEn] = useState(user?.advocate_name_en || user?.name || "");
  const [nameGu, setNameGu] = useState(user?.advocate_name_gu || "");
  const [email, setEmail] = useState(user?.email || "");
  const [barNo, setBarNo] = useState(user?.bar_council_no || "");
  const [state, setState] = useState(user?.state || "Gujarat");
  const [district, setDistrict] = useState<string | null>(user?.district || null);
  const [court, setCourt] = useState(user?.court || "");
  const [districts, setDistricts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.districts().then((r) => setDistricts(Array.isArray(r) ? r : [])).catch(() => setDistricts([]));
  }, []);

  const save = async (goCongrats = true) => {
    setLoading(true);
    try {
      await api.updateProfile({
        name: nameEn || undefined,
        advocate_name_en: nameEn || undefined,
        advocate_name_gu: nameGu || undefined,
        email: email || undefined,
        bar_council_no: barNo || undefined,
        state: state || undefined,
        district: district || undefined,
        court: court || undefined,
      });
      await refresh();
      router.replace(goCongrats ? "/(auth)/congrats" : "/(tabs)/home");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top", "bottom"]}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={styles.header}>
          <Text style={[styles.h1, { color: colors.onSurface }]}>Advocate Profile</Text>
          <Pressable testID="onboarding-skip-button" onPress={() => router.replace("/(auth)/congrats")}>
            <Text style={{ color: colors.brandPrimary, fontWeight: "700" }}>Skip for Now</Text>
          </Pressable>
        </View>
        <Text style={[styles.sub, { color: colors.muted }]}>
          Add your details for auto-filled documents. You can complete this later.
        </Text>

        <ScrollView contentContainerStyle={{ padding: Spacing.xl, paddingTop: Spacing.md }} keyboardShouldPersistTaps="handled">
          <Field testID="ob-name-en" label="Advocate Name (English)" placeholder="e.g. Adv. Ronak Solanki" value={nameEn} onChangeText={setNameEn} />
          <Field testID="ob-name-gu" label="Advocate Name (Gujarati) / વકીલનું નામ" placeholder="દા.ત. એડવોકેટ રોનક સોલંકી" value={nameGu} onChangeText={setNameGu} />
          <Field testID="ob-email" label="Email" placeholder="you@example.com" keyboardType="email-address" autoCapitalize="none" value={email} onChangeText={setEmail} />
          <Field testID="ob-bar" label="Bar Council / Enrollment Number" placeholder="e.g. G/1234/2020" value={barNo} onChangeText={setBarNo} />
          <Field testID="ob-state" label="State" placeholder="State" value={state} onChangeText={setState} />
          <Dropdown
            testID="ob-district"
            label="District"
            placeholder="Select district"
            value={district}
            options={districts.map((d: any) => ({ id: d.id, label: `${d.en} / ${d.gu}` }))}
            onChange={setDistrict}
          />
          <Field testID="ob-court" label="Court / Practice Location" placeholder="e.g. Ahmedabad District Court" value={court} onChangeText={setCourt} />

          <View style={[styles.info, { backgroundColor: colors.brandTertiary, borderColor: colors.brandPrimary + "40" }]}>
            <Ionicons name="information-circle" size={18} color={colors.onBrandTertiary} />
            <Text style={{ color: colors.onBrandTertiary, fontSize: 12, flex: 1, marginLeft: 8 }}>
              This information auto-fills your court applications in the chosen language.
            </Text>
          </View>

          <Button testID="ob-save-button" title="Save & Continue" loading={loading} onPress={() => save(true)} style={{ marginTop: Spacing.md }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: Spacing.xl, paddingTop: Spacing.md },
  h1: { fontSize: 24, fontWeight: "700", fontFamily: "serif" },
  sub: { fontSize: 13, paddingHorizontal: Spacing.xl, marginTop: 4 },
  info: { flexDirection: "row", alignItems: "center", padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1, marginVertical: Spacing.md },
});

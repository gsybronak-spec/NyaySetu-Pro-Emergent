import { useState } from "react";
import { Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router } from "expo-router";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { KeyboardAwareScrollView } from "@/src/components/KeyboardAwareScrollView";
import { api } from "@/src/api/client";
import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { useAppLanguage } from "@/src/context/AppLanguageContext";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";
import { safeBack } from "@/src/utils/navigation";

export default function SetPassword() {
  const { colors } = useTheme();
  const { user, refresh } = useAuth();
  const { t, ui } = useAppLanguage();
  const { isDesktop } = useResponsive();
  const isFirst = !user?.has_password;
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [success, setSuccess] = useState(false);

  const save = async () => {
    setErr(undefined);
    if (password.length < 8) {
      setErr(ui("Password must be at least 8 characters", "પાસવર્ડ ઓછામાં ઓછા ૮ અક્ષરોનો હોવો જોઈએ"));
      return;
    }
    if (password !== confirm) {
      setErr(ui("Passwords do not match", "બંને પાસવર્ડ સરખા નથી"));
      return;
    }
    setBusy(true);
    try {
      await api.setPassword(password);
      await refresh();
      setSuccess(true);
      if (Platform.OS === "web") {
        setTimeout(() => safeBack("/(tabs)/profile"), 1200);
      } else {
        Alert.alert(t("successTitle"), ui("Password updated successfully!", "પાસવર્ડ સફળતાપૂર્વક અપડેટ થઈ ગયો છે!"), [
          { text: t("ok"), onPress: () => safeBack("/(tabs)/profile") },
        ]);
      }
    } catch (e: any) {
      setErr(e?.message || ui("Could not save password. Please try again.", "પાસવર્ડ સાચવી શકાયો નથી. કૃપા કરીને ફરી પ્રયાસ કરો."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top", "bottom"]}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={[styles.header, { borderBottomColor: colors.border }]}>
          <Pressable onPress={() => safeBack("/(tabs)/profile")} hitSlop={8} testID="set-password-back">
            <Ionicons name="arrow-back" size={24} color={colors.onSurface} />
          </Pressable>
          <Text style={[styles.h1, { color: colors.onSurface }]}>
            {isFirst ? ui("Set Password", "પાસવર્ડ સેટ કરો") : ui("Change Password", "પાસવર્ડ બદલો")}
          </Text>
          <View style={{ width: 24 }} />
        </View>

        <KeyboardAwareScrollView contentContainerStyle={[styles.container, isDesktop && styles.desktopContainer]} keyboardShouldPersistTaps="handled">
          {success ? (
            <View style={[styles.successBanner, { backgroundColor: "#10B98120", borderColor: "#10B981" }]}>
              <Ionicons name="checkmark-circle" size={24} color="#10B981" />
              <Text style={{ color: colors.onSurface, fontWeight: "700", marginLeft: 10, fontSize: 15 }}>
                {ui("Password saved successfully! Redirecting...", "પાસવર્ડ સાચવાઈ ગયો! રીડાયરેક્ટ થઈ રહ્યું છે...")}
              </Text>
            </View>
          ) : null}

          {isFirst && !success && (
            <View style={[styles.info, { backgroundColor: colors.brandTertiary, borderColor: colors.brandPrimary + "40" }]}>
              <Ionicons name="information-circle" size={20} color={colors.onBrandTertiary} />
              <Text style={{ color: colors.onBrandTertiary, fontSize: 13, flex: 1, marginLeft: 10, lineHeight: 19 }}>
                {ui(
                  "Your account was created with OTP. Set a password now to also log in with your mobile/email and password.",
                  "તમારું એકાઉન્ટ OTP થી બનેલું છે. મોબાઇલ/ઈમેલ અને પાસવર્ડથી લૉગિન કરવા માટે પાસવર્ડ સેટ કરો."
                )}
              </Text>
            </View>
          )}

          <Field
            testID="set-password-input"
            label={ui("New Password", "નવો પાસવર્ડ")}
            placeholder={ui("Minimum 8 characters", "ઓછામાં ઓછા ૮ અક્ષરો")}
            secureTextEntry={!showPassword}
            autoCapitalize="none"
            value={password}
            onChangeText={setPassword}
            error={err}
          />
          <Field
            testID="set-password-confirm-input"
            label={ui("Confirm Password", "પાસવર્ડ ફરી દાખલ કરો")}
            placeholder={ui("Re-enter new password", "નવો પાસવર્ડ ફરીથી લખો")}
            secureTextEntry={!showPassword}
            autoCapitalize="none"
            value={confirm}
            onChangeText={setConfirm}
          />
          <Pressable testID="set-password-show" onPress={() => setShowPassword((v) => !v)} style={{ marginBottom: Spacing.lg }}>
            <Text style={{ color: colors.brandPrimary, fontSize: 13, fontWeight: "600" }}>
              <Ionicons name={showPassword ? "eye-off-outline" : "eye-outline"} size={16} color={colors.brandPrimary} />{" "}
              {showPassword ? ui("Hide password", "પાસવર્ડ છુપાવો") : ui("Show password", "પાસવર્ડ બતાવો")}
            </Text>
          </Pressable>

          <Button
            testID="set-password-save"
            title={isFirst ? ui("Set Password", "પાસવર્ડ સેટ કરો") : ui("Save Password", "પાસવર્ડ સાચવો")}
            loading={busy}
            onPress={save}
          />
        </KeyboardAwareScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
  },
  h1: { fontSize: 18, fontWeight: "700" },
  container: {
    padding: Spacing.xl,
  },
  desktopContainer: {
    maxWidth: 520,
    alignSelf: "center",
    width: "100%",
    paddingTop: Spacing.xxl,
  },
  info: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
    marginBottom: Spacing.xl,
  },
  successBanner: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
    marginBottom: Spacing.xl,
  },
});

import { useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { api } from "@/src/api/client";
import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { Spacing } from "@/src/theme/tokens";

export default function SetPassword() {
  const { colors } = useTheme();
  const { user, refresh } = useAuth();
  const isFirst = !user?.has_password;
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();

  const save = async () => {
    setErr(undefined);
    if (password.length < 8) {
      setErr("Password must be at least 8 characters");
      return;
    }
    if (password !== confirm) {
      setErr("Passwords do not match");
      return;
    }
    setBusy(true);
    try {
      await api.setPassword(password);
      await refresh();
      router.back();
    } catch (e: any) {
      setErr(e?.message || "Could not save password. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top", "bottom"]}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={[styles.header, { borderBottomColor: colors.border }]}>
          <Pressable onPress={() => router.back()} hitSlop={8} testID="set-password-back">
            <Ionicons name="arrow-back" size={24} color={colors.onSurface} />
          </Pressable>
          <Text style={[styles.h1, { color: colors.onSurface }]}>{isFirst ? "Set Password" : "Change Password"}</Text>
          <View style={{ width: 24 }} />
        </View>

        <ScrollView contentContainerStyle={{ padding: Spacing.xl }} keyboardShouldPersistTaps="handled">
          {isFirst && (
            <View style={[styles.info, { backgroundColor: colors.brandTertiary, borderColor: colors.brandPrimary + "40" }]}>
              <Ionicons name="information-circle" size={18} color={colors.onBrandTertiary} />
              <Text style={{ color: colors.onBrandTertiary, fontSize: 12.5, flex: 1, marginLeft: 8, lineHeight: 18 }}>
                Your account was created with OTP. Set a password now to also login with mobile/email + password.
              </Text>
            </View>
          )}

          <Field
            testID="set-password-input"
            label="New Password"
            placeholder="Minimum 8 characters"
            secureTextEntry={!showPassword}
            autoCapitalize="none"
            value={password}
            onChangeText={setPassword}
            error={err}
          />
          <Field
            testID="set-password-confirm-input"
            label="Confirm Password"
            placeholder="Re-enter new password"
            secureTextEntry={!showPassword}
            autoCapitalize="none"
            value={confirm}
            onChangeText={setConfirm}
          />
          <Pressable testID="set-password-show" onPress={() => setShowPassword((v) => !v)} style={{ marginBottom: Spacing.md }}>
            <Text style={{ color: colors.brandPrimary, fontSize: 13, fontWeight: "600" }}>
              <Ionicons name={showPassword ? "eye-off-outline" : "eye-outline"} size={15} color={colors.brandPrimary} />{" "}
              {showPassword ? "Hide" : "Show"} password
            </Text>
          </Pressable>

          <Button testID="set-password-save" title={isFirst ? "Set Password" : "Save Password"} loading={busy} onPress={save} />
        </ScrollView>
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
  h1: { fontSize: 20, fontWeight: "700", fontFamily: "serif" },
  info: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.md,
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: Spacing.lg,
  },
});

import React, { useState } from "react";
import { Alert, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { Button } from "@/src/components/Button";
import { KeyboardAwareScrollView } from "@/src/components/KeyboardAwareScrollView";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";
import { safeBack } from "@/src/utils/navigation";

export default function DeleteAccountScreen() {
  const { colors } = useTheme();
  const { isDesktop } = useResponsive();
  const { user, deleteAccount } = useAuth();

  const [confirmText, setConfirmText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const canDelete = confirmText.trim().toUpperCase() === "DELETE";

  const handleDelete = async () => {
    if (!canDelete || busy) return;
    setErr(null);
    setBusy(true);
    try {
      await deleteAccount();
      setDone(true);
      if (Platform.OS !== "web") {
        Alert.alert("Account Deleted", "Your account and personal data have been permanently deleted.", [
          { text: "OK", onPress: () => router.replace("/(auth)/login") },
        ]);
      } else {
        setTimeout(() => router.replace("/(auth)/login"), 1400);
      }
    } catch (e: any) {
      setErr(e?.message || "Could not delete account. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top", "bottom"]}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={[styles.header, { borderBottomColor: colors.border }]}>
          <Pressable
            testID="delete-account-back"
            onPress={() => safeBack(user ? "/(tabs)/profile" : "/(auth)/login")}
            hitSlop={12}
          >
            <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
          </Pressable>
          <Text style={[styles.h1, { color: colors.onSurface }]}>Delete Account</Text>
          <View style={{ width: 24 }} />
        </View>

        <KeyboardAwareScrollView
          contentContainerStyle={[styles.container, isDesktop && styles.desktopContainer]}
          keyboardShouldPersistTaps="handled"
        >
          <View style={[styles.card, { backgroundColor: colors.surfaceSecondary, borderColor: colors.error + "50" }]}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 10, marginBottom: Spacing.sm }}>
              <View style={[styles.iconCircle, { backgroundColor: colors.error + "1A" }]}>
                <Ionicons name="warning-outline" size={22} color={colors.error} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[styles.title, { color: colors.onSurface }]}>
                  Permanent Account Deletion / એકાઉન્ટ કાયમ માટે કાઢી નાખો
                </Text>
              </View>
            </View>

            <Text style={[styles.body, { color: colors.onSurfaceSecondary }]}>
              Deleting your NyaySetu Pro account permanently erases your profile details, saved cases, draft applications, generated document history, notifications, and any remaining wallet credits. This action cannot be undone.
            </Text>
            <Text style={[styles.body, { color: colors.muted, marginTop: Spacing.xs }]}>
              તમારું એકાઉન્ટ ડિલીટ કરવાથી પ્રોફાઇલ, સેવ કરેલા કેસ, ડ્રાફ્ટ્સ, ડોક્યુમેન્ટ હિસ્ટ્રી અને વોલેટ ક્રેડિટ્સ કાયમ માટે ભૂંસાઈ જશે. (કાયદેસર પેમેન્ટ/ટેક્સ રેકોર્ડ્સ વ્યક્તિગત ઓળખ વિના રાખવામાં આવી શકે છે.)
            </Text>
          </View>

          {done ? (
            <View style={[styles.card, { backgroundColor: "#10B9811A", borderColor: "#10B981" }]}>
              <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 15 }}>
                Account permanently deleted. Redirecting...
              </Text>
            </View>
          ) : user ? (
            <View style={[styles.card, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
              <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 14, marginBottom: 4 }}>
                Signed in as: {user.mobile ? `+91 ${user.mobile}` : user.email || user.name || user.id}
              </Text>
              <Text style={{ color: colors.muted, fontSize: 13, marginBottom: Spacing.md }}>
                Type <Text style={{ fontWeight: "800", color: colors.error }}>DELETE</Text> below to confirm permanent account deletion:
              </Text>
              <TextInput
                testID="delete-account-confirm-input"
                value={confirmText}
                onChangeText={setConfirmText}
                placeholder="Type DELETE"
                placeholderTextColor={colors.muted}
                autoCapitalize="characters"
                autoCorrect={false}
                style={[
                  styles.input,
                  { color: colors.onSurface, backgroundColor: colors.surface, borderColor: colors.border },
                ]}
              />
              {err ? (
                <Text style={{ color: colors.error, fontSize: 12.5, marginTop: Spacing.xs, fontWeight: "600" }}>{err}</Text>
              ) : null}

              <View style={{ marginTop: Spacing.lg }}>
                <Button
                  testID="delete-account-submit-btn"
                  title="Permanently Delete My Account"
                  variant="secondary"
                  style={{ backgroundColor: colors.error }}
                  disabled={!canDelete}
                  loading={busy}
                  onPress={handleDelete}
                />
              </View>
            </View>
          ) : (
            <View style={[styles.card, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
              <Text style={[styles.title, { color: colors.onSurface, marginBottom: Spacing.xs }]}>
                How to Delete Your Account
              </Text>
              <Text style={[styles.body, { color: colors.onSurfaceSecondary }]}>
                1. Sign in to NyaySetu Pro with your registered mobile number or email.{"\n"}
                2. Open Profile → Delete Account, type DELETE, and confirm for immediate deletion.{"\n\n"}
                If you cannot access your account, email{" "}
                <Text style={{ fontWeight: "700", color: colors.brandPrimary }}>support@nyaysetupro.in</Text>{" "}
                from your registered email address or share your registered mobile number; we will verify ownership and delete your account within 7 days.
              </Text>
              <View style={{ marginTop: Spacing.lg }}>
                <Button
                  testID="delete-account-login-btn"
                  title="Sign In to Delete Account"
                  onPress={() => router.push("/(auth)/login")}
                />
              </View>
            </View>
          )}
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
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  h1: { fontSize: 18, fontWeight: "700", fontFamily: "serif" },
  container: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: 100 },
  desktopContainer: { maxWidth: 640, width: "100%", alignSelf: "center", paddingTop: Spacing.xl },
  card: { padding: Spacing.lg, borderRadius: Radius.md, borderWidth: 1 },
  iconCircle: { width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center" },
  title: { fontSize: 15, fontWeight: "700" },
  body: { fontSize: 13.5, lineHeight: 20 },
  input: {
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: 11,
    fontSize: 14,
    fontWeight: "700",
  },
});

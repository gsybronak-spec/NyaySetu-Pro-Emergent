import { useState } from "react";
import { Image, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { api } from "@/src/api/client";
import { firebaseConfigured, firebaseSendPasswordReset } from "@/src/hooks/useFirebaseAuth";
import { Spacing } from "@/src/theme/tokens";

export default function ForgotPassword() {
  const [mobile, setMobile] = useState("");
  const [resetVia, setResetVia] = useState<"otp" | "firebase">("otp");
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [stepErr, setStepErr] = useState<string>();

  const sendOtp = async () => {
    setErr(undefined);
    const m = mobile.trim();
    // Firebase email reset for email input when Firebase is configured; the
    // existing mobile-OTP reset stays for legacy accounts and mobile numbers.
    if (m.includes("@") && firebaseConfigured) {
      setBusy(true);
      try {
        await firebaseSendPasswordReset(m);
        setResetVia("firebase");
        setDone(true);
      } catch (e: any) {
        setErr(e?.message || "Could not send the reset email. Please try again.");
      } finally {
        setBusy(false);
      }
      return;
    }
    if (!/^\d{10}$/.test(m)) {
      setErr("Enter a valid 10-digit mobile number");
      return;
    }
    setBusy(true);
    try {
      await api.forgotPassword(m);
      setResetVia("otp");
      setOtpSent(true);
    } catch (e: any) {
      setErr(e?.message || "Could not send OTP. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const reset = async () => {
    setStepErr(undefined);
    if (!/^\d{6}$/.test(otp)) {
      setStepErr("Enter the 6-digit OTP");
      return;
    }
    if (password.length < 8) {
      setStepErr("Password must be at least 8 characters");
      return;
    }
    if (password !== confirm) {
      setStepErr("Passwords do not match");
      return;
    }
    setBusy(true);
    try {
      await api.resetPassword(mobile.trim(), otp.trim(), password);
      setDone(true);
    } catch (e: any) {
      setStepErr(e?.message || "Password reset failed. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <LinearGradient colors={["#061024", "#0B1B3D"]} style={{ flex: 1 }}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={{ flex: 1 }}
      >
        <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
          <View style={styles.brandBlock}>
            <View style={styles.logo}>
              <Image source={require("../../assets/images/logo.png")} style={styles.logoImage} resizeMode="contain" />
            </View>
            <Text style={styles.title}>NyaySetu Pro</Text>
            <Text style={styles.tagline}>The New Era of Advocacy</Text>
          </View>

          <View style={styles.card}>
            {done ? (
              <>
                <Ionicons name="checkmark-circle" size={56} color="#4CAF50" style={{ alignSelf: "center", marginBottom: Spacing.md }} />
                <Text style={styles.cardTitle}>Password Reset</Text>
                <Text style={styles.cardSub}>
                  {resetVia === "firebase"
                    ? "If a matching account exists, a password reset email has been sent to your inbox."
                    : "Password reset successfully. Please login with your new password."}
                </Text>
                <Button
                  testID="forgot-go-login"
                  title="Go to Login"
                  onPress={() => router.replace("/(auth)/login")}
                />
              </>
            ) : !otpSent ? (
              <>
                <Text style={styles.cardTitle}>Forgot Password</Text>
                <Text style={styles.cardSub}>
                  Enter your registered mobile number (we'll send an OTP) or email (we'll send a reset link).
                </Text>
                <Field
                  testID="forgot-mobile-input"
                  label="Mobile Number or Email"
                  labelColor="#D1D8E5"
                  placeholder="10-digit mobile or email"
                  keyboardType="email-address"
                  autoCapitalize="none"
                  value={mobile}
                  onChangeText={setMobile}
                  error={err}
                />
                <Button testID="forgot-send-otp-button" title="Send Reset" loading={busy} onPress={sendOtp} />
              </>
            ) : (
              <>
                <Text style={styles.cardTitle}>Reset Password</Text>
                <Text style={styles.cardSub}>
                  Enter the OTP sent to <Text style={{ color: "#FDFDFD", fontWeight: "700" }}>+91 {mobile}</Text> and choose a new password.
                </Text>
                <Field
                  testID="forgot-otp-input"
                  label="Enter OTP"
                  labelColor="#D1D8E5"
                  placeholder="123456"
                  keyboardType="number-pad"
                  maxLength={6}
                  value={otp}
                  onChangeText={setOtp}
                />
                <View>
                  <Field
                    testID="forgot-password-input"
                    label="New Password"
                    labelColor="#D1D8E5"
                    placeholder="Minimum 8 characters"
                    secureTextEntry={!showPassword}
                    autoCapitalize="none"
                    value={password}
                    onChangeText={setPassword}
                    error={stepErr}
                  />
                  <Pressable
                    testID="forgot-show-password"
                    onPress={() => setShowPassword((v) => !v)}
                    style={styles.eyeBtn}
                    hitSlop={8}
                  >
                    <Ionicons name={showPassword ? "eye-off-outline" : "eye-outline"} size={20} color="#A6B1C2" />
                  </Pressable>
                </View>
                <Field
                  testID="forgot-confirm-input"
                  label="Confirm New Password"
                  labelColor="#D1D8E5"
                  placeholder="Re-enter new password"
                  secureTextEntry={!showPassword}
                  autoCapitalize="none"
                  value={confirm}
                  onChangeText={setConfirm}
                />
                <Button testID="forgot-reset-button" title="Reset Password" loading={busy} onPress={reset} />
              </>
            )}

            <Pressable testID="forgot-back-login" onPress={() => router.replace("/(auth)/login")} style={{ marginTop: Spacing.lg, alignItems: "center" }}>
              <Text style={{ color: "#A6B1C2", fontSize: 13 }}>
                <Ionicons name="arrow-back" size={14} color="#A6B1C2" /> Back to Login
              </Text>
            </Pressable>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, padding: Spacing.xl, justifyContent: "center" },
  brandBlock: { alignItems: "center", marginBottom: Spacing.xl },
  logo: { alignItems: "center", justifyContent: "center" },
  logoImage: { width: 92, height: 99 },
  title: { color: "#FDFDFD", fontSize: 26, fontWeight: "700", marginTop: Spacing.md, fontFamily: "serif" },
  tagline: { color: "#C5A059", fontSize: 11, marginTop: 4, letterSpacing: 2, textTransform: "uppercase" },
  card: {
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 20,
    padding: Spacing.xl,
    borderWidth: 1,
    borderColor: "rgba(197,160,89,0.15)",
  },
  cardTitle: { color: "#FDFDFD", fontSize: 22, fontWeight: "700", marginBottom: 4 },
  cardSub: { color: "#A6B1C2", fontSize: 13, marginBottom: Spacing.lg, lineHeight: 19 },
  eyeBtn: { position: "absolute", right: 12, top: 42 },
});

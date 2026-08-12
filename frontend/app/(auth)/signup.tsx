import { useState } from "react";
import { Image, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { useAuth } from "@/src/context/AuthContext";
import { api } from "@/src/api/client";
import { Spacing } from "@/src/theme/tokens";

export default function Signup() {
  const { registerAccount, loading } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [mobile, setMobile] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [referral, setReferral] = useState("");
  const [showReferral, setShowReferral] = useState(false);
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [otpBusy, setOtpBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [otpErr, setOtpErr] = useState<string>();

  const validateBasics = (): string | undefined => {
    if (!mobile.trim()) return "Enter your mobile number";
    if (!/^\d{10}$/.test(mobile.trim())) return "Enter a valid 10-digit mobile number";
    if (password.length < 8) return "Password must be at least 8 characters";
    if (password !== confirm) return "Passwords do not match";
    if (email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) return "Enter a valid email address";
    return undefined;
  };

  const sendOtp = async () => {
    setErr(undefined);
    const v = validateBasics();
    if (v) {
      setErr(v);
      return;
    }
    setOtpBusy(true);
    try {
      await api.sendOtp(mobile.trim());
      setOtpSent(true);
      setOtpErr(undefined);
    } catch (e: any) {
      setErr(e?.message || "Could not send OTP. Please try again.");
    } finally {
      setOtpBusy(false);
    }
  };

  const createAccount = async () => {
    setOtpErr(undefined);
    if (!/^\d{6}$/.test(otp)) {
      setOtpErr("Enter the 6-digit OTP");
      return;
    }
    try {
      await registerAccount({
        mobile: mobile.trim(),
        otp: otp.trim(),
        password,
        name: name.trim() || undefined,
        email: email.trim() || undefined,
        referralCode: referral.trim() || undefined,
      });
      router.replace("/(auth)/onboarding");
    } catch (e: any) {
      setOtpErr(e?.message || "Account creation failed. Please try again.");
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
            <Text style={styles.cardTitle}>Create Account</Text>
            <Text style={styles.cardSub}>Register with your mobile number and a password</Text>

            <Field
              testID="signup-name-input"
              label="Advocate Name"
              labelColor="#D1D8E5"
              placeholder="Full name (optional)"
              value={name}
              onChangeText={setName}
            />
            <Field
              testID="signup-email-input"
              label="Email"
              labelColor="#D1D8E5"
              placeholder="you@example.com (optional)"
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              value={email}
              onChangeText={setEmail}
            />
            <Field
              testID="signup-mobile-input"
              label="Mobile Number"
              labelColor="#D1D8E5"
              placeholder="10-digit mobile"
              keyboardType="number-pad"
              maxLength={10}
              value={mobile}
              onChangeText={setMobile}
              error={err}
            />
            <View>
              <Field
                testID="signup-password-input"
                label="Password"
                labelColor="#D1D8E5"
                placeholder="Minimum 8 characters"
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                value={password}
                onChangeText={setPassword}
              />
              <Pressable
                testID="signup-show-password"
                onPress={() => setShowPassword((v) => !v)}
                style={styles.eyeBtn}
                hitSlop={8}
              >
                <Ionicons name={showPassword ? "eye-off-outline" : "eye-outline"} size={20} color="#A6B1C2" />
              </Pressable>
            </View>
            <Field
              testID="signup-confirm-input"
              label="Confirm Password"
              labelColor="#D1D8E5"
              placeholder="Re-enter your password"
              secureTextEntry={!showPassword}
              autoCapitalize="none"
              value={confirm}
              onChangeText={setConfirm}
            />

            {showReferral ? (
              <Field
                testID="signup-referral-input"
                label="Referral Code (optional)"
                labelColor="#D1D8E5"
                placeholder="e.g. NSA1B2C3"
                autoCapitalize="characters"
                value={referral}
                onChangeText={setReferral}
              />
            ) : (
              <Pressable testID="signup-referral-toggle" onPress={() => setShowReferral(true)} style={{ marginBottom: Spacing.md }}>
                <Text style={{ color: "#C5A059", fontSize: 13, fontWeight: "600" }}>Have a referral code?</Text>
              </Pressable>
            )}

            {!otpSent ? (
              <Button testID="signup-send-otp-button" title="Send OTP" loading={otpBusy} onPress={sendOtp} />
            ) : (
              <>
                <Text style={styles.otpNote}>
                  We've sent a 6-digit code to <Text style={{ color: "#FDFDFD", fontWeight: "700" }}>+91 {mobile}</Text>
                </Text>
                <Field
                  testID="signup-otp-input"
                  label="Enter OTP"
                  labelColor="#D1D8E5"
                  placeholder="123456"
                  keyboardType="number-pad"
                  maxLength={6}
                  value={otp}
                  onChangeText={setOtp}
                  error={otpErr}
                />
                <Button testID="signup-create-button" title="Create Account" loading={loading} onPress={createAccount} />
              </>
            )}

            <Pressable testID="signup-back-login" onPress={() => router.replace("/(auth)/login")} style={{ marginTop: Spacing.lg, alignItems: "center" }}>
              <Text style={{ color: "#A6B1C2", fontSize: 13 }}>
                Already have an account? <Text style={{ color: "#C5A059", fontWeight: "700" }}>Login</Text>
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
  brandBlock: { alignItems: "center", marginBottom: Spacing.lg },
  logo: { alignItems: "center", justifyContent: "center" },
  logoImage: { width: 88, height: 95 },
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
  cardSub: { color: "#A6B1C2", fontSize: 13, marginBottom: Spacing.lg },
  eyeBtn: { position: "absolute", right: 12, top: 42 },
  otpNote: { color: "#A6B1C2", fontSize: 13, marginBottom: Spacing.md, lineHeight: 18 },
});

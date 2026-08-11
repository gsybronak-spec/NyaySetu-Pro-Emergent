import { useState } from "react";
import { Image, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { useAuth } from "@/src/context/AuthContext";
import { useGoogleAuth } from "@/src/hooks/useGoogleAuth";
import { Spacing } from "@/src/theme/tokens";

export default function Login() {
  const [mobile, setMobile] = useState("");
  const [referral, setReferral] = useState("");
  const [showReferral, setShowReferral] = useState(false);
  const [err, setErr] = useState<string>();
  const { signInOtp, loading } = useAuth();
  const { startGoogleLogin, googleBusy, googleError, setGoogleError } = useGoogleAuth();

  const submit = async () => {
    setErr(undefined);
    const m = mobile.trim();
    if (!/^\d{10}$/.test(m)) {
      setErr("Enter a valid 10-digit mobile number");
      return;
    }
    try {
      await signInOtp(m);
      router.push({ pathname: "/(auth)/otp", params: { mobile: m, referral: referral.trim() } });
    } catch (e: any) {
      setErr(e.message);
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
            <Text style={styles.cardTitle}>Sign in</Text>
            <Text style={styles.cardSub}>Enter your mobile number to receive OTP</Text>

            <Field
              testID="login-mobile-input"
              label="Mobile Number"
              labelColor="#D1D8E5"
              placeholder="10-digit mobile"
              keyboardType="number-pad"
              maxLength={10}
              value={mobile}
              onChangeText={setMobile}
              error={err}
            />

            {showReferral ? (
              <Field
                testID="login-referral-input"
                label="Referral Code (optional)"
                labelColor="#D1D8E5"
                placeholder="e.g. NSA1B2C3"
                autoCapitalize="characters"
                value={referral}
                onChangeText={setReferral}
              />
            ) : (
              <Pressable testID="login-referral-toggle" onPress={() => setShowReferral(true)} style={{ marginBottom: Spacing.md }}>
                <Text style={{ color: "#C5A059", fontSize: 13, fontWeight: "600" }}>Have a referral code?</Text>
              </Pressable>
            )}

            <Button testID="login-send-otp-button" title="Send OTP" loading={loading} onPress={submit} />

            <View style={styles.dividerRow}>
              <View style={styles.divLine} />
              <Text style={styles.divTxt}>OR</Text>
              <View style={styles.divLine} />
            </View>

            <Pressable
              testID="login-google-button"
              onPress={async () => {
                setGoogleError("");
                await startGoogleLogin(referral.trim() || undefined);
              }}
              disabled={googleBusy}
              style={[styles.googleBtn, googleBusy && { opacity: 0.6 }]}
            >
              <Ionicons name="logo-google" size={20} color="#0B1B3D" />
              <Text style={styles.googleTxt}>{googleBusy ? "Connecting..." : "Continue with Google"}</Text>
            </Pressable>

            {!!googleError && (
              <Text testID="login-google-error" style={styles.googleError}>
                {googleError}
              </Text>
            )}

            <Text style={styles.hint}>By continuing, you agree to our Terms and Privacy Policy.</Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, padding: Spacing.xl, justifyContent: "center" },
  brandBlock: { alignItems: "center", marginBottom: Spacing.xxl },
  logo: {
    alignItems: "center",
    justifyContent: "center",
  },
  logoImage: {
    width: 116,
    height: 125,
  },
  title: { color: "#FDFDFD", fontSize: 30, fontWeight: "700", marginTop: Spacing.lg, fontFamily: "serif" },
  tagline: { color: "#C5A059", fontSize: 12, marginTop: 6, letterSpacing: 2, textTransform: "uppercase" },
  card: {
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 20,
    padding: Spacing.xl,
    borderWidth: 1,
    borderColor: "rgba(197,160,89,0.15)",
  },
  cardTitle: { color: "#FDFDFD", fontSize: 22, fontWeight: "700", marginBottom: 4 },
  cardSub: { color: "#A6B1C2", fontSize: 13, marginBottom: Spacing.lg },
  dividerRow: { flexDirection: "row", alignItems: "center", marginVertical: Spacing.lg },
  divLine: { flex: 1, height: StyleSheet.hairlineWidth, backgroundColor: "rgba(255,255,255,0.2)" },
  divTxt: { color: "#A6B1C2", fontSize: 12, marginHorizontal: Spacing.md, fontWeight: "600" },
  googleBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: Spacing.sm,
    minHeight: 52, borderRadius: 12, backgroundColor: "#FFFFFF",
  },
  googleTxt: { color: "#0B1B3D", fontSize: 16, fontWeight: "700" },
  googleError: {
    color: "#ff6b6b",
    fontSize: 12.5,
    textAlign: "center",
    marginTop: Spacing.sm,
    lineHeight: 18,
  },
  hint: { color: "#A6B1C2", fontSize: 11, textAlign: "center", marginTop: Spacing.lg },
});

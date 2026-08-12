import { useEffect, useRef, useState } from "react";
import { Image, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { useAuth } from "@/src/context/AuthContext";
import { useGoogleAuth } from "@/src/hooks/useGoogleAuth";
import {
  destroyFirebaseRecaptcha,
  firebaseConfigured as fbConfigured,
  firebaseEmailPasswordLogin,
  firebaseSendPhoneOtp,
} from "@/src/hooks/useFirebaseAuth";
import { Spacing } from "@/src/theme/tokens";

type Mode = "password" | "otp";

export default function Login() {
  const { signInPassword, signInOtp, firebaseExchange, loading } = useAuth();
  const { startGoogleLogin, googleBusy, googleError, setGoogleError } = useGoogleAuth();

  const [mode, setMode] = useState<Mode>("password");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [mobile, setMobile] = useState("");
  const [referral, setReferral] = useState("");
  const [showReferral, setShowReferral] = useState(false);
  const [err, setErr] = useState<string>();
  // Empty anchor element inside the Send OTP button wrapper where Firebase's
  // INVISIBLE reCAPTCHA widget renders (web only). reCAPTCHA requires the
  // container to be empty, and this anchor is invisible — no checkbox, no
  // badge, no visible container is ever rendered on the login page.
  const recaptchaAnchorRef = useRef<View | null>(null);

  // Destroy the invisible reCAPTCHA widget when leaving the login screen so no
  // stale widget/iframe is ever left behind.
  useEffect(() => () => destroyFirebaseRecaptcha(), []);

  const submitPassword = async () => {
    setErr(undefined);
    const id = identifier.trim();
    if (!id) {
      setErr("Enter your mobile number or email");
      return;
    }
    if (!password) {
      setErr("Enter your password");
      return;
    }
    // Firebase email/password is authoritative when the account exists in
    // Firebase. Legacy NyaySetu accounts (never created in Firebase) fall back
    // to the backend password check transparently.
    const isEmail = id.includes("@");
    if (isEmail && fbConfigured) {
      try {
        const fb = await firebaseEmailPasswordLogin(id, password);
        if (fb) {
          const { is_new } = await firebaseExchange(fb.idToken, referral.trim() || undefined);
          router.replace(is_new ? "/(auth)/onboarding" : "/(tabs)/home");
          return;
        }
      } catch (e: any) {
        const code = e?.code || "";
        if (code === "auth/user-not-found") {
          // Not a Firebase account — try the legacy NyaySetu password below.
        } else if (code === "auth/invalid-email") {
          setErr("Enter a valid email address.");
          return;
        } else if (code === "auth/invalid-credential" || code === "auth/wrong-password") {
          setErr("Invalid mobile/email or password.");
          return;
        } else {
          setErr(e?.message || "Invalid mobile/email or password.");
          return;
        }
      }
    }
    try {
      const { is_new } = await signInPassword(id, password, referral.trim() || undefined);
      router.replace(is_new ? "/(auth)/onboarding" : "/(tabs)/home");
    } catch (e: any) {
      setErr(e?.message || "Invalid mobile/email or password.");
    }
  };

  const submitOtp = async () => {
    setErr(undefined);
    const m = mobile.trim();
    if (!/^\d{10}$/.test(m)) {
      setErr("Enter a valid 10-digit mobile number");
      return;
    }
    // Firebase Phone Auth sends the SMS and verifies the OTP (invisible
    // reCAPTCHA behind the scenes, attached to the Send OTP button). On ANY
    // Firebase failure the widget is reset and we fall back to the existing
    // NyaySetu OTP flow so login keeps working.
    if (fbConfigured && Platform.OS === "web" && recaptchaAnchorRef.current) {
      try {
        await firebaseSendPhoneOtp(m, recaptchaAnchorRef.current as any);
        router.push({ pathname: "/(auth)/otp", params: { mobile: m, referral: referral.trim(), firebase: "1" } });
        return;
      } catch {
        // fall through to the existing OTP flow below
      }
    }
    try {
      await signInOtp(m);
      router.push({ pathname: "/(auth)/otp", params: { mobile: m, referral: referral.trim() } });
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const switchMode = (m: Mode) => {
    setMode(m);
    setErr(undefined);
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
            <Text style={styles.cardTitle}>Welcome Back</Text>
            <Text style={styles.cardSub}>Login to continue drafting court documents</Text>

            <View style={styles.modeRow}>
              {(["password", "otp"] as Mode[]).map((m) => (
                <Pressable
                  key={m}
                  testID={`login-mode-${m}`}
                  onPress={() => switchMode(m)}
                  style={[styles.modeTab, mode === m && styles.modeTabActive]}
                >
                  <Text style={[styles.modeTabTxt, mode === m && styles.modeTabTxtActive]}>
                    {m === "password" ? "Password" : "Use OTP"}
                  </Text>
                </Pressable>
              ))}
            </View>

            {mode === "password" ? (
              <>
                <Field
                  testID="login-identifier-input"
                  label="Mobile Number or Email"
                  labelColor="#D1D8E5"
                  placeholder="10-digit mobile or email"
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoCorrect={false}
                  value={identifier}
                  onChangeText={setIdentifier}
                />
                <View>
                  <Field
                    testID="login-password-input"
                    label="Password"
                    labelColor="#D1D8E5"
                    placeholder="Enter your password"
                    secureTextEntry={!showPassword}
                    autoCapitalize="none"
                    value={password}
                    onChangeText={setPassword}
                    error={err}
                  />
                  <Pressable
                    testID="login-show-password"
                    onPress={() => setShowPassword((v) => !v)}
                    style={styles.eyeBtn}
                    hitSlop={8}
                  >
                    <Ionicons name={showPassword ? "eye-off-outline" : "eye-outline"} size={20} color="#A6B1C2" />
                  </Pressable>
                </View>

                <Pressable
                  testID="login-forgot-password"
                  onPress={() => router.push("/(auth)/forgot-password")}
                  style={{ alignSelf: "flex-end", marginBottom: Spacing.md }}
                >
                  <Text style={{ color: "#C5A059", fontSize: 13, fontWeight: "600" }}>Forgot Password?</Text>
                </Pressable>

                <Button testID="login-password-button" title="Login" loading={loading} onPress={submitPassword} />

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
                  <Pressable testID="login-referral-toggle" onPress={() => setShowReferral(true)} style={{ marginTop: Spacing.md }}>
                    <Text style={{ color: "#C5A059", fontSize: 13, fontWeight: "600" }}>Have a referral code?</Text>
                  </Pressable>
                )}
              </>
            ) : (
              <>
                <Text style={styles.otpNote}>
                  Existing OTP accounts can still login with a mobile number and OTP.
                </Text>
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

                {/* The invisible Firebase reCAPTCHA widget renders inside the
                    empty anchor below (inside the Send OTP button wrapper) — no
                    CAPTCHA UI is ever shown to the user. */}
                <View style={styles.otpBtnWrap}>
                  <Button testID="login-send-otp-button" title="Send OTP" loading={loading} onPress={submitOtp} />
                  {fbConfigured && Platform.OS === "web" && (
                    <View ref={recaptchaAnchorRef as any} style={styles.recaptchaAnchor} collapsable={false} />
                  )}
                </View>
              </>
            )}

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

            <Pressable
              testID="login-create-account"
              onPress={() => router.push("/(auth)/signup")}
              style={{ marginTop: Spacing.lg, alignItems: "center" }}
            >
              <Text style={{ color: "#A6B1C2", fontSize: 13 }}>
                Don't have an account?{" "}
                <Text style={{ color: "#C5A059", fontWeight: "700" }}>Create Account</Text>
              </Text>
            </Pressable>

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
  modeRow: {
    flexDirection: "row",
    backgroundColor: "rgba(255,255,255,0.08)",
    borderRadius: 10,
    padding: 3,
    marginBottom: Spacing.lg,
  },
  modeTab: { flex: 1, alignItems: "center", paddingVertical: 8, borderRadius: 8 },
  modeTabActive: { backgroundColor: "#C5A059" },
  modeTabTxt: { color: "#A6B1C2", fontSize: 13, fontWeight: "600" },
  modeTabTxtActive: { color: "#0B1B3D", fontWeight: "700" },
  otpNote: { color: "#A6B1C2", fontSize: 12.5, marginBottom: Spacing.md, lineHeight: 18 },
  eyeBtn: { position: "absolute", right: 12, top: 42 },
  otpBtnWrap: { position: "relative" },
  // Empty, off-screen anchor for the INVISIBLE reCAPTCHA widget. Must remain
  // empty (reCAPTCHA render() requires an empty container) and is never
  // visible — no checkbox, badge, or CAPTCHA card appears on the page.
  recaptchaAnchor: { position: "absolute", left: -9999, top: -9999, width: 1, height: 1, opacity: 0, overflow: "hidden", pointerEvents: "none" },
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

import { useEffect, useRef, useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router, useLocalSearchParams } from "expo-router";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { api } from "@/src/api/client";
import {
  destroyFirebaseRecaptcha,
  firebaseConfirmPasswordReset,
  firebaseConfirmPhoneOtp,
  firebaseEmailPasswordLogin,
  firebaseSendPasswordReset,
  firebaseSendPhoneOtp,
  firebaseVerifyPasswordResetCode,
  getPendingPhoneConfirmation,
  isFirebaseConfigured,
} from "@/src/hooks/useFirebaseAuth";
import { Spacing } from "@/src/theme/tokens";

type RecoveryMethod = "mobile" | "email";

export default function ForgotPassword() {
  const params = useLocalSearchParams<{ mode?: string; oobCode?: string; email?: string }>();
  const actionCode = params?.oobCode || "";
  const isActionReset = params?.mode === "resetPassword" || !!actionCode;

  // Active mode tab: "mobile" or "email"
  const [method, setMethod] = useState<RecoveryMethod>(params?.email?.includes("@") ? "email" : "mobile");

  // Mobile State
  const [mobile, setMobile] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [mobileBusy, setMobileBusy] = useState(false);
  const [mobileErr, setMobileErr] = useState<string>();
  const [mobileStepErr, setMobileStepErr] = useState<string>();
  const [mobileCooldown, setMobileCooldown] = useState(0);
  const mobileCooldownEndRef = useRef<number>(0);

  // Email State
  const [email, setEmail] = useState(params?.email || "");
  const [emailSent, setEmailSent] = useState(false);
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailErr, setEmailErr] = useState<string>();
  const [emailCooldown, setEmailCooldown] = useState(0);
  const emailCooldownEndRef = useRef<number>(0);

  // Completed / Success State
  const [done, setDone] = useState(false);
  const [doneMessage, setDoneMessage] = useState("Password reset successfully. Please login with your new password.");

  // Direct action code (oobCode) state
  const [actionVerifiedEmail, setActionVerifiedEmail] = useState<string>("");
  const [actionVerifying, setActionVerifying] = useState(isActionReset);
  const [actionError, setActionError] = useState<string>();

  // Invisible reCAPTCHA container for Web
  const recaptchaAnchorRef = useRef<View | null>(null);

  // Centralized, robust 1-second interval timer for cooldowns
  useEffect(() => {
    const timer = setInterval(() => {
      const now = Date.now();
      if (mobileCooldownEndRef.current > 0) {
        const rem = Math.max(0, Math.ceil((mobileCooldownEndRef.current - now) / 1000));
        setMobileCooldown(rem);
        if (rem <= 0) {
          mobileCooldownEndRef.current = 0;
        }
      }
      if (emailCooldownEndRef.current > 0) {
        const rem = Math.max(0, Math.ceil((emailCooldownEndRef.current - now) / 1000));
        setEmailCooldown(rem);
        if (rem <= 0) {
          emailCooldownEndRef.current = 0;
        }
      }
    }, 1000);

    return () => {
      clearInterval(timer);
      destroyFirebaseRecaptcha();
    };
  }, []);

  // Verify actionCode if user opened the page from an email reset link
  useEffect(() => {
    if (!actionCode) return;
    let mounted = true;
    (async () => {
      try {
        const verifiedEmail = await firebaseVerifyPasswordResetCode(actionCode);
        if (mounted && verifiedEmail) {
          setActionVerifiedEmail(verifiedEmail);
        }
      } catch (e: any) {
        if (mounted) {
          setActionError("This password reset link is invalid or has expired. Please request a new reset email.");
        }
      } finally {
        if (mounted) setActionVerifying(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [actionCode]);

  // -------------------------------------------------------------
  // A) EMAIL FORGOT PASSWORD HANDLERS
  // -------------------------------------------------------------
  const handleSendEmailReset = async () => {
    if (emailBusy || emailCooldown > 0) return;
    setEmailErr(undefined);

    const targetEmail = email.trim();
    if (!targetEmail || !/\S+@\S+\.\S+/.test(targetEmail)) {
      setEmailErr("Please enter a valid email address.");
      return;
    }

    setEmailBusy(true);
    try {
      if (isFirebaseConfigured()) {
        try {
          await firebaseSendPasswordReset(targetEmail);
        } catch (fbErr: any) {
          const code = fbErr?.code || "";
          if (code === "auth/user-not-found" || code === "auth/invalid-credential") {
            // Requirement A.4: Do NOT reveal whether the email exists. Show generic success!
          } else if (code === "auth/too-many-requests") {
            setEmailErr("Too many reset requests. Please wait a few minutes and try again.");
            setEmailBusy(false);
            return;
          } else if (code === "auth/invalid-email") {
            setEmailErr("Please enter a valid email address.");
            setEmailBusy(false);
            return;
          } else {
            setEmailErr(fbErr?.message || "Could not send reset email. Please try again.");
            setEmailBusy(false);
            return;
          }
        }
      } else {
        // Fallback for dev mode
        await api.forgotPasswordEmail(targetEmail);
      }

      // Success: start 30s cooldown
      emailCooldownEndRef.current = Date.now() + 30000;
      setEmailCooldown(30);
      setEmailSent(true);
    } catch (err: any) {
      setEmailErr(err?.message || "Could not send reset email. Please try again.");
    } finally {
      setEmailBusy(false);
    }
  };

  const handleResendEmailReset = async () => {
    if (emailBusy || emailCooldown > 0) return;
    setEmailErr(undefined);

    const targetEmail = email.trim();
    if (!targetEmail) return;

    setEmailBusy(true);
    try {
      if (isFirebaseConfigured()) {
        try {
          await firebaseSendPasswordReset(targetEmail);
        } catch (fbErr: any) {
          const code = fbErr?.code || "";
          if (code === "auth/user-not-found" || code === "auth/invalid-credential") {
            // Generic success - do not reveal
          } else if (code === "auth/too-many-requests") {
            setEmailErr("Too many reset requests. Please wait a few minutes and try again.");
            setEmailBusy(false);
            return;
          } else {
            setEmailErr(fbErr?.message || "Failed to resend reset email. Please try again.");
            setEmailBusy(false);
            return;
          }
        }
      } else {
        await api.forgotPasswordEmail(targetEmail);
      }

      // Restart 30-second cooldown
      emailCooldownEndRef.current = Date.now() + 30000;
      setEmailCooldown(30);
    } catch (err: any) {
      setEmailErr(err?.message || "Failed to resend reset email. Please try again.");
    } finally {
      setEmailBusy(false);
    }
  };

  // -------------------------------------------------------------
  // B) MOBILE OTP FORGOT PASSWORD HANDLERS
  // -------------------------------------------------------------
  const handleSendMobileOtp = async () => {
    if (mobileBusy || mobileCooldown > 0) return;
    setMobileErr(undefined);

    const m = mobile.trim();
    if (!/^\d{10}$/.test(m)) {
      setMobileErr("Enter a valid 10-digit mobile number");
      return;
    }

    setMobileBusy(true);
    try {
      if (isFirebaseConfigured()) {
        if (Platform.OS === "web" && recaptchaAnchorRef.current) {
          await firebaseSendPhoneOtp(m, recaptchaAnchorRef.current as any);
        } else {
          await firebaseSendPhoneOtp(m, null);
        }
      } else {
        await api.forgotPasswordMobile(m);
      }

      // Success: start 30s cooldown and show OTP form
      mobileCooldownEndRef.current = Date.now() + 30000;
      setMobileCooldown(30);
      setOtpSent(true);
    } catch (e: any) {
      const code = e?.code as string | undefined;
      if (code === "auth/operation-not-allowed" || code === "auth/unauthorized-continue-uri") {
        setMobileErr("SMS OTP is temporarily unavailable for this region. Please try email reset.");
      } else if (code === "auth/too-many-requests") {
        setMobileErr("Too many OTP requests. Please wait a minute and try again.");
      } else if (code === "auth/invalid-phone-number") {
        setMobileErr("Enter a valid 10-digit mobile number.");
      } else if (code === "auth/quota-exceeded") {
        setMobileErr("SMS quota exceeded for today. Please use email reset or contact support.");
      } else {
        setMobileErr(e?.message || "Could not send OTP. Please try again.");
      }
    } finally {
      setMobileBusy(false);
    }
  };

  const handleResendMobileOtp = async () => {
    if (mobileBusy || mobileCooldown > 0) return;
    setMobileStepErr(undefined);

    const m = mobile.trim();
    if (!/^\d{10}$/.test(m)) return;

    setMobileBusy(true);
    try {
      if (isFirebaseConfigured()) {
        if (Platform.OS === "web" && recaptchaAnchorRef.current) {
          await firebaseSendPhoneOtp(m, recaptchaAnchorRef.current as any);
        } else {
          await firebaseSendPhoneOtp(m, null);
        }
      } else {
        await api.forgotPasswordMobile(m);
      }

      // Restart 30-second cooldown on successful resend
      mobileCooldownEndRef.current = Date.now() + 30000;
      setMobileCooldown(30);
    } catch (e: any) {
      const code = e?.code as string | undefined;
      if (code === "auth/too-many-requests") {
        setMobileStepErr("Too many OTP requests. Please wait a minute and try again.");
      } else {
        setMobileStepErr(e?.message || "Could not resend OTP. Please try again.");
      }
    } finally {
      setMobileBusy(false);
    }
  };

  const handleResetMobilePassword = async () => {
    setMobileStepErr(undefined);
    if (!/^\d{6}$/.test(otp.trim())) {
      setMobileStepErr("Enter the 6-digit OTP");
      return;
    }
    if (password.length < 8) {
      setMobileStepErr("Password must be at least 8 characters");
      return;
    }
    if (password !== confirm) {
      setMobileStepErr("Passwords do not match");
      return;
    }

    setMobileBusy(true);
    try {
      if (isFirebaseConfigured()) {
        const confirmation = getPendingPhoneConfirmation();
        if (!confirmation) {
          setMobileStepErr("OTP session expired. Please go back and request a new OTP.");
          setMobileBusy(false);
          return;
        }

        let idToken: string;
        try {
          idToken = await firebaseConfirmPhoneOtp(confirmation, otp.trim());
        } catch (e: any) {
          const code = e?.code || "";
          if (code === "auth/invalid-verification-code") {
            setMobileStepErr("Invalid OTP. Please check the code and try again.");
          } else if (code === "auth/code-expired") {
            setMobileStepErr("OTP expired. Please go back and request a new OTP.");
          } else {
            setMobileStepErr(e?.message || "Failed to verify OTP. Please try again.");
          }
          setMobileBusy(false);
          return;
        }

        await api.resetPasswordWithFirebase(idToken, password);
      } else {
        await api.resetPassword(mobile.trim(), otp.trim(), password);
      }

      setDoneMessage("Password reset successfully. Please login with your new password.");
      setDone(true);
    } catch (e: any) {
      setMobileStepErr(e?.message || "Password reset failed. Please try again.");
    } finally {
      setMobileBusy(false);
    }
  };

  // -------------------------------------------------------------
  // C) DIRECT ACTION CODE (OOBCODE) PASSWORD RESET
  // -------------------------------------------------------------
  const handleResetWithActionCode = async () => {
    setActionError(undefined);
    if (password.length < 8) {
      setActionError("Password must be at least 8 characters");
      return;
    }
    if (password !== confirm) {
      setActionError("Passwords do not match");
      return;
    }

    setMobileBusy(true);
    try {
      await firebaseConfirmPasswordReset(actionCode, password);

      // Opportunistically log in to get a verified ID token to sync backend password & bump token_version
      if (actionVerifiedEmail) {
        try {
          const cred = await firebaseEmailPasswordLogin(actionVerifiedEmail, password);
          if (cred?.idToken) {
            await api.resetPasswordWithFirebase(cred.idToken, password);
          }
        } catch (syncErr) {
          console.warn("[forgot-password] Syncing backend password after reset notice:", syncErr);
        }
      }

      setDoneMessage("Your password has been reset successfully. Please login with your new password.");
      setDone(true);
    } catch (e: any) {
      const code = e?.code || "";
      if (code === "auth/invalid-action-code" || code === "auth/expired-action-code") {
        setActionError("This password reset link is invalid or has expired. Please request a new one.");
      } else if (code === "auth/weak-password") {
        setActionError("Password must be at least 8 characters.");
      } else {
        setActionError(e?.message || "Could not reset password. Please try again.");
      }
    } finally {
      setMobileBusy(false);
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
              <Image
                source={Platform.OS === "web" ? "/logo.webp" : require("../../assets/images/logo.png")}
                style={styles.logoImage}
                contentFit="contain"
                accessibilityLabel="NyaySetu Pro Logo"
              />
            </View>
            <Text style={styles.title}>NyaySetu Pro</Text>
            <Text style={styles.tagline}>The New Era of Advocacy</Text>
          </View>

          <View style={styles.card}>
            {/* SUCCESS STATE */}
            {done ? (
              <>
                <Ionicons name="checkmark-circle" size={56} color="#4CAF50" style={{ alignSelf: "center", marginBottom: Spacing.md }} />
                <Text style={styles.cardTitle}>Password Reset</Text>
                <Text style={styles.cardSub}>{doneMessage}</Text>
                <Button
                  testID="forgot-go-login"
                  title="Go to Login"
                  onPress={() => router.replace("/(auth)/login")}
                />
              </>
            ) : isActionReset ? (
              /* ACTION LINK / OOBCODE RESET STATE */
              <>
                <Text style={styles.cardTitle}>Set New Password</Text>
                <Text style={styles.cardSub}>
                  {actionVerifying
                    ? "Verifying reset link..."
                    : actionVerifiedEmail
                    ? `Create a new password for ${actionVerifiedEmail}.`
                    : "Create a new password for your account."}
                </Text>

                {actionError && (
                  <View style={styles.errorBox}>
                    <Ionicons name="alert-circle" size={18} color="#FF6B6B" />
                    <Text style={styles.errorBoxText}>{actionError}</Text>
                  </View>
                )}

                {!actionVerifying && !actionError && (
                  <>
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

                    <Button
                      testID="forgot-reset-button"
                      title="Update Password"
                      loading={mobileBusy}
                      onPress={handleResetWithActionCode}
                    />
                  </>
                )}
              </>
            ) : (
              /* NORMAL FORGOT PASSWORD FORM (TABS: MOBILE vs EMAIL) */
              <>
                <Text style={styles.cardTitle}>Forgot Password</Text>
                <Text style={styles.cardSub}>
                  Choose your preferred recovery method to restore access to your account.
                </Text>

                {/* SEGMENTED TAB SELECTOR (Hidden once OTP or Email is sent) */}
                {!otpSent && !emailSent && (
                  <View style={styles.tabContainer}>
                    <Pressable
                      testID="forgot-tab-mobile"
                      style={[styles.tabBtn, method === "mobile" && styles.tabBtnActive]}
                      onPress={() => {
                        setMethod("mobile");
                        setMobileErr(undefined);
                        setEmailErr(undefined);
                      }}
                    >
                      <Ionicons
                        name="call-outline"
                        size={16}
                        color={method === "mobile" ? "#0B1B3D" : "#A6B1C2"}
                      />
                      <Text style={[styles.tabText, method === "mobile" && styles.tabTextActive]}>
                        Mobile OTP
                      </Text>
                    </Pressable>

                    <Pressable
                      testID="forgot-tab-email"
                      style={[styles.tabBtn, method === "email" && styles.tabBtnActive]}
                      onPress={() => {
                        setMethod("email");
                        setMobileErr(undefined);
                        setEmailErr(undefined);
                      }}
                    >
                      <Ionicons
                        name="mail-outline"
                        size={16}
                        color={method === "email" ? "#0B1B3D" : "#A6B1C2"}
                      />
                      <Text style={[styles.tabText, method === "email" && styles.tabTextActive]}>
                        Email Reset
                      </Text>
                    </Pressable>
                  </View>
                )}

                {/* ================= METHOD 1: MOBILE OTP ================= */}
                {method === "mobile" && (
                  !otpSent ? (
                    <>
                      <Field
                        testID="forgot-mobile-input"
                        label="Registered Mobile Number"
                        labelColor="#D1D8E5"
                        placeholder="10-digit mobile number"
                        keyboardType="phone-pad"
                        maxLength={10}
                        value={mobile}
                        onChangeText={setMobile}
                        error={mobileErr}
                      />
                      <View style={{ position: "relative" }}>
                        <Button
                          testID="forgot-send-otp-button"
                          title="Send OTP"
                          loading={mobileBusy}
                          onPress={handleSendMobileOtp}
                        />
                        <View ref={recaptchaAnchorRef as any} style={styles.recaptchaAnchor} collapsable={false} />
                      </View>
                    </>
                  ) : (
                    <>
                      <Text style={styles.noticeText}>
                        OTP sent to <Text style={{ color: "#FDFDFD", fontWeight: "700" }}>+91 {mobile}</Text>. Enter the code and set your new password.
                      </Text>

                      <Field
                        testID="forgot-otp-input"
                        label="6-Digit OTP"
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
                          error={mobileStepErr}
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

                      <Button
                        testID="forgot-reset-button"
                        title="Reset Password"
                        loading={mobileBusy}
                        onPress={handleResetMobilePassword}
                      />

                      {/* MOBILE RESEND SECTION WITH 30s COOLDOWN */}
                      <View style={styles.resendBlock}>
                        <Text style={styles.resendPrompt}>Didn't receive the OTP?</Text>
                        {mobileCooldown > 0 ? (
                          <View style={[styles.resendBtn, styles.resendBtnDisabled]} testID="forgot-resend-otp-disabled">
                            <Ionicons name="time-outline" size={15} color="#8A9BB3" />
                            <Text style={styles.resendTextDisabled}>Resend OTP in {mobileCooldown}s</Text>
                          </View>
                        ) : (
                          <Pressable
                            testID="forgot-resend-otp-button"
                            onPress={handleResendMobileOtp}
                            disabled={mobileBusy}
                            style={({ pressed }) => [styles.resendBtn, pressed && { opacity: 0.7 }]}
                          >
                            <Ionicons name="refresh-outline" size={15} color="#C5A059" />
                            <Text style={styles.resendTextActive}>Resend OTP</Text>
                          </Pressable>
                        )}
                        <Pressable
                          onPress={() => {
                            setOtpSent(false);
                            setOtp("");
                            setMobileStepErr(undefined);
                          }}
                          style={{ marginTop: 8 }}
                        >
                          <Text style={styles.changeMethodText}>Change mobile number</Text>
                        </Pressable>
                      </View>
                    </>
                  )
                )}

                {/* ================= METHOD 2: EMAIL RESET ================= */}
                {method === "email" && (
                  !emailSent ? (
                    <>
                      <Field
                        testID="forgot-email-input"
                        label="Registered Email Address"
                        labelColor="#D1D8E5"
                        placeholder="advocate@example.com"
                        keyboardType="email-address"
                        autoCapitalize="none"
                        value={email}
                        onChangeText={setEmail}
                        error={emailErr}
                      />
                      <Button
                        testID="forgot-send-email-button"
                        title="Send Reset Email"
                        loading={emailBusy}
                        onPress={handleSendEmailReset}
                      />
                    </>
                  ) : (
                    <>
                      <View style={styles.emailSentCard}>
                        <Ionicons name="mail-unread-outline" size={48} color="#C5A059" style={{ alignSelf: "center", marginBottom: Spacing.sm }} />
                        <Text style={styles.emailSentTitle}>Reset Email Sent</Text>
                        <Text style={styles.emailSentSub}>
                          If an account exists for <Text style={{ color: "#FDFDFD", fontWeight: "700" }}>{email.trim()}</Text>, a password reset link has been sent to your inbox.
                        </Text>
                      </View>

                      {emailErr && (
                        <Text style={[styles.noticeText, { color: "#FF6B6B", marginBottom: 12 }]}>
                          {emailErr}
                        </Text>
                      )}

                      {/* EMAIL RESEND SECTION WITH 30s COOLDOWN */}
                      <View style={styles.resendBlock}>
                        <Text style={styles.resendPrompt}>Didn't receive the email?</Text>
                        <Text style={styles.resendHint}>Be sure to check your spam or junk folder.</Text>

                        {emailCooldown > 0 ? (
                          <View style={[styles.resendBtn, styles.resendBtnDisabled]} testID="forgot-resend-email-disabled">
                            <Ionicons name="time-outline" size={15} color="#8A9BB3" />
                            <Text style={styles.resendTextDisabled}>Resend available in {emailCooldown}s</Text>
                          </View>
                        ) : (
                          <Button
                            testID="forgot-resend-email-button"
                            title="Resend Reset Email"
                            loading={emailBusy}
                            onPress={handleResendEmailReset}
                            variant="secondary"
                            style={{ marginTop: 8 }}
                          />
                        )}

                        <Pressable
                          onPress={() => {
                            setEmailSent(false);
                            setEmailErr(undefined);
                          }}
                          style={{ marginTop: 12 }}
                        >
                          <Text style={styles.changeMethodText}>Try a different email</Text>
                        </Pressable>
                      </View>
                    </>
                  )
                )}
              </>
            )}

            <Pressable
              testID="forgot-back-login"
              onPress={() => router.replace("/(auth)/login")}
              style={{ marginTop: Spacing.lg, alignItems: "center" }}
            >
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
  tabContainer: {
    flexDirection: "row",
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 12,
    padding: 4,
    marginBottom: Spacing.lg,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  tabBtn: {
    flex: 1,
    paddingVertical: 10,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 9,
    flexDirection: "row",
    gap: 6,
  },
  tabBtnActive: {
    backgroundColor: "#C5A059",
  },
  tabText: {
    color: "#A6B1C2",
    fontSize: 13,
    fontWeight: "600",
  },
  tabTextActive: {
    color: "#0B1B3D",
    fontWeight: "700",
  },
  noticeText: {
    color: "#A6B1C2",
    fontSize: 13,
    lineHeight: 18,
    marginBottom: Spacing.md,
  },
  resendBlock: {
    marginTop: Spacing.lg,
    paddingTop: Spacing.md,
    borderTopWidth: 1,
    borderTopColor: "rgba(255,255,255,0.08)",
    alignItems: "center",
  },
  resendPrompt: {
    color: "#D1D8E5",
    fontSize: 13,
    fontWeight: "600",
    marginBottom: 4,
  },
  resendHint: {
    color: "#8A9BB3",
    fontSize: 12,
    marginBottom: 6,
  },
  resendBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
  },
  resendBtnDisabled: {
    backgroundColor: "rgba(255,255,255,0.04)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  resendTextDisabled: {
    color: "#8A9BB3",
    fontSize: 13,
    fontWeight: "600",
  },
  resendTextActive: {
    color: "#C5A059",
    fontSize: 13,
    fontWeight: "700",
  },
  changeMethodText: {
    color: "#8A9BB3",
    fontSize: 12,
    textDecorationLine: "underline",
  },
  emailSentCard: {
    backgroundColor: "rgba(197,160,89,0.08)",
    borderRadius: 14,
    padding: Spacing.lg,
    borderWidth: 1,
    borderColor: "rgba(197,160,89,0.25)",
    marginBottom: Spacing.md,
    alignItems: "center",
  },
  emailSentTitle: {
    color: "#FDFDFD",
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 4,
  },
  emailSentSub: {
    color: "#D1D8E5",
    fontSize: 13,
    lineHeight: 19,
    textAlign: "center",
  },
  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "rgba(255, 107, 107, 0.12)",
    padding: Spacing.md,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "rgba(255, 107, 107, 0.3)",
    marginBottom: Spacing.md,
  },
  errorBoxText: {
    color: "#FF6B6B",
    fontSize: 13,
    flex: 1,
    lineHeight: 18,
  },
  eyeBtn: { position: "absolute", right: 12, top: 42 },
  recaptchaAnchor: { position: "absolute", opacity: 0, height: 0, width: 0 },
});

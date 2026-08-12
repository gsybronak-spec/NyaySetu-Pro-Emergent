import { useState } from "react";
import { Image, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { router, useLocalSearchParams } from "expo-router";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { useAuth } from "@/src/context/AuthContext";
import {
  firebaseConfirmPhoneOtp,
  getPendingPhoneConfirmation,
} from "@/src/hooks/useFirebaseAuth";
import { Spacing } from "@/src/theme/tokens";

export default function Otp() {
  const { mobile, referral, firebase } = useLocalSearchParams<{ mobile: string; referral?: string; firebase?: string }>();
  const { verifyOtp, firebaseExchange, loading } = useAuth();
  const [otp, setOtp] = useState("");
  const [err, setErr] = useState<string>();

  const submit = async () => {
    setErr(undefined);
    if (!/^\d{6}$/.test(otp)) {
      setErr("Enter the 6-digit OTP");
      return;
    }
    try {
      // Firebase phone-auth OTP: confirm with Firebase, exchange the ID token.
      if (firebase === "1") {
        const confirmation = getPendingPhoneConfirmation();
        if (!confirmation) {
          setErr("OTP session expired. Please go back and request a new OTP.");
          return;
        }
        const idToken = await firebaseConfirmPhoneOtp(confirmation, otp);
        const { is_new } = await firebaseExchange(idToken, referral ? String(referral) : undefined);
        router.replace(is_new ? "/(auth)/onboarding" : "/(tabs)/home");
        return;
      }
      const { is_new } = await verifyOtp(String(mobile), otp, referral ? String(referral) : undefined);
      router.replace(is_new ? "/(auth)/onboarding" : "/(tabs)/home");
    } catch (e: any) {
      setErr(e.message);
    }
  };

  return (
    <LinearGradient colors={["#061024", "#0B1B3D"]} style={{ flex: 1 }}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
          <View style={styles.logo}>
            <Image source={require("../../assets/images/logo.png")} style={styles.logoImage} resizeMode="contain" />
          </View>
          <Text style={styles.title}>Verify OTP</Text>
          <Text style={styles.sub}>
            We've sent a 6-digit code to {"\n"}
            <Text style={{ color: "#FDFDFD", fontWeight: "700" }}>+91 {mobile}</Text>
          </Text>

          <View style={styles.card}>
            <Field
              testID="otp-input"
              label="Enter OTP"
              labelColor="#D1D8E5"
              placeholder="123456"
              keyboardType="number-pad"
              maxLength={6}
              value={otp}
              onChangeText={setOtp}
              error={err}
            />
            <Button testID="otp-verify-button" title="Verify & Continue" loading={loading} onPress={submit} />
            <Text style={styles.hint}>For testing use OTP: 123456</Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, padding: Spacing.xl, justifyContent: "center" },
  logo: {
    alignSelf: "center",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: Spacing.lg,
  },
  logoImage: {
    width: 92,
    height: 99,
  },
  title: { color: "#FDFDFD", fontSize: 26, fontWeight: "700", textAlign: "center", fontFamily: "serif" },
  sub: { color: "#A6B1C2", fontSize: 14, textAlign: "center", marginTop: 6, marginBottom: Spacing.xl },
  card: {
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 20,
    padding: Spacing.xl,
    borderWidth: 1,
    borderColor: "rgba(197,160,89,0.15)",
  },
  hint: { color: "#C5A059", fontSize: 12, textAlign: "center", marginTop: Spacing.md },
});

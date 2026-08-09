import { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { useAuth } from "@/src/context/AuthContext";
import { Spacing } from "@/src/theme/tokens";

export default function Login() {
  const [mobile, setMobile] = useState("");
  const [err, setErr] = useState<string>();
  const { signInOtp, loading } = useAuth();

  const submit = async () => {
    setErr(undefined);
    const m = mobile.trim();
    if (!/^\d{10}$/.test(m)) {
      setErr("Enter a valid 10-digit mobile number");
      return;
    }
    try {
      await signInOtp(m);
      router.push({ pathname: "/(auth)/otp", params: { mobile: m } });
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
              <Ionicons name="scale" size={44} color="#C5A059" />
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

            <Button testID="login-send-otp-button" title="Send OTP" loading={loading} onPress={submit} />
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
    width: 84,
    height: 84,
    borderRadius: 22,
    backgroundColor: "rgba(197,160,89,0.12)",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "rgba(197,160,89,0.35)",
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
  hint: { color: "#A6B1C2", fontSize: 11, textAlign: "center", marginTop: Spacing.lg },
});

import React, { useState } from "react";
import {
  StyleSheet,
  Text,
  TextInput,
  View,
  Pressable,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useAdminAuth } from "@/src/context/AdminAuthContext";

export function AdminLoginView() {
  const { signIn, loading } = useAdminAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!email.trim()) {
      setErrorMsg("Please enter your Super Admin email address.");
      return;
    }
    if (!password) {
      setErrorMsg("Please enter your password.");
      return;
    }

    setErrorMsg(null);
    try {
      const admin = await signIn(email.trim(), password);
      if (admin.role !== "super_admin") {
        setErrorMsg("Access denied. Super Administrator privileges required.");
        return;
      }
      router.replace("/admin/dashboard" as any);
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to sign in. Please verify your credentials.");
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: "#061024" }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        {/* Card */}
        <View style={styles.card}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.badge}>
              <Ionicons name="shield-half-outline" size={28} color="#C5A059" />
            </View>
            <Text style={styles.title}>
              NyaySetu <Text style={{ color: "#C5A059" }}>Pro</Text>
            </Text>
            <Text style={styles.subtitle}>SUPER ADMIN CONTROL CENTER</Text>
            <Text style={styles.description}>
              Sign in with your administrative credentials to manage platform users, templates, cases, and system configurations.
            </Text>
          </View>

          {/* Error Banner */}
          {errorMsg ? (
            <View style={styles.errorBox}>
              <Ionicons name="alert-circle" size={18} color="#E53E3E" style={{ marginRight: 8 }} />
              <Text style={styles.errorText}>{errorMsg}</Text>
            </View>
          ) : null}

          {/* Form */}
          <View style={styles.form}>
            <View style={styles.field}>
              <Text style={styles.label}>Admin Email</Text>
              <View style={styles.inputWrapper}>
                <Ionicons name="mail-outline" size={18} color="#8B96A9" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="admin@nyaysetu.gov.in"
                  placeholderTextColor="#6B7280"
                  value={email}
                  onChangeText={(val) => {
                    setEmail(val);
                    if (errorMsg) setErrorMsg(null);
                  }}
                  autoCapitalize="none"
                  keyboardType="email-address"
                  autoComplete="email"
                />
              </View>
            </View>

            <View style={styles.field}>
              <Text style={styles.label}>Password</Text>
              <View style={styles.inputWrapper}>
                <Ionicons name="lock-closed-outline" size={18} color="#8B96A9" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="Enter administrator password"
                  placeholderTextColor="#6B7280"
                  value={password}
                  onChangeText={(val) => {
                    setPassword(val);
                    if (errorMsg) setErrorMsg(null);
                  }}
                  secureTextEntry={!showPassword}
                  autoCapitalize="none"
                />
                <Pressable
                  onPress={() => setShowPassword(!showPassword)}
                  style={styles.eyeBtn}
                >
                  <Ionicons
                    name={showPassword ? "eye-off-outline" : "eye-outline"}
                    size={18}
                    color="#8B96A9"
                  />
                </Pressable>
              </View>
            </View>

            {/* Submit */}
            <Pressable
              disabled={loading}
              onPress={handleSubmit}
              style={({ pressed }) => [
                styles.submitBtn,
                pressed && { opacity: 0.85 },
                loading && { opacity: 0.7 },
              ]}
            >
              {loading ? (
                <ActivityIndicator size="small" color="#061024" style={{ marginRight: 8 }} />
              ) : (
                <Ionicons name="log-in-outline" size={18} color="#061024" style={{ marginRight: 8 }} />
              )}
              <Text style={styles.submitBtnText}>
                {loading ? "Authenticating..." : "Access Control Center"}
              </Text>
            </Pressable>
          </View>

          {/* Security Notice */}
          <View style={styles.footerNote}>
            <Ionicons name="lock-closed" size={12} color="#6B7280" style={{ marginRight: 4 }} />
            <Text style={styles.footerNoteText}>
              Restricted Area. All administrative actions are recorded in immutable audit logs.
            </Text>
          </View>
        </View>

        {/* Back to Client */}
        <Pressable
          onPress={() => router.push("/(tabs)/home" as any)}
          style={styles.backBtn}
        >
          <Ionicons name="arrow-back" size={16} color="#8B96A9" style={{ marginRight: 6 }} />
          <Text style={styles.backBtnText}>Return to Lawyer Application</Text>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    minHeight: "100%",
    backgroundColor: "#061024",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  card: {
    backgroundColor: "#0B1B3D",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#1B2A49",
    width: "100%",
    maxWidth: 440,
    padding: 32,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.4,
    shadowRadius: 20,
    elevation: 8,
  },
  header: {
    alignItems: "center",
    marginBottom: 24,
  },
  badge: {
    width: 56,
    height: 56,
    borderRadius: 16,
    backgroundColor: "rgba(197, 160, 89, 0.15)",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: "800",
    color: "#FDFDFD",
    fontFamily: "serif",
    letterSpacing: -0.3,
  },
  subtitle: {
    fontSize: 10,
    fontWeight: "800",
    color: "#C5A059",
    letterSpacing: 1.2,
    marginTop: 4,
  },
  description: {
    fontSize: 12,
    color: "#8B96A9",
    textAlign: "center",
    marginTop: 10,
    lineHeight: 18,
  },
  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(229, 62, 62, 0.12)",
    borderWidth: 1,
    borderColor: "rgba(229, 62, 62, 0.3)",
    borderRadius: 8,
    padding: 12,
    marginBottom: 20,
  },
  errorText: {
    flex: 1,
    fontSize: 12,
    color: "#F56565",
    fontWeight: "500",
  },
  form: {
    gap: 18,
  },
  field: {
    gap: 6,
  },
  label: {
    fontSize: 12,
    fontWeight: "700",
    color: "#D1D8E5",
    letterSpacing: 0.3,
  },
  inputWrapper: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#12203B",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#253452",
    paddingHorizontal: 12,
    height: 44,
  },
  inputIcon: {
    marginRight: 10,
  },
  input: {
    flex: 1,
    color: "#FDFDFD",
    fontSize: 14,
    height: "100%",
  },
  eyeBtn: {
    padding: 6,
  },
  submitBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#C5A059",
    borderRadius: 10,
    height: 44,
    marginTop: 6,
  },
  submitBtnText: {
    fontSize: 14,
    fontWeight: "800",
    color: "#061024",
  },
  footerNote: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 24,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: "#162544",
  },
  footerNoteText: {
    fontSize: 11,
    color: "#6B7280",
    textAlign: "center",
    flex: 1,
  },
  backBtn: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 20,
    padding: 8,
  },
  backBtnText: {
    fontSize: 13,
    color: "#8B96A9",
    fontWeight: "500",
  },
});

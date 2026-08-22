import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";

import { Button } from "@/src/components/Button";
import { Field } from "@/src/components/Field";
import { Dropdown } from "@/src/components/Dropdown";
import { useAuth } from "@/src/context/AuthContext";
import { useTheme } from "@/src/theme/ThemeContext";
import { useResponsive } from "@/src/hooks/useResponsive";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";

const USER_ROLES = ["Advocate", "Legal Professional", "Law Student", "Other"] as const;
const GENDERS = ["Male", "Female", "Other"] as const;

interface ProfileFormProps {
  mode: "onboarding" | "edit";
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function ProfileForm({ mode, onSuccess, onCancel }: ProfileFormProps) {
  const { colors, isDark } = useTheme();
  const { user, refresh, signOut, ready } = useAuth();
  const { isDesktop } = useResponsive();

  // If in onboarding mode and user is already completed, route directly to home
  useEffect(() => {
    if (mode === "onboarding" && ready && user && (user.profile_completed || user.is_profile_complete)) {
      router.replace("/(tabs)/home");
    }
  }, [mode, ready, user]);

  // Split Google / existing name into First, Middle, Last names
  const parsedNames = useMemo(() => {
    if (user?.first_name || user?.last_name) {
      return {
        first: user?.first_name || "",
        middle: user?.middle_name || "",
        last: user?.last_name || "",
      };
    }
    const raw = (user?.name || "").trim();
    if (!raw) return { first: "", middle: "", last: "" };
    const parts = raw.split(/\s+/);
    if (parts.length === 1) return { first: parts[0], middle: "", last: "" };
    if (parts.length === 2) return { first: parts[0], middle: "", last: parts[1] };
    return {
      first: parts[0],
      middle: parts.slice(1, -1).join(" "),
      last: parts[parts.length - 1],
    };
  }, [user]);

  const [firstName, setFirstName] = useState(user?.first_name || parsedNames.first || "");
  const [middleName, setMiddleName] = useState(user?.middle_name || parsedNames.middle || "");
  const [lastName, setLastName] = useState(user?.last_name || parsedNames.last || "");
  const [mobile, setMobile] = useState(user?.mobile || "");
  const [gender, setGender] = useState<string>(user?.gender || "");
  const [dob, setDob] = useState(user?.dob || "");
  const [userType, setUserType] = useState<string>(user?.user_type || "Advocate");
  const [barCouncilNo, setBarCouncilNo] = useState(user?.bar_council_no || "");
  const [state, setState] = useState(user?.state || "Gujarat");
  const [district, setDistrict] = useState<string | null>(user?.district || null);
  const [districts, setDistricts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Load districts catalog
  useEffect(() => {
    api.districts()
      .then((r) => setDistricts(Array.isArray(r) ? r : []))
      .catch(() => setDistricts([]));
  }, []);

  // Sync state whenever user profile object updates
  useEffect(() => {
    if (user) {
      if (user.first_name || parsedNames.first) setFirstName(user.first_name || parsedNames.first || "");
      if (user.middle_name || parsedNames.middle) setMiddleName(user.middle_name || parsedNames.middle || "");
      if (user.last_name || parsedNames.last) setLastName(user.last_name || parsedNames.last || "");
      if (user.mobile) setMobile(user.mobile);
      if (user.gender) setGender(user.gender);
      if (user.dob) setDob(user.dob);
      if (user.user_type) setUserType(user.user_type);
      if (user.bar_council_no) setBarCouncilNo(user.bar_council_no);
      if (user.state) setState(user.state);
      if (user.district) setDistrict(user.district);
    }
  }, [user?.id, user?.name, user?.mobile, user?.district, user?.bar_council_no, user?.user_type]);

  const handleSave = async () => {
    setErr(null);
    setSuccessMsg(null);
    const fName = firstName.trim();
    const mName = middleName.trim();
    const lName = lastName.trim();
    let cleanMobile = mobile.replace(/\D/g, "");

    if (cleanMobile.startsWith("91") && cleanMobile.length === 12) {
      cleanMobile = cleanMobile.slice(2);
    }

    if (!fName) {
      setErr("Please enter your First Name.");
      return;
    }
    if (!lName) {
      setErr("Please enter your Last Name.");
      return;
    }
    if (!cleanMobile || cleanMobile.length !== 10 || !["6", "7", "8", "9"].includes(cleanMobile[0])) {
      setErr("Please enter a valid 10-digit Indian mobile number (e.g. 9876543210).");
      return;
    }
    if (!userType) {
      setErr("Please select your User Type / Role.");
      return;
    }
    if (userType === "Advocate" && !barCouncilNo.trim()) {
      setErr("Bar Council / Enrollment Number is required for Advocates (e.g. G/1234/2020).");
      return;
    }
    if (!state.trim()) {
      setErr("Please enter your State.");
      return;
    }
    if (!district) {
      setErr("Please select your District / City.");
      return;
    }

    const fullName = [fName, mName, lName].filter(Boolean).join(" ").trim();
    const advName = userType === "Advocate" ? `Adv. ${fullName}` : fullName;

    setLoading(true);
    try {
      await api.updateProfile({
        first_name: fName,
        middle_name: mName || undefined,
        last_name: lName,
        name: fullName,
        advocate_name_en: advName,
        mobile: cleanMobile,
        gender: gender || undefined,
        dob: dob.trim() || undefined,
        email: user?.email || undefined,
        user_type: userType,
        bar_council_no: userType === "Advocate" ? barCouncilNo.trim() : undefined,
        state: state.trim() || "Gujarat",
        district: district,
        picture: user?.picture || undefined,
        profile_completed: true,
        is_profile_complete: true,
      });

      await refresh();
      setSuccessMsg("Profile saved successfully!");

      if (onSuccess) {
        onSuccess();
      } else if (mode === "onboarding") {
        router.replace("/(tabs)/home");
      } else {
        if (Platform.OS === "web") {
          setTimeout(() => {
            router.replace("/(tabs)/profile" as any);
          }, 500);
        } else {
          Alert.alert("Success", "Profile updated successfully!", [
            { text: "OK", onPress: () => router.replace("/(tabs)/profile" as any) },
          ]);
        }
      }
    } catch (e: any) {
      setErr(e?.message || "Unable to save your profile. Please check your information and try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    } else if (router.canGoBack()) {
      router.back();
    } else {
      router.replace("/(tabs)/profile" as any);
    }
  };

  const isEdit = mode === "edit";

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#061024" }} edges={["top", "bottom"]}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView
          contentContainerStyle={[
            styles.scrollContent,
            isDesktop && styles.desktopContainer,
          ]}
          keyboardShouldPersistTaps="handled"
        >
          {/* Top Bar */}
          <View style={styles.topBar}>
            {isEdit ? (
              <Pressable
                testID="edit-profile-back-button"
                onPress={handleCancel}
                style={styles.backBtn}
              >
                <Ionicons name="arrow-back" size={20} color="#FDFDFD" />
                <Text style={styles.backText}>Back to Profile</Text>
              </Pressable>
            ) : (
              <View style={styles.brandRow}>
                <Ionicons name="shield-checkmark" size={22} color="#C5A059" />
                <Text style={styles.brandText}>NyaySetu Pro</Text>
              </View>
            )}

            {!isEdit ? (
              <Pressable
                testID="setup-switch-account"
                onPress={() => signOut().then(() => router.replace("/(auth)/login")).catch(() => router.replace("/(auth)/login"))}
                style={styles.logoutBtn}
              >
                <Ionicons name="log-out-outline" size={16} color="#A6B1C2" />
                <Text style={styles.logoutText}>Switch Account</Text>
              </Pressable>
            ) : null}
          </View>

          {/* Header Card */}
          <View style={styles.card}>
            <View style={styles.headerRow}>
              {user?.picture ? (
                <View style={styles.avatarWrap}>
                  <Image source={{ uri: user.picture }} style={styles.avatarImg} />
                  <View style={styles.googleIconBadge}>
                    <Ionicons name="logo-google" size={12} color="#FFF" />
                  </View>
                </View>
              ) : (
                <View style={styles.avatarPlaceholder}>
                  <Text style={styles.avatarInitial}>
                    {(firstName || user?.first_name || user?.name || "A").charAt(0).toUpperCase()}
                  </Text>
                </View>
              )}

              <View style={{ flex: 1 }}>
                <Text style={styles.title}>
                  {isEdit ? "Edit Profile" : "Complete Your Profile"}
                </Text>
                <Text style={styles.subtitle}>
                  {isEdit
                    ? "Update your personal and advocate workspace details."
                    : "Just a few details to personalize your NyaySetu Pro workspace."}
                </Text>
              </View>
            </View>

            {user?.email ? (
              <View style={styles.emailBadge}>
                <Ionicons name="checkmark-circle" size={16} color="#10B981" />
                <Text style={styles.emailText} numberOfLines={1}>
                  {user.email}
                </Text>
                <Text style={styles.verifiedTag}>
                  {user?.provider === "google" || user?.email.includes("@") ? "Verified Email" : "Account Email"}
                </Text>
              </View>
            ) : null}
          </View>

          {/* Validation Feedback Banner */}
          {err ? (
            <View style={styles.errorBox}>
              <Ionicons name="alert-circle" size={18} color="#EF4444" />
              <Text style={styles.errorText}>{err}</Text>
            </View>
          ) : null}

          {/* Success Banner */}
          {successMsg ? (
            <View style={styles.successBox}>
              <Ionicons name="checkmark-circle" size={18} color="#10B981" />
              <Text style={styles.successText}>{successMsg}</Text>
            </View>
          ) : null}

          {/* Form Fields */}
          <View style={styles.formCard}>
            {/* Name Fields */}
            <View style={styles.nameRow}>
              <View style={{ flex: 1, marginRight: Spacing.sm }}>
                <Field
                  testID="setup-first-name"
                  label="First Name *"
                  labelColor="#D1D8E5"
                  placeholder="e.g. Jaydeep"
                  value={firstName}
                  onChangeText={setFirstName}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Field
                  testID="setup-middle-name"
                  label="Middle Name"
                  labelColor="#D1D8E5"
                  placeholder="e.g. K"
                  value={middleName}
                  onChangeText={setMiddleName}
                />
              </View>
            </View>

            <Field
              testID="setup-last-name"
              label="Last Name *"
              labelColor="#D1D8E5"
              placeholder="e.g. Patel"
              value={lastName}
              onChangeText={setLastName}
            />

            {/* Mobile Number */}
            <Field
              testID="setup-mobile"
              label="Mobile Number *"
              labelColor="#D1D8E5"
              placeholder="10-digit mobile number (e.g. 9876543210)"
              keyboardType="number-pad"
              maxLength={10}
              value={mobile}
              onChangeText={setMobile}
            />

            {/* Optional Gender & Date of Birth */}
            <View style={{ marginBottom: Spacing.md }}>
              <Text style={styles.fieldLabel}>Gender (Optional)</Text>
              <View style={styles.pillsRow}>
                {GENDERS.map((g) => {
                  const active = gender === g;
                  return (
                    <Pressable
                      key={g}
                      testID={`setup-gender-${g.toLowerCase()}`}
                      onPress={() => setGender(active ? "" : g)}
                      style={[styles.genderPill, active && styles.genderPillActive]}
                    >
                      <Text style={[styles.pillText, active && styles.pillTextActive]}>{g}</Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>

            <Field
              testID="setup-dob"
              label="Date of Birth (Optional)"
              labelColor="#D1D8E5"
              placeholder="DD/MM/YYYY"
              value={dob}
              onChangeText={setDob}
            />

            {/* User Type / Role Selector */}
            <View style={{ marginBottom: Spacing.md }}>
              <Text style={styles.fieldLabel}>User Type / Role *</Text>
              <View style={styles.rolesGrid}>
                {USER_ROLES.map((role) => {
                  const active = userType === role;
                  return (
                    <Pressable
                      key={role}
                      testID={`setup-role-${role.toLowerCase().replace(/\s+/g, "-")}`}
                      onPress={() => setUserType(role)}
                      style={[
                        styles.rolePill,
                        active && styles.rolePillActive,
                      ]}
                    >
                      <Ionicons
                        name={
                          role === "Advocate"
                            ? "briefcase"
                            : role === "Legal Professional"
                            ? "business"
                            : role === "Law Student"
                            ? "school"
                            : "person"
                        }
                        size={15}
                        color={active ? "#061024" : "#C5A059"}
                      />
                      <Text style={[styles.roleText, active && styles.roleTextActive]}>
                        {role}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>

            {/* Bar Council / Enrollment Number (Dynamic: required only for Advocate) */}
            {userType === "Advocate" && (
              <Field
                testID="setup-bar-council"
                label="Bar Council / Enrollment Number *"
                labelColor="#D1D8E5"
                placeholder="e.g. G/1234/2020"
                value={barCouncilNo}
                onChangeText={setBarCouncilNo}
              />
            )}

            <Field
              testID="setup-state"
              label="State *"
              labelColor="#D1D8E5"
              placeholder="e.g. Gujarat"
              value={state}
              onChangeText={setState}
            />

            <Dropdown
              testID="setup-district"
              label="District / City *"
              placeholder="Select your district / city"
              searchable
              value={district}
              options={districts.map((d: any) => ({
                id: d.id,
                label: `${d.en} / ${d.gu}`,
              }))}
              onChange={setDistrict}
            />

            <View style={styles.infoBanner}>
              <Ionicons name="lock-closed-outline" size={18} color="#C5A059" />
              <Text style={styles.infoText}>
                Your details are securely saved and automatically formatted on your court documents.
              </Text>
            </View>

            <Button
              testID="setup-continue-button"
              title={isEdit ? "Save Changes" : "Save & Continue to Dashboard"}
              loading={loading}
              disabled={loading}
              onPress={handleSave}
              style={{ marginTop: Spacing.md }}
            />

            {isEdit && (
              <Button
                testID="setup-cancel-button"
                title="Cancel"
                variant="outline"
                disabled={loading}
                onPress={handleCancel}
                style={{ marginTop: Spacing.sm }}
              />
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    padding: Spacing.lg,
    paddingBottom: Spacing.xxl * 2,
  },
  desktopContainer: {
    maxWidth: 560,
    width: "100%",
    alignSelf: "center",
    paddingTop: Spacing.xl,
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: Spacing.lg,
  },
  backBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingVertical: 6,
    paddingHorizontal: 8,
  },
  backText: {
    color: "#FDFDFD",
    fontSize: 15,
    fontWeight: "600",
  },
  brandRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  brandText: {
    color: "#C5A059",
    fontWeight: "700",
    fontSize: 16,
    letterSpacing: 0.5,
    textTransform: "uppercase",
  },
  logoutBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: Radius.sm,
    backgroundColor: "rgba(255,255,255,0.05)",
  },
  logoutText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#A6B1C2",
  },
  card: {
    backgroundColor: "#0B1B3D",
    borderRadius: Radius.lg,
    borderWidth: 1,
    borderColor: "rgba(197, 160, 89, 0.25)",
    padding: Spacing.lg,
    marginBottom: Spacing.md,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.md,
  },
  avatarWrap: {
    position: "relative",
  },
  avatarImg: {
    width: 56,
    height: 56,
    borderRadius: 28,
    borderWidth: 2,
    borderColor: "#C5A059",
  },
  googleIconBadge: {
    position: "absolute",
    bottom: -2,
    right: -2,
    backgroundColor: "#EA4335",
    width: 20,
    height: 20,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1.5,
    borderColor: "#0B1B3D",
  },
  avatarPlaceholder: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#C5A059",
    alignItems: "center",
    justifyContent: "center",
  },
  avatarInitial: {
    color: "#0B1B3D",
    fontSize: 22,
    fontWeight: "800",
  },
  title: {
    fontSize: 20,
    fontWeight: "700",
    color: "#FDFDFD",
    fontFamily: "serif",
    letterSpacing: 0.3,
  },
  subtitle: {
    fontSize: 13,
    color: "#94A3B8",
    marginTop: 4,
    lineHeight: 18,
  },
  emailBadge: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: Spacing.md,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: Radius.md,
    backgroundColor: "#112240",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
    gap: 8,
  },
  emailText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#CBD5E1",
    flex: 1,
  },
  verifiedTag: {
    fontSize: 11,
    fontWeight: "700",
    color: "#10B981",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: "#EF4444",
    backgroundColor: "rgba(239, 68, 68, 0.15)",
    marginBottom: Spacing.md,
    gap: 8,
  },
  errorText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#FCA5A5",
    flex: 1,
  },
  successBox: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: "#10B981",
    backgroundColor: "rgba(16, 185, 129, 0.15)",
    marginBottom: Spacing.md,
    gap: 8,
  },
  successText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#6EE7B7",
    flex: 1,
  },
  formCard: {
    backgroundColor: "#0B1B3D",
    borderRadius: Radius.lg,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
    padding: Spacing.lg,
  },
  nameRow: {
    flexDirection: "row",
  },
  fieldLabel: {
    fontSize: 13,
    fontWeight: "600",
    color: "#D1D8E5",
    marginBottom: Spacing.xs,
  },
  pillsRow: {
    flexDirection: "row",
    gap: 8,
  },
  genderPill: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: Radius.md,
    backgroundColor: "#112240",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
  },
  genderPillActive: {
    backgroundColor: "#C5A059",
    borderColor: "#C5A059",
  },
  pillText: {
    fontSize: 13,
    color: "#CBD5E1",
    fontWeight: "500",
  },
  pillTextActive: {
    color: "#061024",
    fontWeight: "700",
  },
  rolesGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  rolePill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: Radius.md,
    backgroundColor: "#112240",
    borderWidth: 1,
    borderColor: "rgba(197, 160, 89, 0.3)",
  },
  rolePillActive: {
    backgroundColor: "#C5A059",
    borderColor: "#C5A059",
  },
  roleText: {
    fontSize: 13,
    color: "#E2E8F0",
    fontWeight: "500",
  },
  roleTextActive: {
    color: "#061024",
    fontWeight: "700",
  },
  infoBanner: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.md,
    borderRadius: Radius.md,
    backgroundColor: "#112240",
    borderWidth: 1,
    borderColor: "rgba(197, 160, 89, 0.2)",
    marginVertical: Spacing.sm,
    gap: Spacing.sm,
  },
  infoText: {
    fontSize: 12,
    color: "#CBD5E1",
    flex: 1,
    lineHeight: 17,
  },
});

import { useCallback, useState } from "react";
import { Alert, Pressable, ScrollView, StyleSheet, Switch, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";
import { formatAdvocateName } from "@/src/utils/advocate";

export default function Profile() {
  const { colors, isDark, setMode } = useTheme();
  const { user, signOut } = useAuth();
  const [wallet, setWallet] = useState({ balance: 0, total_used: 0 });

  useFocusEffect(useCallback(() => {
    api.wallet().then(setWallet).catch(() => {});
  }, []));

  const logout = () => {
    Alert.alert("Sign out?", "You will need to verify OTP again to sign in.", [
      { text: "Cancel", style: "cancel" },
      { text: "Sign out", style: "destructive", onPress: async () => { await signOut(); router.replace("/(auth)/login"); } },
    ]);
  };

  const rows: { icon: any; label: string; onPress?: () => void; right?: React.ReactNode }[] = [
    { icon: "person-outline", label: "Edit Profile", onPress: () => router.push("/(auth)/onboarding") },
    { icon: "wallet-outline", label: `Credit Balance: ${wallet.balance} templates`, onPress: () => router.push("/(tabs)/subscription") },
    { icon: "receipt-outline", label: "Transaction History", onPress: () => router.push("/transactions") },
    { icon: "share-social-outline", label: "Refer & Earn", onPress: () => router.push("/referral") },
    {
      icon: "moon-outline",
      label: "Dark Mode",
      right: (
        <Switch
          testID="dark-mode-switch"
          value={isDark}
          onValueChange={(v) => setMode(v ? "dark" : "light")}
          trackColor={{ true: colors.brandPrimary, false: colors.border }}
          thumbColor={"#fff"}
        />
      ),
    },
    { icon: "mail-outline", label: "Contact Support", onPress: () => Alert.alert("Support", "Email us at support@nyaysetupro.in") },
    { icon: "information-circle-outline", label: "About Us", onPress: () => Alert.alert("About NyaySetu Pro", "The New Era of Advocacy — helping Indian Advocates draft routine court documents faster and more affordably.") },
    { icon: "document-lock-outline", label: "Privacy Policy", onPress: () => router.push("/legal/privacy") },
    { icon: "shield-checkmark-outline", label: "Terms & Conditions", onPress: () => router.push("/legal/terms") },
    { icon: "refresh-outline", label: "Refund Policy", onPress: () => router.push("/legal/refund") },
  ];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <ScrollView contentContainerStyle={{ paddingBottom: Spacing.xxxl }}>
        <View style={[styles.header, { borderBottomColor: colors.border }]}>
          <Text style={[styles.h1, { color: colors.onSurface }]}>Profile</Text>
        </View>

        <View style={[styles.userCard, { backgroundColor: colors.brand }]}>
          <View style={[styles.avatar, { backgroundColor: colors.brandPrimary }]}>
            <Text style={{ color: colors.onBrandPrimary, fontSize: 22, fontWeight: "800" }}>
              {(user?.name || user?.mobile || "A").charAt(0).toUpperCase()}
            </Text>
          </View>
          <View style={{ flex: 1, marginLeft: Spacing.md }}>
            <Text style={{ color: "#FFF", fontSize: 17, fontWeight: "700" }}>{formatAdvocateName(user?.name)}</Text>
            <Text style={{ color: "#A6B1C2", fontSize: 12, marginTop: 2 }}>+91 {user?.mobile}</Text>
            {user?.bar_council_no ? (
              <Text style={{ color: "#C5A059", fontSize: 11, marginTop: 2 }}>Bar: {user.bar_council_no}</Text>
            ) : null}
          </View>
        </View>

        <View style={{ paddingHorizontal: Spacing.lg, gap: Spacing.xs, marginTop: Spacing.md }}>
          {rows.map((r, i) => (
            <Pressable
              key={i}
              testID={`profile-row-${i}`}
              onPress={r.onPress}
              style={[styles.row, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
            >
              <Ionicons name={r.icon} size={20} color={colors.onSurface} />
              <Text style={{ color: colors.onSurface, flex: 1, marginLeft: Spacing.md, fontSize: 14 }}>{r.label}</Text>
              {r.right || <Ionicons name="chevron-forward" size={18} color={colors.muted} />}
            </Pressable>
          ))}

          <Pressable
            testID="logout-btn"
            onPress={logout}
            style={[styles.row, { backgroundColor: colors.surfaceSecondary, borderColor: colors.error + "40", marginTop: Spacing.md }]}
          >
            <Ionicons name="log-out-outline" size={20} color={colors.error} />
            <Text style={{ color: colors.error, flex: 1, marginLeft: Spacing.md, fontSize: 14, fontWeight: "700" }}>Sign Out</Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { padding: Spacing.lg, borderBottomWidth: StyleSheet.hairlineWidth },
  h1: { fontSize: 22, fontWeight: "700", fontFamily: "serif" },
  userCard: {
    flexDirection: "row", alignItems: "center",
    margin: Spacing.lg, padding: Spacing.lg, borderRadius: Radius.lg,
  },
  avatar: { width: 56, height: 56, borderRadius: 18, alignItems: "center", justifyContent: "center" },
  row: {
    flexDirection: "row", alignItems: "center",
    paddingVertical: Spacing.md, paddingHorizontal: Spacing.md,
    borderRadius: Radius.md, borderWidth: 1,
  },
});

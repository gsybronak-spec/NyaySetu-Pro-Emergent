import { useCallback, useState } from "react";
import { Alert, Platform, Pressable, ScrollView, StyleSheet, Switch, Text, View } from "react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router, useFocusEffect } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { useAppLanguage } from "@/src/context/AppLanguageContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";
import { formatAdvocateName, formatDisplayName } from "@/src/utils/advocate";
import { useResponsive } from "@/src/hooks/useResponsive";
import { DesktopPage } from "@/src/components/DesktopPage";

import { getCachedWallet, setCachedPlans, setCachedWallet } from "@/src/constants/plans";
import { preloadRazorpayScript } from "@/src/utils/razorpay";

export default function Profile() {
  const { colors, isDark, setMode } = useTheme();
  const { appLang, t, ui } = useAppLanguage();
  const { isDesktop } = useResponsive();
  const insets = useSafeAreaInsets();
  const { user, signOut } = useAuth();
  const [wallet, setWallet] = useState(() => getCachedWallet() || { balance: user?.wallet_balance ?? 0, total_used: user?.total_credits_used ?? 0 });

  useFocusEffect(useCallback(() => {
    let active = true;
    api.wallet().then((w) => {
      if (active && w && typeof w === "object") {
        setWallet(w);
        setCachedWallet(w);
      }
    }).catch(() => {});
    api.plans().then((p) => {
      if (active && Array.isArray(p) && p.length > 0) {
        setCachedPlans(p);
      }
    }).catch(() => {});
    try {
      preloadRazorpayScript();
    } catch {
      // Fire-and-forget non-blocking
    }
    return () => {
      active = false;
    };
  }, []));

  const logout = () => {
    if (Platform.OS === "web") {
      if (typeof window !== "undefined" && window.confirm(ui("Sign out? You will need to login again to continue.", "લૉગ આઉટ કરવું છે? આગળ વધવા માટે ફરી લૉગિન કરવું પડશે."))) {
        signOut().then(() => router.replace("/(auth)/login")).catch(() => router.replace("/(auth)/login"));
      }
      return;
    }
    Alert.alert(
      ui("Sign out?", "લૉગ આઉટ કરવું છે?"),
      ui("You will need to verify OTP again to sign in.", "ફરી સાઇન ઇન કરવા માટે OTP ચકાસવો પડશે."),
      [
        { text: t("cancel"), style: "cancel" },
        { text: ui("Sign out", "લૉગ આઉટ"), style: "destructive", onPress: async () => { await signOut(); router.replace("/(auth)/login"); } },
      ]
    );
  };

  const isUnlimited = Boolean(user?.unlimited_access || user?.is_owner || user?.is_partner || (wallet as any)?.unlimited || (wallet as any)?.unlimited_access);

  const rows: { icon: any; label: string; danger?: boolean; onPress?: () => void; right?: React.ReactNode }[] = [
    { icon: "person-outline", label: ui("Edit Profile", "પ્રોફાઇલ સુધારો"), onPress: () => router.push("/profile/edit" as any) },
    {
      icon: "book-outline",
      label: t("userGuideFull"),
      onPress: () => router.push("/user-guide" as any),
    },
    {
      icon: "key-outline",
      label: user?.has_password ? ui("Change Password", "પાસવર્ડ બદલો") : ui("Set Password", "પાસવર્ડ સેટ કરો"),
      onPress: () => router.push("/profile/set-password" as any),
    },
    { icon: "diamond-outline", label: ui("Plans & Subscription", "પ્લાન્સ અને સબ્સ્ક્રિપ્શન"), onPress: () => router.push("/(tabs)/subscription" as any) },
    {
      icon: "wallet-outline",
      label: isUnlimited
        ? (user?.is_owner
            ? ui("Credit Balance: Unlimited (Owner Access)", "ક્રેડિટ બેલેન્સ: અમર્યાદિત (માલિક ઍક્સેસ)")
            : ui("Credit Balance: Unlimited (Partner Access)", "ક્રેડિટ બેલેન્સ: અમર્યાદિત (પાર્ટનર ઍક્સેસ)"))
        : ui(`Credit Balance: ${wallet.balance} templates (Buy Credits)`, `ક્રેડિટ બેલેન્સ: ${wallet.balance} અરજીઓ (ક્રેડિટ ખરીદો)`),
      onPress: () => router.push("/(tabs)/subscription" as any),
    },
    { icon: "receipt-outline", label: ui("Transaction History", "વ્યવહાર ઇતિહાસ"), onPress: () => router.push("/transactions" as any) },
    { icon: "file-tray-full-outline", label: ui("Document Vault & History", "ડોક્યુમેન્ટ વૉલ્ટ અને ઇતિહાસ"), onPress: () => router.push("/vault" as any) },
    { icon: "share-social-outline", label: ui("Refer & Earn", "રેફર કરો અને કમાઓ"), onPress: () => router.push("/referral" as any) },
    {
      icon: "moon-outline",
      label: ui("Dark Mode", "ડાર્ક મોડ"),
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
    { icon: "mail-outline", label: ui("Contact Support", "સહાય સંપર્ક"), onPress: () => router.push("/support" as any) },
    { icon: "information-circle-outline", label: ui("About Us", "અમારા વિશે"), onPress: () => router.push("/about" as any) },
    { icon: "document-lock-outline", label: ui("Privacy Policy", "ગોપનીયતા નીતિ"), onPress: () => router.push("/legal/privacy" as any) },
    { icon: "shield-checkmark-outline", label: ui("Terms & Conditions", "નિયમો અને શરતો"), onPress: () => router.push("/legal/terms" as any) },
    { icon: "refresh-outline", label: ui("Refund Policy", "રિફંડ નીતિ"), onPress: () => router.push("/legal/refund" as any) },
    { icon: "trash-outline", label: ui("Delete Account", "એકાઉન્ટ કાઢી નાખો"), danger: true, onPress: () => router.push("/delete-account" as any) },
  ];

  // ------------------------- DESKTOP -------------------------
  if (isDesktop) {
    return (
      <DesktopPage
        title={t("tabProfile")}
        subtitle={ui("Manage your account and preferences", "તમારું એકાઉન્ટ અને પસંદગીઓ મેનેજ કરો")}
      >
        <View style={styles.dGrid}>
          <View style={[styles.dUserCard, { backgroundColor: colors.brand }]}>
            <View style={[styles.avatar, { backgroundColor: colors.brandPrimary }]}>
              <Text style={{ color: colors.onBrandPrimary, fontSize: 26, fontWeight: "800" }}>
                {(user?.first_name || user?.name || user?.mobile || "A").charAt(0).toUpperCase()}
              </Text>
            </View>
            <Text style={{ color: "#FFF", fontSize: 18, fontWeight: "700", marginTop: Spacing.md }}>
              {formatDisplayName(user, t("user"), appLang)}
            </Text>
            {user?.advocate_name_gu ? (
              <Text style={{ color: "#E2E8F0", fontSize: 14, marginTop: 1 }}>{formatAdvocateName(user.advocate_name_gu, "gu")}</Text>
            ) : null}
            {(user?.advocate_qualification || user?.qualification) ? (
              <Text style={{ color: "#CBD5E1", fontSize: 13, marginTop: 2, fontWeight: "600" }}>
                {user?.advocate_qualification || user?.qualification}
              </Text>
            ) : null}
            <Text style={{ color: "#A6B1C2", fontSize: 13, marginTop: 2 }}>{user?.mobile ? `+91 ${user.mobile}` : user?.email || ""}</Text>
            {user?.email && user?.mobile ? <Text style={{ color: "#A6B1C2", fontSize: 12, marginTop: 2 }} numberOfLines={1}>{user.email}</Text> : null}
            {user?.office_address || user?.advocate_address ? (
              <Text style={{ color: "#94A3B8", fontSize: 12, marginTop: 2 }} numberOfLines={2}>
                {user?.office_address || user?.advocate_address}
              </Text>
            ) : null}
            {user?.bar_council_no ? (
              <View style={styles.dBarChip}>
                <Ionicons name="ribbon" size={13} color="#C5A059" />
                <Text style={{ color: "#C5A059", fontSize: 12, fontWeight: "700", marginLeft: 6 }}>{ui("Bar:", "સનદ:")} {user.bar_council_no}</Text>
              </View>
            ) : null}
            {isUnlimited ? (
              <View style={[styles.dBarChip, { backgroundColor: "rgba(16,185,129,0.15)", marginTop: Spacing.sm }]}>
                <Ionicons name="shield-checkmark" size={13} color="#10B981" />
                <Text style={{ color: "#10B981", fontSize: 12, fontWeight: "700", marginLeft: 6 }}>
                  {user?.is_owner ? ui("Owner Unlimited Access", "માલિક અમર્યાદિત ઍક્સેસ") : ui("Partner Unlimited Access", "પાર્ટનર અમર્યાદિત ઍક્સેસ")}
                </Text>
              </View>
            ) : null}
            <View style={[styles.dWalletLine, { borderTopColor: "rgba(255,255,255,0.1)" }]}>
              <Ionicons name="wallet" size={18} color="#C5A059" />
              <Text style={{ color: "#FDFDFD", fontWeight: "800", fontSize: 16, marginLeft: 8 }}>
                {isUnlimited ? t("unlimited") : wallet.balance}{" "}
                <Text style={{ color: "#A6B1C2", fontSize: 12, fontWeight: "500" }}>
                  {isUnlimited ? ui("templates access", "અરજીઓનો ઍક્સેસ") : ui("templates remaining", "અરજીઓ બાકી")}
                </Text>
              </Text>
            </View>
            <Pressable
              testID="logout-btn"
              onPress={logout}
              style={styles.dLogout}
            >
              <Ionicons name="log-out-outline" size={18} color="#FDFDFD" />
              <Text style={{ color: "#FDFDFD", fontWeight: "700", marginLeft: 8 }}>{ui("Sign Out", "લૉગ આઉટ")}</Text>
            </Pressable>
          </View>

          <View style={{ flex: 1, gap: Spacing.sm }}>
            {rows.map((r, i) => (
              <Pressable
                key={i}
                testID={`profile-row-${i}`}
                onPress={r.onPress}
                style={[styles.dRow, { backgroundColor: colors.surfaceSecondary, borderColor: r.danger ? colors.error + "40" : colors.border }]}
              >
                <Ionicons name={r.icon} size={20} color={r.danger ? colors.error : colors.onSurface} />
                <Text style={{ color: r.danger ? colors.error : colors.onSurface, flex: 1, marginLeft: Spacing.md, fontSize: 14, fontWeight: r.danger ? "600" : "400" }}>{r.label}</Text>
                {r.right || <Ionicons name="chevron-forward" size={18} color={colors.muted} />}
              </Pressable>
            ))}
          </View>
        </View>
      </DesktopPage>
    );
  }

  // ------------------------- MOBILE (unchanged) -------------------------
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ paddingBottom: Math.max(90, 60 + insets.bottom + Spacing.xl) }}
      >
        <View style={[styles.header, { borderBottomColor: colors.border }]}>
          <Text style={[styles.h1, { color: colors.onSurface }]}>{t("tabProfile")}</Text>
        </View>

        <View style={[styles.userCard, { backgroundColor: colors.brand }]}>
          <View style={[styles.avatar, { backgroundColor: colors.brandPrimary }]}>
            <Text style={{ color: colors.onBrandPrimary, fontSize: 22, fontWeight: "800" }}>
              {(user?.first_name || user?.name || user?.mobile || "A").charAt(0).toUpperCase()}
            </Text>
          </View>
          <View style={{ flex: 1, marginLeft: Spacing.md }}>
            <Text style={{ color: "#FFF", fontSize: 17, fontWeight: "700" }}>{formatDisplayName(user, t("user"), appLang)}</Text>
            {user?.advocate_name_gu ? (
              <Text style={{ color: "#E2E8F0", fontSize: 13, marginTop: 1 }}>{formatAdvocateName(user.advocate_name_gu, "gu")}</Text>
            ) : null}
            {(user?.advocate_qualification || user?.qualification) ? (
              <Text style={{ color: "#CBD5E1", fontSize: 12, marginTop: 1, fontWeight: "600" }}>
                {user?.advocate_qualification || user?.qualification}
              </Text>
            ) : null}
            <Text style={{ color: "#A6B1C2", fontSize: 12, marginTop: 2 }}>{user?.mobile ? `+91 ${user.mobile}` : user?.email || ""}</Text>
            {user?.office_address || user?.advocate_address ? (
              <Text style={{ color: "#94A3B8", fontSize: 11, marginTop: 1 }} numberOfLines={1}>
                {user?.office_address || user?.advocate_address}
              </Text>
            ) : null}
            {user?.bar_council_no ? (
              <Text style={{ color: "#C5A059", fontSize: 11, marginTop: 2 }}>{ui("Bar:", "સનદ:")} {user.bar_council_no}</Text>
            ) : null}
            {isUnlimited ? (
              <Text style={{ color: "#10B981", fontSize: 11, fontWeight: "700", marginTop: 2 }}>
                {user?.is_owner ? ui("Owner Unlimited Access", "માલિક અમર્યાદિત ઍક્સેસ") : ui("Partner Unlimited Access", "પાર્ટનર અમર્યાદિત ઍક્સેસ")}
              </Text>
            ) : null}
          </View>
        </View>

        <View style={{ paddingHorizontal: Spacing.lg, gap: Spacing.xs, marginTop: Spacing.md }}>
          {rows.map((r, i) => (
            <Pressable
              key={i}
              testID={`profile-row-${i}`}
              onPress={r.onPress}
              style={[styles.row, { backgroundColor: colors.surfaceSecondary, borderColor: r.danger ? colors.error + "40" : colors.border }]}
            >
              <Ionicons name={r.icon} size={20} color={r.danger ? colors.error : colors.onSurface} />
              <Text style={{ color: r.danger ? colors.error : colors.onSurface, flex: 1, marginLeft: Spacing.md, fontSize: 14, fontWeight: r.danger ? "600" : "400" }}>{r.label}</Text>
              {r.right || <Ionicons name="chevron-forward" size={18} color={colors.muted} />}
            </Pressable>
          ))}

          <Pressable
            testID="logout-btn"
            onPress={logout}
            style={[styles.row, { backgroundColor: colors.surfaceSecondary, borderColor: colors.error + "40", marginTop: Spacing.md }]}
          >
            <Ionicons name="log-out-outline" size={20} color={colors.error} />
            <Text style={{ color: colors.error, flex: 1, marginLeft: Spacing.md, fontSize: 14, fontWeight: "700" }}>{ui("Sign Out", "લૉગ આઉટ")}</Text>
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
  // Desktop
  dGrid: { flexDirection: "row", gap: Spacing.xl, alignItems: "flex-start" },
  dUserCard: {
    width: 320, flexShrink: 0,
    borderRadius: 16, padding: Spacing.xl, alignItems: "center",
  },
  dBarChip: {
    flexDirection: "row", alignItems: "center", marginTop: Spacing.md,
    backgroundColor: "rgba(197,160,89,0.12)", paddingHorizontal: Spacing.md, paddingVertical: 6,
    borderRadius: 999,
  },
  dWalletLine: {
    flexDirection: "row", alignItems: "center",
    borderTopWidth: 1, marginTop: Spacing.xl, paddingTop: Spacing.lg, alignSelf: "stretch",
  },
  dLogout: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    marginTop: Spacing.lg, alignSelf: "stretch",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.25)",
    borderRadius: 12, paddingVertical: 12,
  },
  dRow: {
    flexDirection: "row", alignItems: "center",
    paddingVertical: Spacing.md, paddingHorizontal: Spacing.md,
    borderRadius: Radius.md, borderWidth: 1,
  },
});

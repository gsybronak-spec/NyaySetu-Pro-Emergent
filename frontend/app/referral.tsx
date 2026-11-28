import { useCallback, useState } from "react";
import { Pressable, Share, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import * as Clipboard from "expo-clipboard";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router, useFocusEffect } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAppLanguage } from "@/src/context/AppLanguageContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";
import { safeBack } from "@/src/utils/navigation";

export default function Referral() {
  const { colors, isDark } = useTheme();
  const { ui } = useAppLanguage();
  const [data, setData] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  useFocusEffect(useCallback(() => {
    api.referral().then(setData).catch(() => {});
  }, []));

  const code = data?.referral_code || "…";
  const reward = data?.reward_per_referral || 10;

  const shareMessage = ui(
    `I'm using NyaySetu Pro to draft court applications in seconds\n\nUse my referral code *${code}* when you sign up.\n\nThe New Era of Advocacy.`,
    `હું સેકન્ડમાં કોર્ટ અરજીઓ બનાવવા માટે NyaySetu Pro વાપરું છું\n\nસાઇન અપ કરતી વખતે મારો રેફરલ કોડ *${code}* વાપરો.\n\nવકીલાતનો નવો યુગ.`
  );

  const copy = async () => {
    await Clipboard.setStringAsync(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const share = async () => {
    try {
      await Share.share({ message: shareMessage });
    } catch {}
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Pressable testID="referral-back" onPress={() => safeBack("/(tabs)/profile")} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
        </Pressable>
        <Text style={[styles.h1, { color: colors.onSurface }]}>{ui("Refer & Earn", "રેફર કરો અને કમાઓ")}</Text>
        <View style={{ width: 24 }} />
      </View>

      <View style={{ padding: Spacing.lg }}>
        <LinearGradient colors={isDark ? ["#0B1B3D", "#061024"] : ["#0B1B3D", "#112240"]} style={styles.hero}>
          <View style={styles.giftBadge}>
            <Ionicons name="gift" size={34} color="#C5A059" />
          </View>
          <Text style={styles.heroBig}>{ui(`Give & Get ${reward} Templates`, `${reward} મફત અરજીઓ મેળવો`)}</Text>
          <Text style={styles.heroSub}>
            {ui(
              `Invite a fellow Advocate. When they sign up with your code, you get ${reward} free templates.`,
              `સાથી એડવોકેટને આમંત્રણ આપો. જ્યારે તેઓ તમારા કોડથી સાઇન અપ કરશે, ત્યારે તમને ${reward} મફત અરજીઓ મળશે.`
            )}
          </Text>
        </LinearGradient>

        {/* Code card */}
        <View style={[styles.codeCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.brandPrimary }]}>
          <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "700", letterSpacing: 1 }}>{ui("YOUR REFERRAL CODE", "તમારો રેફરલ કોડ")}</Text>
          <Text style={[styles.code, { color: colors.onSurface }]}>{code}</Text>
          <View style={{ flexDirection: "row", gap: Spacing.md, marginTop: Spacing.md }}>
            <Pressable testID="referral-copy" onPress={copy} style={[styles.actBtn, { borderColor: colors.brandPrimary }]}>
              <Ionicons name={copied ? "checkmark" : "copy-outline"} size={18} color={colors.brandPrimary} />
              <Text style={{ color: colors.brandPrimary, fontWeight: "700", marginLeft: 6 }}>
                {copied ? ui("Copied", "કૉપિ થયું") : ui("Copy", "કૉપિ કરો")}
              </Text>
            </Pressable>
            <Pressable testID="referral-share" onPress={share} style={[styles.actBtn, { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary }]}>
              <Ionicons name="share-social" size={18} color={colors.onBrandPrimary} />
              <Text style={{ color: colors.onBrandPrimary, fontWeight: "700", marginLeft: 6 }}>{ui("Share", "શેર કરો")}</Text>
            </Pressable>
          </View>
        </View>

        {/* Stats */}
        <View style={styles.statsRow}>
          <View style={[styles.stat, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
            <Text style={[styles.statVal, { color: colors.onSurface }]}>{data?.total_referred ?? 0}</Text>
            <Text style={{ color: colors.muted, fontSize: 12 }}>{ui("Advocates Invited", "આમંત્રિત એડવોકેટ્સ")}</Text>
          </View>
          <View style={[styles.stat, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
            <Text style={[styles.statVal, { color: colors.brandPrimary }]}>{data?.total_reward_credits ?? 0}</Text>
            <Text style={{ color: colors.muted, fontSize: 12 }}>{ui("Templates Earned", "મેળવેલી અરજીઓ")}</Text>
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, borderBottomWidth: StyleSheet.hairlineWidth,
  },
  h1: { fontSize: 18, fontWeight: "700", fontFamily: "serif" },
  hero: { borderRadius: Radius.lg, padding: Spacing.xl, alignItems: "center", borderWidth: 1, borderColor: "rgba(197,160,89,0.2)" },
  giftBadge: {
    width: 72, height: 72, borderRadius: 22, backgroundColor: "rgba(197,160,89,0.12)",
    alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: "rgba(197,160,89,0.35)",
  },
  heroBig: { color: "#FDFDFD", fontSize: 22, fontWeight: "700", fontFamily: "serif", marginTop: Spacing.md, textAlign: "center" },
  heroSub: { color: "#A6B1C2", fontSize: 13, textAlign: "center", marginTop: Spacing.sm, lineHeight: 19 },
  codeCard: { marginTop: Spacing.lg, padding: Spacing.lg, borderRadius: Radius.lg, borderWidth: 1.5, alignItems: "center" },
  code: { fontSize: 30, fontWeight: "800", letterSpacing: 3, marginTop: Spacing.sm, fontFamily: "serif" },
  actBtn: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", height: 46, borderRadius: Radius.md, borderWidth: 1.5 },
  statsRow: { flexDirection: "row", gap: Spacing.md, marginTop: Spacing.lg },
  stat: { flex: 1, padding: Spacing.lg, borderRadius: Radius.md, borderWidth: 1, alignItems: "center" },
  statVal: { fontSize: 26, fontWeight: "800", fontFamily: "serif" },
});

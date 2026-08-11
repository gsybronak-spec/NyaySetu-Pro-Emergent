import { useCallback, useEffect, useState } from "react";
import { FlatList, Image, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";

export default function Home() {
  const { colors, isDark } = useTheme();
  const { user } = useAuth();
  const [quote, setQuote] = useState("Justice begins with preparation.");
  const [wallet, setWallet] = useState({ balance: 0, total_used: 0 });
  const [templates, setTemplates] = useState<any[]>([]);
  const [drafts, setDrafts] = useState<any[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState(false);

  const load = useCallback(async () => {
    let failed = false;
    const [q, w, tpls, drs] = await Promise.all([
      api.quote().catch(() => { failed = true; return null; }),
      api.wallet().catch(() => { failed = true; return null; }),
      api.templates().catch(() => { failed = true; return []; }),
      api.drafts().catch(() => { failed = true; return []; }),
    ]);
    if (q?.quote) setQuote(q.quote);
    if (w && typeof w === "object") setWallet(w);
    setTemplates(Array.isArray(tpls) ? tpls.slice(0, 10) : []);
    setDrafts(Array.isArray(drs) ? drs : []);
    setLoadError(failed);
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good Morning" : hour < 18 ? "Good Afternoon" : "Good Evening";
  const advocateName = user?.name || "Advocate";

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <View style={styles.brandRow}>
          <Image source={require("../../assets/images/logo.png")} style={styles.brandLogo} resizeMode="contain" />
          <Text style={[styles.brandName, { color: colors.onSurface }]}>NyaySetu <Text style={{ color: colors.brandPrimary }}>Pro</Text></Text>
        </View>
        <View style={{ flexDirection: "row", gap: Spacing.md }}>
          <Pressable testID="home-search-btn" onPress={() => router.push("/search")}>
            <Ionicons name="search" size={22} color={colors.onSurface} />
          </Pressable>
        </View>
      </View>

      <ScrollView
        contentContainerStyle={{ paddingBottom: Spacing.xxxl }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {loadError && (
          <View style={[styles.errorBanner, { backgroundColor: colors.surfaceSecondary, borderColor: colors.error + "50" }]}>
            <Ionicons name="cloud-offline-outline" size={16} color={colors.error} />
            <Text style={{ color: colors.error, fontSize: 12, flex: 1, marginLeft: 6 }}>
              Couldn't refresh your data. Check your connection.
            </Text>
            <Pressable testID="home-error-retry" onPress={load} hitSlop={8}>
              <Text style={{ color: colors.brandPrimary, fontWeight: "700", fontSize: 12 }}>Retry</Text>
            </Pressable>
          </View>
        )}
        {/* Welcome Card */}
        <LinearGradient
          colors={isDark ? ["#0B1B3D", "#112240"] : ["#0B1B3D", "#1D2D50"]}
          style={styles.welcome}
        >
          <Text style={styles.welcomeGreet}>{greeting},</Text>
          <Text style={styles.welcomeName}>{advocateName}</Text>
          <View style={styles.quoteRow}>
            <View style={styles.quoteBar} />
            <Text style={styles.quote}>"{quote}"</Text>
          </View>
          <View style={styles.walletChip}>
            <Ionicons name="wallet" size={14} color="#C5A059" />
            <Text style={styles.walletTxt}>{wallet.balance} Templates Remaining</Text>
          </View>
        </LinearGradient>

        {/* Action Cards */}
        <View style={styles.actionRow}>
          <Pressable
            testID="home-add-case-card"
            onPress={() => router.push("/case/new")}
            style={[styles.actionCard, { backgroundColor: colors.brandPrimary }]}
          >
            <Ionicons name="add-circle" size={26} color={colors.onBrandPrimary} />
            <Text style={[styles.actionTitle, { color: colors.onBrandPrimary }]}>Add New Case</Text>
            <Text style={[styles.actionSub, { color: colors.onBrandPrimary, opacity: 0.85 }]}>Create in seconds</Text>
          </Pressable>
          <Pressable
            testID="home-my-cases-card"
            onPress={() => router.push("/(tabs)/cases")}
            style={[styles.actionCard, { backgroundColor: colors.brand }]}
          >
            <Ionicons name="folder-open" size={26} color="#FFF" />
            <Text style={[styles.actionTitle, { color: "#FFF" }]}>My Cases</Text>
            <Text style={[styles.actionSub, { color: "#FFF", opacity: 0.75 }]}>Manage all cases</Text>
          </Pressable>
        </View>

        {/* Continue Drafting */}
        {drafts.length > 0 && (
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: colors.onSurface }]}>Continue Drafting</Text>
            {drafts.slice(0, 2).map((d) => (
              <Pressable
                key={d.id}
                testID={`draft-${d.id}`}
                onPress={() => router.push({ pathname: "/template/[id]", params: { id: d.template_id, case_id: d.case_id ?? "", lang: d.language, draft: "1" } })}
                style={[styles.draftRow, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
              >
                <Ionicons name="document-text" size={22} color={colors.brandPrimary} />
                <View style={{ flex: 1, marginLeft: Spacing.md }}>
                  <Text style={{ color: colors.onSurface, fontWeight: "700" }}>{d.template_name}</Text>
                  <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }}>Last edited: {new Date(d.updated_at).toLocaleString()}</Text>
                </View>
                <Ionicons name="chevron-forward" size={20} color={colors.muted} />
              </Pressable>
            ))}
          </View>
        )}

        {/* Categories */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.onSurface }]}>Categories</Text>
          <View style={{ flexDirection: "row", gap: Spacing.md }}>
            {[
              { key: "Civil", icon: "business", color: "#0B1B3D" },
              { key: "Criminal", icon: "shield", color: "#7A1C1C" },
            ].map((c) => (
              <Pressable
                key={c.key}
                testID={`cat-${c.key.toLowerCase()}`}
                onPress={() => router.push({ pathname: "/(tabs)/templates", params: { cat: c.key } })}
                style={[styles.catCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
              >
                <View style={[styles.catIcon, { backgroundColor: c.color + "20" }]}>
                  <Ionicons name={c.icon as any} size={22} color={c.color} />
                </View>
                <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 15 }}>{c.key}</Text>
              </Pressable>
            ))}
          </View>
        </View>

        {/* Most Used Templates */}
        <View style={styles.section}>
          <View style={styles.rowBetween}>
            <Text style={[styles.sectionTitle, { color: colors.onSurface, marginBottom: 0 }]}>Most Used Templates</Text>
            <Pressable testID="see-all-templates" onPress={() => router.push("/(tabs)/templates")}>
              <Text style={{ color: colors.brandPrimary, fontWeight: "700" }}>See All</Text>
            </Pressable>
          </View>
          <FlatList
            data={templates}
            keyExtractor={(t) => t.id}
            numColumns={2}
            scrollEnabled={false}
            columnWrapperStyle={{ gap: Spacing.md }}
            contentContainerStyle={{ gap: Spacing.md, marginTop: Spacing.md }}
            renderItem={({ item }) => (
              <Pressable
                testID={`tpl-card-${item.id}`}
                onPress={() => router.push({ pathname: "/template/[id]", params: { id: item.id } })}
                style={[styles.tplCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
              >
                <Ionicons name="document-text" size={22} color={colors.brandPrimary} />
                <Text style={{ color: colors.onSurface, fontWeight: "700", marginTop: Spacing.sm }} numberOfLines={2}>
                  {item.name_en}
                </Text>
                <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }} numberOfLines={1}>
                  {item.name_gu}
                </Text>
              </Pressable>
            )}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  brandRow: { flexDirection: "row", alignItems: "center", gap: Spacing.sm },
  brandLogo: { width: 28, height: 30 },
  brandName: { fontSize: 18, fontWeight: "800", fontFamily: "serif" },
  welcome: {
    margin: Spacing.lg,
    padding: Spacing.xl,
    borderRadius: Radius.lg,
    borderWidth: 1,
    borderColor: "rgba(197,160,89,0.2)",
  },
  welcomeGreet: { color: "#C5A059", fontSize: 12, letterSpacing: 1.5, textTransform: "uppercase", fontWeight: "700" },
  welcomeName: { color: "#FDFDFD", fontSize: 24, fontFamily: "serif", fontWeight: "700", marginTop: 4 },
  quoteRow: { flexDirection: "row", alignItems: "center", marginTop: Spacing.md },
  quoteBar: { width: 3, height: 20, backgroundColor: "#C5A059", marginRight: Spacing.sm },
  quote: { color: "#D1D8E5", fontStyle: "italic", flex: 1, fontSize: 13 },
  walletChip: {
    flexDirection: "row", alignItems: "center", alignSelf: "flex-start",
    gap: 6, backgroundColor: "rgba(197,160,89,0.1)",
    paddingHorizontal: Spacing.md, paddingVertical: 6,
    borderRadius: Radius.pill, marginTop: Spacing.md,
    borderWidth: 1, borderColor: "rgba(197,160,89,0.35)",
  },
  walletTxt: { color: "#C5A059", fontSize: 12, fontWeight: "700" },
  errorBanner: {
    flexDirection: "row", alignItems: "center", marginHorizontal: Spacing.lg, marginTop: Spacing.md,
    padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1,
  },
  actionRow: { flexDirection: "row", paddingHorizontal: Spacing.lg, gap: Spacing.md },
  actionCard: { flex: 1, padding: Spacing.lg, borderRadius: Radius.lg, gap: 6 },
  actionTitle: { fontSize: 16, fontWeight: "800", marginTop: Spacing.sm },
  actionSub: { fontSize: 11 },
  section: { paddingHorizontal: Spacing.lg, marginTop: Spacing.xl },
  sectionTitle: { fontSize: 17, fontWeight: "700", marginBottom: Spacing.md, fontFamily: "serif" },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  draftRow: {
    flexDirection: "row", alignItems: "center", padding: Spacing.md,
    borderRadius: Radius.md, borderWidth: 1, marginBottom: Spacing.sm,
  },
  catCard: {
    flex: 1, padding: Spacing.lg, borderRadius: Radius.md, borderWidth: 1,
    alignItems: "flex-start", gap: Spacing.sm,
  },
  catIcon: { width: 40, height: 40, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  tplCard: {
    flex: 1, padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1, minHeight: 110,
  },
});

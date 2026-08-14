import { useCallback, useState } from "react";
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";

function fmtDate(iso?: string) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso.slice(0, 10);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) +
    " · " + d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

export default function Transactions() {
  const { colors } = useTheme();
  const { isDesktop } = useResponsive();
  const [items, setItems] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const txs = await api.transactions();
      setItems(Array.isArray(txs) ? txs : []);
      setError(null);
    } catch (e: any) {
      setError(e?.message || "Could not load transactions.");
      setItems([]);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const renderTxn = ({ item }: { item: any }) => {
    const positive = (item.credits || 0) > 0 && item.status === "success";
    return (
      <View style={isDesktop ? { maxWidth: 820, width: "100%" } : undefined}>
        <View style={[styles.card, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
          <View style={[styles.icon, { backgroundColor: (colors.brandPrimary + "1A") }]}>
            <Ionicons name={item.mock ? "card-outline" : "wallet-outline"} size={18} color={colors.brandPrimary} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 14 }} numberOfLines={1}>
              {item.plan_name || "Template Credits"}
            </Text>
            <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }}>{fmtDate(item.created_at)}</Text>
            {item.reference ? (
              <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }} numberOfLines={1}>
                Ref: {item.reference}
              </Text>
            ) : null}
          </View>
          <View style={{ alignItems: "flex-end" }}>
            <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 14 }}>
              ₹{(item.amount ?? 0).toLocaleString("en-IN")}
            </Text>
            <Text style={{ color: positive ? colors.brandPrimary : colors.muted, fontSize: 12, marginTop: 2 }}>
              {positive ? "+" : ""}{item.credits ?? 0} credits
            </Text>
            <Text style={{ color: item.status === "success" ? "#1B7F4D" : colors.error, fontSize: 11, marginTop: 2, fontWeight: "600" }}>
              {(item.status || "unknown").toUpperCase()}
            </Text>
          </View>
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Pressable testID="txn-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
        </Pressable>
        <Text style={[styles.h1, { color: colors.onSurface }]}>Transaction History</Text>
        <View style={{ width: 24 }} />
      </View>

      {items === null ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.brandPrimary} size="large" />
          <Text style={{ color: colors.muted, marginTop: Spacing.md }}>Loading transactions…</Text>
        </View>
      ) : error ? (
        <View style={styles.center}>
          <Ionicons name="cloud-offline-outline" size={40} color={colors.muted} />
          <Text style={[styles.msg, { color: colors.onSurface }]}>{error}</Text>
          <Pressable
            testID="txn-retry"
            onPress={load}
            style={[styles.retry, { backgroundColor: colors.brandPrimary }]}
          >
            <Text style={{ color: colors.onBrandPrimary, fontWeight: "700" }}>Retry</Text>
          </Pressable>
        </View>
      ) : items.length === 0 ? (
        <View style={styles.center}>
          <Ionicons name="receipt-outline" size={40} color={colors.muted} />
          <Text style={[styles.msg, { color: colors.onSurface }]}>No transactions yet.</Text>
          <Text style={{ color: colors.muted, fontSize: 13, textAlign: "center", paddingHorizontal: Spacing.xl }}>
            Your wallet and purchase activity will appear here.
          </Text>
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(t) => t.id || t.created_at}
          contentContainerStyle={isDesktop ? { alignItems: "center", paddingBottom: 120 } : { padding: Spacing.lg, paddingBottom: 120 }}
          refreshing={refreshing}
          onRefresh={onRefresh}
          renderItem={renderTxn}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, borderBottomWidth: StyleSheet.hairlineWidth,
  },
  h1: { fontSize: 16, fontWeight: "700", fontFamily: "serif" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 8 },
  msg: { fontSize: 15, fontWeight: "600", marginTop: Spacing.sm, textAlign: "center", paddingHorizontal: Spacing.xl },
  retry: { marginTop: Spacing.md, paddingHorizontal: Spacing.xl, paddingVertical: Spacing.sm, borderRadius: Radius.md },
  card: {
    flexDirection: "row", alignItems: "center", gap: Spacing.md,
    padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1, marginBottom: Spacing.sm,
  },
  icon: { width: 38, height: 38, borderRadius: 12, alignItems: "center", justifyContent: "center" },
});

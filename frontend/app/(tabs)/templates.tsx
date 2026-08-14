import { useCallback, useEffect, useState } from "react";
import { FlatList, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";
import { DesktopPage } from "@/src/components/DesktopPage";

export default function Templates() {
  const { colors } = useTheme();
  const { isDesktop } = useResponsive();
  const params = useLocalSearchParams<{ cat?: string }>();
  const [q, setQ] = useState("");
  const [cat, setCat] = useState<string | null>(params.cat || null);
  const [items, setItems] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await api.templates(q || undefined, cat || undefined);
      setItems(Array.isArray(res) ? res : []);
    } catch (e: any) {
      setItems([]);
      setError(e?.message || "Could not load templates.");
    }
  }, [q, cat]);

  useEffect(() => { load(); }, [load]);

  const cats = ["All", "Civil", "Criminal", "General", "Bail", "Family", "Revenue"];

  // ------------------------- DESKTOP -------------------------
  if (isDesktop) {
    return (
      <DesktopPage
        title="Templates"
        subtitle={`${items.length} legal templates — English & ગુજરાતી`}
        actions={
          <View style={[styles.dSearch, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
            <Ionicons name="search" size={16} color={colors.muted} />
            <TextInput
              testID="tpl-search"
              placeholder="Search: mudat, adjournment, મુદત..."
              placeholderTextColor={colors.muted}
              value={q}
              onChangeText={setQ}
              style={{ flex: 1, color: colors.onSurface, marginLeft: Spacing.sm, minWidth: 240 }}
            />
          </View>
        }
      >
        <View style={{ flexDirection: "row", gap: Spacing.sm, flexWrap: "wrap" }}>
          {cats.map((c) => {
            const active = (c === "All" && !cat) || cat === c;
            return (
              <Pressable
                key={c}
                testID={`chip-${c.toLowerCase()}`}
                onPress={() => setCat(c === "All" ? null : c)}
                style={[
                  styles.dChip,
                  { backgroundColor: active ? colors.brandPrimary : colors.surfaceSecondary, borderColor: active ? colors.brandPrimary : colors.border },
                ]}
              >
                <Text style={{ color: active ? colors.onBrandPrimary : colors.onSurface, fontSize: 13, fontWeight: "700" }}>{c}</Text>
              </Pressable>
            );
          })}
        </View>

        {error ? (
          <View style={styles.dEmpty}>
            <Ionicons name="cloud-offline-outline" size={40} color={colors.muted} />
            <Text style={{ color: colors.onSurface, fontWeight: "700", marginTop: 12 }}>Couldn't load templates</Text>
            <Text style={{ color: colors.muted, fontSize: 13, marginTop: 4 }}>{error}</Text>
            <Pressable testID="tpl-error-retry" onPress={load} style={[styles.dEmptyBtn, { backgroundColor: colors.brandPrimary }]}>
              <Text style={{ color: colors.onBrandPrimary, fontWeight: "700" }}>Retry</Text>
            </Pressable>
          </View>
        ) : items.length === 0 ? (
          <View style={styles.dEmpty}>
            <Ionicons name="file-tray-outline" size={40} color={colors.muted} />
            <Text style={{ color: colors.onSurface, fontWeight: "700", marginTop: 12 }}>No templates found</Text>
            <Text style={{ color: colors.muted, fontSize: 13, marginTop: 4 }}>Try a different search term or category.</Text>
          </View>
        ) : (
          <View style={styles.dGrid}>
            {items.map((item) => (
              <Pressable
                key={item.id}
                testID={`tpl-${item.id}`}
                onPress={() => router.push({ pathname: "/template/[id]", params: { id: item.id } })}
                style={({ pressed }) => [
                  styles.dCard,
                  { backgroundColor: colors.surfaceSecondary, borderColor: colors.border },
                  pressed && { opacity: 0.85 },
                ]}
              >
                <View style={[styles.icon, { backgroundColor: colors.brandTertiary }]}>
                  <Ionicons name="document-text" size={20} color={colors.onBrandTertiary} />
                </View>
                <Text style={{ color: colors.onSurface, fontWeight: "700", marginTop: Spacing.sm, fontSize: 14 }} numberOfLines={2}>
                  {item.name_en}
                </Text>
                <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }} numberOfLines={1}>
                  {item.name_gu}
                </Text>
                <View style={[styles.dPill, { borderColor: colors.border }]}>
                  <Text style={{ color: colors.muted, fontSize: 11, fontWeight: "600" }}>{item.category}</Text>
                </View>
              </Pressable>
            ))}
          </View>
        )}
      </DesktopPage>
    );
  }

  // ------------------------- MOBILE (unchanged) -------------------------
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Text style={[styles.h1, { color: colors.onSurface }]}>Templates</Text>
        <Text style={{ color: colors.muted, fontSize: 12 }}>{items.length} available</Text>
      </View>

      <View style={[styles.searchBar, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
        <Ionicons name="search" size={18} color={colors.muted} />
        <TextInput
          testID="tpl-search"
          placeholder="Search: mudat, adjournment, મુદત..."
          placeholderTextColor={colors.muted}
          value={q}
          onChangeText={setQ}
          style={{ flex: 1, color: colors.onSurface, marginLeft: Spacing.sm }}
        />
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={{ maxHeight: 56, marginBottom: Spacing.sm }}
        contentContainerStyle={{ paddingHorizontal: Spacing.lg, gap: Spacing.sm, paddingVertical: Spacing.sm }}
      >
        {cats.map((c) => {
          const active = (c === "All" && !cat) || cat === c;
          return (
            <Pressable
              key={c}
              testID={`chip-${c.toLowerCase()}`}
              onPress={() => setCat(c === "All" ? null : c)}
              style={[
                styles.chip,
                {
                  backgroundColor: active ? colors.brandPrimary : colors.surfaceSecondary,
                  borderColor: active ? colors.brandPrimary : colors.border,
                  flexShrink: 0,
                },
              ]}
            >
              <Text style={{ color: active ? colors.onBrandPrimary : colors.onSurface, fontSize: 13, fontWeight: "700" }}>
                {c}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>

      {error ? (
        <View style={styles.errorBox}>
          <Ionicons name="cloud-offline-outline" size={40} color={colors.muted} />
          <Text style={{ color: colors.onSurface, fontWeight: "700", marginTop: 12 }}>Couldn't load templates</Text>
          <Text style={{ color: colors.muted, fontSize: 12, marginTop: 4, textAlign: "center", paddingHorizontal: Spacing.xl }}>
            {error}
          </Text>
          <Pressable
            testID="tpl-error-retry"
            onPress={load}
            style={[styles.retryBtn, { backgroundColor: colors.brandPrimary }]}
          >
            <Text style={{ color: colors.onBrandPrimary, fontWeight: "700" }}>Retry</Text>
          </Pressable>
        </View>
      ) : (
      <FlatList
        data={items}
        keyExtractor={(t) => t.id}
        numColumns={2}
        columnWrapperStyle={{ gap: Spacing.md, paddingHorizontal: Spacing.lg }}
        contentContainerStyle={{ gap: Spacing.md, paddingBottom: Spacing.xxxl }}
        renderItem={({ item }) => (
          <Pressable
            testID={`tpl-${item.id}`}
            onPress={() => router.push({ pathname: "/template/[id]", params: { id: item.id } })}
            style={[styles.card, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
          >
            <View style={[styles.icon, { backgroundColor: colors.brandTertiary }]}>
              <Ionicons name="document-text" size={20} color={colors.onBrandTertiary} />
            </View>
            <Text style={{ color: colors.onSurface, fontWeight: "700", marginTop: Spacing.sm, fontSize: 14 }} numberOfLines={2}>
              {item.name_en}
            </Text>
            <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }} numberOfLines={1}>
              {item.name_gu}
            </Text>
            <View style={[styles.catPill, { borderColor: colors.border }]}>
              <Text style={{ color: colors.muted, fontSize: 10, fontWeight: "600" }}>{item.category}</Text>
            </View>
          </Pressable>
        )}
      />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  h1: { fontSize: 22, fontWeight: "700", fontFamily: "serif" },
  searchBar: {
    flexDirection: "row", alignItems: "center", margin: Spacing.lg, marginBottom: Spacing.sm,
    paddingHorizontal: Spacing.md, height: 44, borderRadius: Radius.md, borderWidth: 1,
  },
  chip: {
    height: 36, paddingHorizontal: Spacing.lg, borderRadius: 999,
    borderWidth: 1, alignItems: "center", justifyContent: "center",
  },
  card: {
    flex: 1, padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1, minHeight: 130,
  },
  icon: { width: 36, height: 36, borderRadius: 10, alignItems: "center", justifyContent: "center" },
  catPill: {
    alignSelf: "flex-start", paddingHorizontal: 8, paddingVertical: 3,
    borderRadius: 6, borderWidth: 1, marginTop: Spacing.sm,
  },
  errorBox: { alignItems: "center", marginTop: Spacing.xxxl, paddingHorizontal: Spacing.xl, gap: 4 },
  retryBtn: { marginTop: Spacing.xl, paddingHorizontal: Spacing.xl, paddingVertical: Spacing.md, borderRadius: 999 },
  // Desktop
  dSearch: {
    flexDirection: "row", alignItems: "center",
    paddingHorizontal: Spacing.md, height: 42, borderRadius: Radius.md, borderWidth: 1,
  },
  dChip: {
    height: 34, paddingHorizontal: Spacing.lg, borderRadius: 999, borderWidth: 1,
    alignItems: "center", justifyContent: "center",
  },
  dPill: {
    alignSelf: "flex-start", paddingHorizontal: 8, paddingVertical: 3,
    borderRadius: 6, borderWidth: 1, marginTop: Spacing.sm,
  },
  dEmpty: { alignItems: "center", paddingVertical: Spacing.xxxl, gap: 6 },
  dEmptyBtn: { marginTop: Spacing.md, paddingHorizontal: Spacing.xl, paddingVertical: Spacing.md, borderRadius: 999 },
  dGrid: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.lg },
  dCard: {
    width: "23.5%", minWidth: 220, padding: Spacing.lg,
    borderRadius: 14, borderWidth: 1, minHeight: 160,
  },
});

import { useCallback, useState } from "react";
import { FlatList, Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";

const FILTERS = ["All", "Civil", "Criminal", "Other"];
const SORTS: { id: string; label: string; icon: any }[] = [
  { id: "updated", label: "Recently Updated", icon: "time-outline" },
  { id: "name", label: "Name (A-Z)", icon: "text-outline" },
  { id: "type", label: "Case Type", icon: "pricetag-outline" },
];

function timeAgo(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString();
}

export default function Cases() {
  const { colors } = useTheme();
  const [cases, setCases] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("All");
  const [showArchived, setShowArchived] = useState(false);
  const [sort, setSort] = useState("updated");
  const [sortOpen, setSortOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (query: string, cat: string, archived: boolean, sortBy: string) => {
    setLoading(true);
    try {
      const c = await api.listCases({
        q: query || undefined,
        category: cat !== "All" ? cat : undefined,
        status: archived ? "archived" : "active",
        sort: sortBy,
      });
      setCases(Array.isArray(c) ? c : []);
    } catch {
      setCases([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(q, filter, showArchived, sort); }, [load, q, filter, showArchived, sort]));

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Text style={[styles.h1, { color: colors.onSurface }]}>My Cases</Text>
        <View style={{ flexDirection: "row", gap: Spacing.sm }}>
          <Pressable
            testID="archive-toggle"
            onPress={() => setShowArchived((s) => !s)}
            style={[styles.iconBtnGhost, { borderColor: colors.border, backgroundColor: showArchived ? colors.brandTertiary : "transparent" }]}
          >
            <Ionicons name="archive-outline" size={20} color={showArchived ? colors.onBrandTertiary : colors.muted} />
          </Pressable>
          <Pressable
            testID="new-case-btn"
            onPress={() => router.push("/case/new")}
            style={[styles.iconBtn, { backgroundColor: colors.brandPrimary }]}
          >
            <Ionicons name="add" size={22} color={colors.onBrandPrimary} />
          </Pressable>
        </View>
      </View>

      <View style={[styles.searchBar, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
        <Ionicons name="search" size={18} color={colors.muted} />
        <TextInput
          testID="cases-search-input"
          placeholder="Search by nickname, party, number, type..."
          placeholderTextColor={colors.muted}
          value={q}
          onChangeText={setQ}
          style={{ flex: 1, color: colors.onSurface, marginLeft: Spacing.sm }}
        />
      </View>

      <View style={styles.filterRow}>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={{ flex: 1 }}
          contentContainerStyle={{ paddingLeft: Spacing.lg, gap: Spacing.sm, paddingVertical: Spacing.sm }}
        >
          {FILTERS.map((f) => {
            const active = filter === f;
            return (
              <Pressable
                key={f}
                testID={`filter-${f.toLowerCase()}`}
                onPress={() => setFilter(f)}
                style={[
                  styles.chip,
                  { backgroundColor: active ? colors.brandPrimary : colors.surfaceSecondary, borderColor: active ? colors.brandPrimary : colors.border, flexShrink: 0 },
                ]}
              >
                <Text style={{ color: active ? colors.onBrandPrimary : colors.onSurface, fontSize: 13, fontWeight: "700" }}>{f}</Text>
              </Pressable>
            );
          })}
        </ScrollView>
        <Pressable
          testID="sort-btn"
          onPress={() => setSortOpen(true)}
          style={[styles.sortBtn, { borderColor: colors.border, backgroundColor: colors.surfaceSecondary }]}
        >
          <Ionicons name="swap-vertical" size={16} color={colors.onSurface} />
          <Text style={{ color: colors.onSurface, fontSize: 12, fontWeight: "700", marginLeft: 4 }}>Sort</Text>
        </Pressable>
      </View>

      <Modal visible={sortOpen} transparent animationType="fade" onRequestClose={() => setSortOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setSortOpen(false)}>
          <Pressable style={[styles.sortSheet, { backgroundColor: colors.surface, borderColor: colors.border }]} onPress={(e) => e.stopPropagation()}>
            <Text style={[styles.sortTitle, { color: colors.onSurface }]}>Sort Cases By</Text>
            {SORTS.map((s) => {
              const active = sort === s.id;
              return (
                <Pressable
                  key={s.id}
                  testID={`sort-${s.id}`}
                  onPress={() => { setSort(s.id); setSortOpen(false); }}
                  style={[styles.sortOpt, { borderBottomColor: colors.divider }]}
                >
                  <Ionicons name={s.icon} size={18} color={active ? colors.brandPrimary : colors.muted} />
                  <Text style={{ color: active ? colors.brandPrimary : colors.onSurface, fontWeight: active ? "700" : "500", flex: 1, marginLeft: Spacing.md }}>{s.label}</Text>
                  {active ? <Ionicons name="checkmark" size={20} color={colors.brandPrimary} /> : null}
                </Pressable>
              );
            })}
          </Pressable>
        </Pressable>
      </Modal>

      <FlatList
        data={cases}
        keyExtractor={(c) => c.id}
        contentContainerStyle={{ padding: Spacing.lg, paddingTop: Spacing.sm, paddingBottom: Spacing.xxxl }}
        ItemSeparatorComponent={() => <View style={{ height: Spacing.sm }} />}
        ListEmptyComponent={
          !loading ? (
            <View style={styles.empty}>
              <Ionicons name={showArchived ? "archive-outline" : "folder-open-outline"} size={44} color={colors.muted} />
              <Text style={{ color: colors.onSurface, fontWeight: "700", marginTop: 12 }}>
                {showArchived ? "No archived cases" : "No cases yet"}
              </Text>
              {!showArchived && (
                <>
                  <Text style={{ color: colors.muted, fontSize: 12, marginTop: 4, textAlign: "center" }}>
                    Create your first case to start generating court applications.
                  </Text>
                  <Pressable
                    testID="empty-add-case"
                    onPress={() => router.push("/case/new")}
                    style={[styles.emptyBtn, { backgroundColor: colors.brandPrimary }]}
                  >
                    <Text style={{ color: colors.onBrandPrimary, fontWeight: "700" }}>Add New Case</Text>
                  </Pressable>
                </>
              )}
            </View>
          ) : null
        }
        renderItem={({ item }) => (
          <Pressable
            testID={`case-item-${item.id}`}
            onPress={() => router.push({ pathname: "/case/[id]", params: { id: item.id } })}
            style={[styles.card, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
          >
            <View style={styles.cardTop}>
              <View style={{ flex: 1 }}>
                <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 15 }} numberOfLines={1}>
                  {item.nickname || item.party_name || item.case_type_label || "Untitled Case"}
                </Text>
                <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }} numberOfLines={1}>
                  {item.case_number ? `${item.case_number} • ` : ""}{item.case_type_label || "Case"}
                </Text>
              </View>
              <View style={[styles.catPill, { backgroundColor: item.category === "Criminal" ? "#7A1C1C20" : colors.brandTertiary }]}>
                <Text style={{ color: item.category === "Criminal" ? "#7A1C1C" : colors.onBrandTertiary, fontSize: 10, fontWeight: "700" }}>
                  {item.category || "Other"}
                </Text>
              </View>
            </View>
            <View style={styles.cardBottom}>
              {item.party_name ? (
                <View style={styles.metaItem}>
                  <Ionicons name="person-outline" size={12} color={colors.muted} />
                  <Text style={{ color: colors.muted, fontSize: 11, marginLeft: 4 }} numberOfLines={1}>{item.party_name}</Text>
                </View>
              ) : null}
              <View style={styles.metaItem}>
                <Ionicons name="time-outline" size={12} color={colors.muted} />
                <Text style={{ color: colors.muted, fontSize: 11, marginLeft: 4 }}>{timeAgo(item.updated_at)}</Text>
              </View>
              <View style={[styles.langPill, { backgroundColor: colors.surfaceTertiary }]}>
                <Text style={{ color: colors.onSurfaceTertiary, fontSize: 10, fontWeight: "700" }}>{item.language === "gu" ? "ગુ" : "EN"}</Text>
              </View>
            </View>
            {item.last_used_template ? (
              <Text style={{ color: colors.brandPrimary, fontSize: 11, marginTop: Spacing.sm }} numberOfLines={1}>
                Last application: {item.last_used_template}
              </Text>
            ) : null}
          </Pressable>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, borderBottomWidth: StyleSheet.hairlineWidth,
  },
  h1: { fontSize: 22, fontWeight: "700", fontFamily: "serif" },
  iconBtn: { width: 40, height: 40, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  iconBtnGhost: { width: 40, height: 40, borderRadius: 12, alignItems: "center", justifyContent: "center", borderWidth: 1 },
  searchBar: {
    flexDirection: "row", alignItems: "center", marginHorizontal: Spacing.lg, marginTop: Spacing.lg,
    paddingHorizontal: Spacing.md, height: 44, borderRadius: Radius.md, borderWidth: 1,
  },
  chip: { height: 36, paddingHorizontal: Spacing.lg, borderRadius: 999, borderWidth: 1, alignItems: "center", justifyContent: "center" },
  filterRow: { flexDirection: "row", alignItems: "center", maxHeight: 56 },
  sortBtn: {
    flexDirection: "row", alignItems: "center", height: 36, paddingHorizontal: Spacing.md,
    borderRadius: 999, borderWidth: 1, marginRight: Spacing.lg, marginLeft: Spacing.sm, flexShrink: 0,
  },
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: "flex-end" },
  sortSheet: { borderTopLeftRadius: Radius.lg, borderTopRightRadius: Radius.lg, borderWidth: 1, padding: Spacing.lg, paddingBottom: 32 },
  sortTitle: { fontSize: 16, fontWeight: "700", marginBottom: Spacing.md },
  sortOpt: { flexDirection: "row", alignItems: "center", paddingVertical: Spacing.md, borderBottomWidth: StyleSheet.hairlineWidth },
  card: { padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1 },
  cardTop: { flexDirection: "row", alignItems: "center" },
  cardBottom: { flexDirection: "row", alignItems: "center", gap: Spacing.md, marginTop: Spacing.sm },
  metaItem: { flexDirection: "row", alignItems: "center", maxWidth: "45%" },
  catPill: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  langPill: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999, marginLeft: "auto" },
  empty: { alignItems: "center", marginTop: Spacing.xxxl, paddingHorizontal: Spacing.xl },
  emptyBtn: { marginTop: Spacing.xl, paddingHorizontal: Spacing.xl, paddingVertical: Spacing.md, borderRadius: 999 },
});

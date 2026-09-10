import { useEffect, useMemo, useState } from "react";
import { FlatList, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router, useLocalSearchParams } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";
import { DesktopPage } from "@/src/components/DesktopPage";
import { searchTemplatePairs, SearchMatchedPair } from "@/src/utils/templateSearch";
import { TemplateLogicalPair, getOrderedTemplatePairs } from "@/src/data/templateCatalogPairs";
import { catalogCache } from "@/src/services/catalogCache";
import { LanguageSelectModal } from "@/src/components/LanguageSelectModal";

export default function Templates() {
  const { colors } = useTheme();
  const { isDesktop } = useResponsive();
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ cat?: string }>();

  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [cat, setCat] = useState<string | null>(params.cat || null);
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set());
  const [templateOrder, setTemplateOrder] = useState<string[] | null>(() => catalogCache.peekTemplateOrder());
  const [selectedPair, setSelectedPair] = useState<TemplateLogicalPair | null>(null);

  // Debounce search query by 150ms to prevent expensive re-renders while typing
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQ(q);
    }, 150);
    return () => clearTimeout(timer);
  }, [q]);

  // Fetch authoritative template order
  useEffect(() => {
    catalogCache.getTemplateOrder().then((order) => {
      if (Array.isArray(order) && order.length > 0) {
        setTemplateOrder(order);
      }
    }).catch(() => {});
  }, []);

  const orderedBasePairs = useMemo(() => {
    return getOrderedTemplatePairs(templateOrder);
  }, [templateOrder]);

  // Load user favorites on mount
  useEffect(() => {
    api.favTemplates()
      .then((res: any) => {
        if (Array.isArray(res)) {
          setFavoriteIds(new Set(res.map((f: any) => (typeof f === "string" ? f : f?.id))));
        }
      })
      .catch(() => {});
  }, []);

  const toggleFavorite = async (pair: TemplateLogicalPair, e?: any) => {
    if (e && typeof e.stopPropagation === "function") {
      e.stopPropagation();
    }
    const isFav = favoriteIds.has(pair.guId) || favoriteIds.has(pair.enId) || favoriteIds.has(pair.baseKey);
    const nextSet = new Set(favoriteIds);
    if (isFav) {
      nextSet.delete(pair.guId);
      nextSet.delete(pair.enId);
      nextSet.delete(pair.baseKey);
      setFavoriteIds(nextSet);
      try {
        await Promise.all([
          api.removeFavTemplate(pair.guId).catch(() => {}),
          api.removeFavTemplate(pair.enId).catch(() => {}),
        ]);
      } catch {
      }
    } else {
      nextSet.add(pair.guId);
      nextSet.add(pair.enId);
      nextSet.add(pair.baseKey);
      setFavoriteIds(nextSet);
      try {
        await Promise.all([
          api.addFavTemplate(pair.guId).catch(() => {}),
          api.addFavTemplate(pair.enId).catch(() => {}),
        ]);
      } catch {
      }
    }
  };

  // Perform deterministic bilingual search & category filter over authoritative ordered pairs
  const matchedPairs: SearchMatchedPair[] = useMemo(() => {
    return searchTemplatePairs(debouncedQ, cat, favoriteIds, orderedBasePairs);
  }, [debouncedQ, cat, favoriteIds, orderedBasePairs]);

  const cats = ["All", "Favorites", "Civil", "Criminal", "General", "Bail"];

  const openTemplate = (id: string, e?: any) => {
    if (e && typeof e.stopPropagation === "function") {
      e.stopPropagation();
    }
    router.push({ pathname: "/template/[id]", params: { id } });
  };

  // ------------------------- DESKTOP -------------------------
  if (isDesktop) {
    return (
      <DesktopPage
        title="Legal Templates"
        subtitle="21 Authoritative Court Applications — ગુજરાતી & English"
        actions={
          <View style={[styles.dSearch, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
            <Ionicons name="search" size={16} color={colors.muted} />
            <TextInput
              testID="tpl-search"
              placeholder="Search: mudat, warrant, jamin, મુદત, વોરંટ..."
              placeholderTextColor={colors.muted}
              value={q}
              onChangeText={setQ}
              style={{ flex: 1, color: colors.onSurface, marginLeft: Spacing.sm, minWidth: 260 }}
            />
            {q ? (
              <Pressable onPress={() => setQ("")} hitSlop={8}>
                <Ionicons name="close-circle" size={16} color={colors.muted} />
              </Pressable>
            ) : null}
          </View>
        }
      >
        <View style={{ flexDirection: "row", gap: Spacing.sm, flexWrap: "wrap", marginBottom: Spacing.md }}>
          {cats.map((c) => {
            const active = (c === "All" && !cat) || cat === c;
            return (
              <Pressable
                key={c}
                testID={`chip-${c.toLowerCase()}`}
                onPress={() => setCat(c === "All" ? null : c)}
                style={[
                  styles.dChip,
                  {
                    backgroundColor: active ? colors.brandPrimary : colors.surfaceSecondary,
                    borderColor: active ? colors.brandPrimary : colors.border,
                  },
                ]}
              >
                <Text style={{ color: active ? colors.onBrandPrimary : colors.onSurface, fontSize: 13, fontWeight: "700" }}>
                  {c === "Favorites" ? "⭐ " : ""}
                  {c}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {matchedPairs.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Ionicons name="search-outline" size={48} color={colors.muted} />
            <Text style={[styles.emptyTitle, { color: colors.onSurface }]}>કોઈ સંબંધિત અરજી મળી નથી</Text>
            <Text style={[styles.emptySubtitle, { color: colors.muted }]}>No related application found</Text>
            <Text style={[styles.emptyHint, { color: colors.muted }]}>
              કૃપા કરીને બીજો શબ્દ શોધો — Try searching with different keywords
            </Text>
            <Pressable
              testID="tpl-empty-reset"
              onPress={() => {
                setQ("");
                setCat(null);
              }}
              style={[styles.clearBtn, { backgroundColor: colors.brandPrimary }]}
            >
              <Text style={{ color: colors.onBrandPrimary, fontWeight: "700" }}>બધી અરજીઓ જુઓ (View All)</Text>
            </Pressable>
          </View>
        ) : (
          <View style={styles.dGrid}>
            {matchedPairs.map(({ pair, is_favorite }) => (
              <Pressable
                key={pair.baseKey}
                testID={`tpl-pair-${pair.baseKey}`}
                onPress={() => setSelectedPair(pair)}
                style={({ pressed }) => [
                  styles.dCard,
                  { backgroundColor: colors.surfaceSecondary, borderColor: colors.border },
                  pressed && { opacity: 0.9 },
                ]}
              >
                <View style={{ flex: 1 }}>
                  <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                    <View style={[styles.catPill, { backgroundColor: colors.surface, borderColor: colors.border }]}>
                      <Text style={{ color: colors.brandPrimary, fontSize: 11, fontWeight: "700" }}>{pair.category}</Text>
                    </View>
                    <Pressable
                      testID={`tpl-fav-${pair.baseKey}`}
                      hitSlop={8}
                      onPress={(e) => toggleFavorite(pair, e)}
                      style={styles.favBtn}
                    >
                      <Ionicons
                        name={is_favorite ? "star" : "star-outline"}
                        size={20}
                        color={is_favorite ? "#E5A93C" : colors.muted}
                      />
                    </Pressable>
                  </View>

                  {/* Clean Legal Titles */}
                  <Text style={{ color: colors.onSurface, fontWeight: "700", marginTop: Spacing.sm, fontSize: 15, lineHeight: 22 }} numberOfLines={2}>
                    {pair.name_gu}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 12, marginTop: 4, fontWeight: "600" }} numberOfLines={2}>
                    {pair.name_en}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 11, marginTop: 6, opacity: 0.85 }} numberOfLines={2}>
                    {pair.description_gu}
                  </Text>
                </View>

                {/* Subtle Action Cue */}
                <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: Spacing.md, paddingTop: Spacing.xs, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border }}>
                  <Text style={{ color: colors.brandPrimary, fontSize: 12, fontWeight: "600" }}>Draft / અરજી તૈયાર કરો</Text>
                  <Ionicons name="chevron-forward" size={16} color={colors.brandPrimary} />
                </View>
              </Pressable>
            ))}
          </View>
        )}
        <LanguageSelectModal
          visible={selectedPair !== null}
          onClose={() => setSelectedPair(null)}
          templateNameGu={selectedPair?.name_gu}
          templateNameEn={selectedPair?.name_en}
          category={selectedPair?.category}
          onSelect={(lang) => {
            if (selectedPair) {
              const id = lang === "gu" ? selectedPair.guId : selectedPair.enId;
              router.push({ pathname: "/template/[id]", params: { id, lang } });
              setSelectedPair(null);
            }
          }}
        />
      </DesktopPage>
    );
  }

  // ------------------------- MOBILE -------------------------
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Text style={[styles.h1, { color: colors.onSurface }]}>Legal Templates</Text>
        <Text style={{ color: colors.muted, fontSize: 12 }}>{matchedPairs.length} of 21 applications</Text>
      </View>

      {/* Search Input Bar */}
      <View style={[styles.searchBar, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
        <Ionicons name="search" size={18} color={colors.muted} />
        <TextInput
          testID="tpl-search"
          placeholder="Search: mudat, warrant, jamin, મુદત..."
          placeholderTextColor={colors.muted}
          value={q}
          onChangeText={setQ}
          style={{ flex: 1, color: colors.onSurface, marginLeft: Spacing.sm, fontSize: 14 }}
        />
        {q ? (
          <Pressable onPress={() => setQ("")} hitSlop={8}>
            <Ionicons name="close-circle" size={18} color={colors.muted} />
          </Pressable>
        ) : null}
      </View>

      {/* Category Filter Chips */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={{ height: 46, marginBottom: Spacing.xs, flexGrow: 0 }}
        contentContainerStyle={{ paddingHorizontal: Spacing.lg, gap: Spacing.sm, alignItems: "center" }}
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
                },
              ]}
            >
              <Text style={{ color: active ? colors.onBrandPrimary : colors.onSurface, fontSize: 12, fontWeight: "700" }}>
                {c === "Favorites" ? "⭐ " : ""}
                {c}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>

      {/* Results List */}
      {matchedPairs.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Ionicons name="search-outline" size={44} color={colors.muted} />
          <Text style={[styles.emptyTitle, { color: colors.onSurface }]}>કોઈ સંબંધિત અરજી મળી નથી</Text>
          <Text style={[styles.emptySubtitle, { color: colors.muted }]}>No related application found</Text>
          <Text style={[styles.emptyHint, { color: colors.muted }]}>
            કૃપા કરીને બીજો શબ્દ શોધો — Try searching with different keywords
          </Text>
          <Pressable
            testID="tpl-empty-reset"
            onPress={() => {
              setQ("");
              setCat(null);
            }}
            style={[styles.clearBtn, { backgroundColor: colors.brandPrimary }]}
          >
            <Text style={{ color: colors.onBrandPrimary, fontWeight: "700" }}>બધી અરજીઓ જુઓ (View All)</Text>
          </Pressable>
        </View>
      ) : (
        <FlatList
          style={{ flex: 1 }}
          data={matchedPairs}
          keyExtractor={(item) => item.pair.baseKey}
          numColumns={2}
          initialNumToRender={10}
          maxToRenderPerBatch={10}
          windowSize={5}
          removeClippedSubviews={Platform.OS !== "web"}
          columnWrapperStyle={styles.mobileColWrapper}
          contentContainerStyle={{
            paddingHorizontal: Spacing.md,
            paddingTop: Spacing.xs,
            paddingBottom: Math.max(90, 60 + insets.bottom + Spacing.xl),
            gap: Spacing.sm,
          }}
          renderItem={({ item }) => {
            const { pair, is_favorite } = item;
            return (
              <Pressable
                testID={`tpl-pair-${pair.baseKey}`}
                onPress={() => setSelectedPair(pair)}
                style={[
                  styles.card,
                  { backgroundColor: colors.surfaceSecondary, borderColor: colors.border },
                ]}
              >
                <View style={{ flex: 1 }}>
                  <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                    <View style={[styles.catPill, { backgroundColor: colors.surface, borderColor: colors.border }]}>
                      <Text style={{ color: colors.brandPrimary, fontSize: 10, fontWeight: "700" }}>{pair.category}</Text>
                    </View>
                    <Pressable
                      testID={`tpl-fav-${pair.baseKey}`}
                      hitSlop={8}
                      onPress={(e) => toggleFavorite(pair, e)}
                      style={styles.favBtn}
                    >
                      <Ionicons
                        name={is_favorite ? "star" : "star-outline"}
                        size={20}
                        color={is_favorite ? "#E5A93C" : colors.muted}
                      />
                    </Pressable>
                  </View>

                  {/* Clean Gujarati Title */}
                  <Text style={{ color: colors.onSurface, fontWeight: "700", marginTop: Spacing.xs, fontSize: 15, lineHeight: 21 }}>
                    {pair.name_gu}
                  </Text>

                  {/* Clean English Subtitle */}
                  <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2, fontWeight: "600" }}>
                    {pair.name_en}
                  </Text>

                  {/* Description */}
                  <Text style={{ color: colors.muted, fontSize: 11, marginTop: 4, opacity: 0.85 }} numberOfLines={2}>
                    {pair.description_gu}
                  </Text>
                </View>

                {/* Subtle Action Cue */}
                <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: Spacing.sm, paddingTop: Spacing.xs, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border }}>
                  <Text style={{ color: colors.brandPrimary, fontSize: 11, fontWeight: "600" }}>Draft / અરજી તૈયાર કરો</Text>
                  <Ionicons name="chevron-forward" size={14} color={colors.brandPrimary} />
                </View>
              </Pressable>
            );
          }}
        />
      )}
      <LanguageSelectModal
        visible={selectedPair !== null}
        onClose={() => setSelectedPair(null)}
        templateNameGu={selectedPair?.name_gu}
        templateNameEn={selectedPair?.name_en}
        category={selectedPair?.category}
        onSelect={(lang) => {
          if (selectedPair) {
            const id = lang === "gu" ? selectedPair.guId : selectedPair.enId;
            router.push({ pathname: "/template/[id]", params: { id, lang } });
            setSelectedPair(null);
          }
        }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  h1: { fontSize: 22, fontWeight: "700", fontFamily: "serif" },
  searchBar: {
    flexDirection: "row",
    alignItems: "center",
    marginHorizontal: Spacing.lg,
    marginVertical: Spacing.sm,
    paddingHorizontal: Spacing.md,
    height: 44,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  chip: {
    height: 34,
    paddingHorizontal: Spacing.md,
    borderRadius: 999,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  mobileColWrapper: {
    justifyContent: "space-between",
  },
  card: {
    width: "48.5%",
    padding: Spacing.sm,
    borderRadius: Radius.md,
    borderWidth: 1,
    justifyContent: "space-between",
    minHeight: 165,
    marginBottom: Spacing.xs,
  },
  catPill: {
    alignSelf: "flex-start",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    borderWidth: 1,
  },
  favBtn: { padding: 4 },
  actionButtonRow: {
    flexDirection: "row",
    gap: Spacing.sm,
    marginTop: Spacing.sm,
    paddingTop: Spacing.xs,
  },
  langBtn: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: Radius.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  langBtnText: {
    fontSize: 12,
    fontWeight: "700",
  },
  emptyContainer: {
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: Spacing.xxxl,
    paddingHorizontal: Spacing.xl,
    gap: 6,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: "700",
    marginTop: Spacing.sm,
    textAlign: "center",
  },
  emptySubtitle: {
    fontSize: 13,
    fontWeight: "600",
    textAlign: "center",
  },
  emptyHint: {
    fontSize: 12,
    marginTop: 4,
    textAlign: "center",
  },
  clearBtn: {
    marginTop: Spacing.lg,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    borderRadius: 999,
  },
  // Desktop
  dSearch: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: Spacing.md,
    height: 42,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  dChip: {
    height: 34,
    paddingHorizontal: Spacing.lg,
    borderRadius: 999,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  dGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    gap: Spacing.md,
  },
  dCard: {
    width: "48.5%",
    padding: Spacing.lg,
    borderRadius: 14,
    borderWidth: 1,
    minHeight: 180,
    justifyContent: "space-between",
  },
});

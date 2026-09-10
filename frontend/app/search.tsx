import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";
import { searchTemplatePairs, SearchMatchedPair } from "@/src/utils/templateSearch";

interface SearchResults {
  cases: any[];
  templatePairs: SearchMatchedPair[];
}

export default function Search() {
  const { colors } = useTheme();
  const { isDesktop } = useResponsive();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResults | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<TextInput>(null);
  const debounceRef = useRef<any>(null);

  const run = useCallback(async (query: string) => {
    const trimmed = query.trim();
    if (!trimmed) {
      setResults(null);
      setError(null);
      return;
    }
    setSearching(true);
    setError(null);
    try {
      const [res, matchedPairs] = await Promise.all([
        api.search(trimmed).catch(() => ({ cases: [] })),
        Promise.resolve(searchTemplatePairs(trimmed)),
      ]);
      setResults({
        cases: Array.isArray(res?.cases) ? res.cases : [],
        templatePairs: matchedPairs.slice(0, 10),
      });
    } catch (e: any) {
      setError(e?.message || "Could not search. Please try again.");
      setResults(null);
    } finally {
      setSearching(false);
    }
  }, []);

  const onChange = (text: string) => {
    setQ(text);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => run(text), 300);
  };

  useEffect(() => {
    const t = setTimeout(() => inputRef.current?.focus(), 250);
    return () => clearTimeout(t);
  }, []);

  const total = (results?.cases.length || 0) + (results?.templatePairs.length || 0);

  const renderCase = ({ item }: { item: any }) => (
    <Pressable
      testID={`search-case-${item.id}`}
      onPress={() => router.push({ pathname: "/case/[id]", params: { id: item.id } })}
      style={[styles.card, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
    >
      <View style={[styles.icon, { backgroundColor: (colors.brandPrimary + "1A") }]}>
        <Ionicons name="folder-open" size={18} color={colors.brandPrimary} />
      </View>
      <View style={{ flex: 1, marginLeft: Spacing.md }}>
        <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 14 }} numberOfLines={1}>
          {item.nickname || item.case_number || "Case"}
        </Text>
        <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }} numberOfLines={1}>
          {[item.case_number, item.party_name].filter(Boolean).join(" · ")}
        </Text>
      </View>
      <Ionicons name="chevron-forward" size={18} color={colors.muted} />
    </Pressable>
  );

  const renderTemplatePair = ({ item }: { item: SearchMatchedPair }) => (
    <View
      style={[
        styles.card,
        {
          backgroundColor: colors.surfaceSecondary,
          borderColor: colors.border,
          flexDirection: "column",
          alignItems: "stretch",
          gap: 8,
        },
      ]}
    >
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: Spacing.sm, flex: 1 }}>
          <View style={[styles.icon, { backgroundColor: colors.brandTertiary }]}>
            <Ionicons name="document-text" size={18} color={colors.onBrandTertiary} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 14 }} numberOfLines={1}>
              {item.pair.name_gu}
            </Text>
            <Text style={{ color: colors.muted, fontSize: 12 }} numberOfLines={1}>
              {item.pair.name_en}
            </Text>
          </View>
        </View>
        <View
          style={{
            paddingHorizontal: 8,
            paddingVertical: 2,
            borderRadius: 6,
            borderWidth: 1,
            borderColor: colors.border,
            backgroundColor: colors.surface,
          }}
        >
          <Text style={{ color: colors.brandPrimary, fontSize: 10, fontWeight: "700" }}>{item.pair.category}</Text>
        </View>
      </View>

      <View style={{ flexDirection: "row", gap: Spacing.sm, marginTop: 4 }}>
        <Pressable
          testID={`search-btn-gu-${item.pair.baseKey}`}
          onPress={() => router.push({ pathname: "/template/[id]", params: { id: item.pair.guId, lang: "gu" } })}
          style={({ pressed }) => [
            styles.langBtn,
            { backgroundColor: colors.brandPrimary },
            pressed && { opacity: 0.8 },
          ]}
        >
          <Text style={[styles.langBtnText, { color: colors.onBrandPrimary }]}>ગુજરાતી</Text>
        </Pressable>
        <Pressable
          testID={`search-btn-en-${item.pair.baseKey}`}
          onPress={() => router.push({ pathname: "/template/[id]", params: { id: item.pair.enId, lang: "en" } })}
          style={({ pressed }) => [
            styles.langBtn,
            { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
            pressed && { opacity: 0.8 },
          ]}
        >
          <Text style={[styles.langBtnText, { color: colors.onSurface }]}>English</Text>
        </Pressable>
      </View>
    </View>
  );

  const sectionHeader = (title: string, count: number) => (
    <Text style={[styles.sectionTitle, { color: colors.onSurface }]}>
      {title} <Text style={{ color: colors.muted, fontWeight: "600" }}>({count})</Text>
    </Text>
  );

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Pressable testID="search-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
        </Pressable>
        <View style={[styles.inputWrap, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
          <Ionicons name="search" size={18} color={colors.muted} />
          <TextInput
            ref={inputRef}
            testID="global-search-input"
            placeholder="Search cases, templates, ગુજરાતી..."
            placeholderTextColor={colors.muted}
            value={q}
            onChangeText={onChange}
            autoCapitalize="none"
            style={{ flex: 1, color: colors.onSurface, marginLeft: Spacing.sm, height: 44 }}
          />
          {searching && <ActivityIndicator size="small" color={colors.brandPrimary} />}
          {q.length > 0 && !searching && (
            <Pressable onPress={() => { setQ(""); setResults(null); }} hitSlop={8} testID="search-clear">
              <Ionicons name="close-circle" size={18} color={colors.muted} />
            </Pressable>
          )}
        </View>
      </View>

      {error ? (
        <View style={styles.center}>
          <Ionicons name="cloud-offline-outline" size={40} color={colors.muted} />
          <Text style={[styles.msg, { color: colors.onSurface }]}>{error}</Text>
          <Pressable
            testID="search-retry"
            onPress={() => run(q)}
            style={[styles.retry, { backgroundColor: colors.brandPrimary }]}
          >
            <Text style={{ color: colors.onBrandPrimary, fontWeight: "700" }}>Retry</Text>
          </Pressable>
        </View>
      ) : !results ? (
        <View style={styles.center}>
          <Ionicons name="search-outline" size={40} color={colors.muted} />
          <Text style={[styles.msg, { color: colors.onSurface }]}>
            Search your cases and legal templates
          </Text>
          <Text style={{ color: colors.muted, fontSize: 13, textAlign: "center", paddingHorizontal: Spacing.xl }}>
            Try a case number, party name, or template name like &quot;mudat&quot; / &quot;મુદત&quot;.
          </Text>
        </View>
      ) : total === 0 ? (
        <View style={styles.center}>
          <Ionicons name="file-tray-outline" size={40} color={colors.muted} />
          <Text style={[styles.msg, { color: colors.onSurface }]}>
            કોઈ પરિણામ મળ્યા નથી &mdash; No results for &quot;{q.trim()}&quot;
          </Text>
          <Text style={{ color: colors.muted, fontSize: 13, textAlign: "center", paddingHorizontal: Spacing.xl }}>
            કૃપા કરીને બીજો શબ્દ શોધો / Check the spelling or try a different term.
          </Text>
        </View>
      ) : (
        <FlatList
          data={[0]}
          keyExtractor={() => "root"}
          contentContainerStyle={isDesktop ? { alignItems: "center" } : undefined}
          renderItem={() => (
            <View style={isDesktop ? { maxWidth: 820, width: "100%", paddingBottom: 120 } : { paddingHorizontal: Spacing.lg, paddingBottom: 120 }}>
              {results.cases.length > 0 && (
                <>
                  {sectionHeader("Cases", results.cases.length)}
                  <View style={{ gap: Spacing.sm }}>
                    {results.cases.map((c) => (
                      <View key={c.id}>{renderCase({ item: c })}</View>
                    ))}
                  </View>
                </>
              )}
              {results.templatePairs.length > 0 && (
                <>
                  {sectionHeader("Legal Templates", results.templatePairs.length)}
                  <View style={{ gap: Spacing.sm }}>
                    {results.templatePairs.map((t) => (
                      <View key={t.pair.baseKey}>{renderTemplatePair({ item: t })}</View>
                    ))}
                  </View>
                </>
              )}
            </View>
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    gap: Spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  inputWrap: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 8 },
  msg: { fontSize: 15, fontWeight: "600", marginTop: Spacing.sm, textAlign: "center", paddingHorizontal: Spacing.xl },
  retry: { marginTop: Spacing.md, paddingHorizontal: Spacing.xl, paddingVertical: Spacing.sm, borderRadius: Radius.md },
  sectionTitle: { fontSize: 16, fontWeight: "800", marginTop: Spacing.lg, marginBottom: Spacing.sm, fontFamily: "serif" },
  card: {
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  icon: { width: 38, height: 38, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  langBtn: {
    flex: 1,
    paddingVertical: 7,
    borderRadius: Radius.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  langBtnText: {
    fontSize: 12,
    fontWeight: "700",
  },
});

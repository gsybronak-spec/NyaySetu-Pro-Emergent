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
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";

interface SearchResults {
  cases: any[];
  templates: any[];
}

export default function Search() {
  const { colors } = useTheme();
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
      const res = await api.search(trimmed);
      setResults({
        cases: Array.isArray(res?.cases) ? res.cases : [],
        templates: Array.isArray(res?.templates) ? res.templates : [],
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
    debounceRef.current = setTimeout(() => run(text), 350);
  };

  useEffect(() => {
    const t = setTimeout(() => inputRef.current?.focus(), 250);
    return () => clearTimeout(t);
  }, []);

  const total = (results?.cases.length || 0) + (results?.templates.length || 0);

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

  const renderTemplate = ({ item }: { item: any }) => (
    <Pressable
      testID={`search-tpl-${item.id}`}
      onPress={() => router.push({ pathname: "/template/[id]", params: { id: item.id } })}
      style={[styles.card, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
    >
      <View style={[styles.icon, { backgroundColor: colors.brandTertiary }]}>
        <Ionicons name="document-text" size={18} color={colors.onBrandTertiary} />
      </View>
      <View style={{ flex: 1, marginLeft: Spacing.md }}>
        <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 14 }} numberOfLines={1}>
          {item.name_en}
        </Text>
        <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }} numberOfLines={1}>
          {item.name_gu} · {item.category}
        </Text>
      </View>
      <Ionicons name="chevron-forward" size={18} color={colors.muted} />
    </Pressable>
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
            Try a case number, party name, or template name like "mudat" / "મુદત".
          </Text>
        </View>
      ) : total === 0 ? (
        <View style={styles.center}>
          <Ionicons name="file-tray-outline" size={40} color={colors.muted} />
          <Text style={[styles.msg, { color: colors.onSurface }]}>No results for "{q.trim()}"</Text>
          <Text style={{ color: colors.muted, fontSize: 13, textAlign: "center", paddingHorizontal: Spacing.xl }}>
            Check the spelling or try a different term.
          </Text>
        </View>
      ) : (
        <FlatList
          data={[0]}
          keyExtractor={() => "root"}
          renderItem={() => (
            <View style={{ paddingHorizontal: Spacing.lg, paddingBottom: 120 }}>
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
              {results.templates.length > 0 && (
                <>
                  {sectionHeader("Templates", results.templates.length)}
                  <View style={{ gap: Spacing.sm }}>
                    {results.templates.map((t) => (
                      <View key={t.id}>{renderTemplate({ item: t })}</View>
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
    flexDirection: "row", alignItems: "center",
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md,
    gap: Spacing.md, borderBottomWidth: StyleSheet.hairlineWidth,
  },
  inputWrap: {
    flex: 1, flexDirection: "row", alignItems: "center",
    paddingHorizontal: Spacing.md, borderRadius: Radius.md, borderWidth: 1,
  },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 8 },
  msg: { fontSize: 15, fontWeight: "600", marginTop: Spacing.sm, textAlign: "center", paddingHorizontal: Spacing.xl },
  retry: { marginTop: Spacing.md, paddingHorizontal: Spacing.xl, paddingVertical: Spacing.sm, borderRadius: Radius.md },
  sectionTitle: { fontSize: 16, fontWeight: "800", marginTop: Spacing.lg, marginBottom: Spacing.sm, fontFamily: "serif" },
  card: {
    flexDirection: "row", alignItems: "center",
    padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1,
  },
  icon: { width: 38, height: 38, borderRadius: 12, alignItems: "center", justifyContent: "center" },
});

import { useCallback, useState } from "react";
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";

export default function CaseDetail() {
  const { colors } = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [c, setC] = useState<any>(null);
  const [templates, setTemplates] = useState<any[]>([]);

  const load = useCallback(async () => {
    try {
      const [cs, tpls] = await Promise.all([api.getCase(String(id)), api.templates()]);
      setC(cs);
      setTemplates(tpls);
    } catch {}
  }, [id]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const archive = () => {
    Alert.alert("Archive Case?", "You can restore it later from the archived view.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Archive",
        onPress: async () => {
          await api.archiveCase(String(id));
          router.replace("/(tabs)/cases");
        },
      },
    ]);
  };

  const restore = async () => {
    await api.restoreCase(String(id));
    load();
  };

  const remove = () => {
    Alert.alert(
      "Delete Case?",
      "This permanently deletes the case. This cannot be undone. Consider archiving instead.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            await api.deleteCase(String(id));
            router.replace("/(tabs)/cases");
          },
        },
      ]
    );
  };

  if (!c) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center" }}>
        <Text style={{ color: colors.muted }}>Loading...</Text>
      </SafeAreaView>
    );
  }

  const isArchived = c.status === "archived";

  const rows: [string, string | undefined | null][] = [
    ["Case Number", c.case_number],
    ["Case Type", c.case_type_label],
    ["Category", c.category],
    ["Complaint", c.complaint_label || c.complaint_custom],
    ["Applicable Law", c.law_label],
    ["Section", c.section_label],
    ["Party / Client", c.party_name],
    ["Opposite Party", c.opposite_party],
    ["Court", c.court],
    ["District", c.district_label],
    ["Police Station", c.police_station],
    ["Language", c.language === "gu" ? "ગુજરાતી" : "English"],
    ["Applications Generated", c.application_count ? String(c.application_count) : null],
  ].filter(([, v]) => !!v) as any;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Pressable testID="case-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
        </Pressable>
        <Text style={[styles.h1, { color: colors.onSurface }]} numberOfLines={1}>
          {c.nickname || c.party_name || "Case Details"}
        </Text>
        <Pressable testID="case-edit-btn" onPress={() => router.push({ pathname: "/case/edit/[id]", params: { id: c.id } })} hitSlop={12}>
          <Ionicons name="create-outline" size={22} color={colors.brandPrimary} />
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={{ padding: Spacing.lg, paddingBottom: Spacing.xxxl }}>
        {isArchived && (
          <View style={[styles.archivedBanner, { backgroundColor: colors.brandTertiary, borderColor: colors.brandPrimary + "40" }]}>
            <Ionicons name="archive" size={16} color={colors.onBrandTertiary} />
            <Text style={{ color: colors.onBrandTertiary, fontSize: 12, flex: 1, marginLeft: 8 }}>This case is archived.</Text>
            <Pressable testID="restore-case-btn" onPress={restore}>
              <Text style={{ color: colors.brandPrimary, fontWeight: "700", fontSize: 12 }}>Restore</Text>
            </Pressable>
          </View>
        )}

        {/* Case info */}
        <View style={[styles.infoCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
          <Text style={[styles.section, { color: colors.brandPrimary }]}>CASE INFORMATION</Text>
          {rows.map(([k, v]) => (
            <View key={k as string} style={styles.infoRow}>
              <Text style={{ color: colors.muted, fontSize: 12, flex: 1 }}>{k}</Text>
              <Text style={{ color: colors.onSurface, fontSize: 13, fontWeight: "600", flex: 1.4, textAlign: "right" }}>{v}</Text>
            </View>
          ))}
        </View>

        <Text style={[styles.section, { color: colors.onSurface, marginTop: Spacing.lg, fontSize: 15 }]}>Create Application</Text>
        <Text style={{ color: colors.muted, fontSize: 12, marginBottom: Spacing.md }}>Choose a template — case data auto-fills.</Text>

        <View style={{ gap: Spacing.sm }}>
          {templates.map((t) => (
            <Pressable
              key={t.id}
              testID={`case-tpl-${t.id}`}
              onPress={() => router.push({ pathname: "/template/[id]", params: { id: t.id, case_id: c.id, lang: c.language } })}
              style={[styles.tplRow, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
            >
              <View style={[styles.tplIcon, { backgroundColor: colors.brandTertiary }]}>
                <Ionicons name="document-text" size={18} color={colors.onBrandTertiary} />
              </View>
              <View style={{ flex: 1, marginLeft: Spacing.md }}>
                <Text style={{ color: colors.onSurface, fontWeight: "700" }} numberOfLines={1}>
                  {c.language === "gu" ? t.name_gu : t.name_en}
                </Text>
                <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }} numberOfLines={1}>
                  {c.language === "gu" ? t.name_en : t.name_gu} • {t.category}
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={colors.muted} />
            </Pressable>
          ))}
        </View>

        {/* Danger zone */}
        <View style={{ marginTop: Spacing.xl, gap: Spacing.sm }}>
          {!isArchived && (
            <Pressable testID="archive-case-btn" onPress={archive} style={[styles.actionRow, { borderColor: colors.border }]}>
              <Ionicons name="archive-outline" size={18} color={colors.onSurfaceSecondary} />
              <Text style={{ color: colors.onSurfaceSecondary, fontWeight: "700", marginLeft: Spacing.sm }}>Archive Case</Text>
            </Pressable>
          )}
          <Pressable testID="delete-case-btn" onPress={remove} style={[styles.actionRow, { borderColor: colors.error + "50" }]}>
            <Ionicons name="trash-outline" size={18} color={colors.error} />
            <Text style={{ color: colors.error, fontWeight: "700", marginLeft: Spacing.sm }}>Delete Case</Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, borderBottomWidth: StyleSheet.hairlineWidth,
  },
  h1: { fontSize: 17, fontWeight: "700", fontFamily: "serif", flex: 1, textAlign: "center", marginHorizontal: 8 },
  archivedBanner: { flexDirection: "row", alignItems: "center", padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1, marginBottom: Spacing.md },
  infoCard: { padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1 },
  section: { fontSize: 11, fontWeight: "800", letterSpacing: 1, marginBottom: Spacing.sm },
  infoRow: { flexDirection: "row", paddingVertical: 6 },
  tplRow: { flexDirection: "row", alignItems: "center", padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1 },
  tplIcon: { width: 36, height: 36, borderRadius: 10, alignItems: "center", justifyContent: "center" },
  actionRow: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    paddingVertical: Spacing.md, borderRadius: Radius.md, borderWidth: 1.5,
  },
});

import { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAppLanguage } from "@/src/context/AppLanguageContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";
import { DesktopPage } from "@/src/components/DesktopPage";
import { ErrorBoundary } from "@/src/components/ErrorBoundary";
import { LanguageSelectModal } from "@/src/components/LanguageSelectModal";
import { ConfirmModal } from "@/src/components/ConfirmModal";
import { safeBack } from "@/src/utils/navigation";
import { TemplateLogicalPair, getActiveTemplatePairs } from "@/src/data/templateCatalogPairs";
import { catalogCache } from "@/src/services/catalogCache";

export default function CaseDetail() {
  const { colors } = useTheme();
  const { t, ui } = useAppLanguage();
  const { isDesktop } = useResponsive();
  const { id, _refresh } = useLocalSearchParams<{ id: string; _refresh?: string }>();
  const [c, setC] = useState<any>(null);
  const [selectedPair, setSelectedPair] = useState<TemplateLogicalPair | null>(null);
  const [fieldLabels, setFieldLabels] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [caseDrafts, setCaseDrafts] = useState<any[]>([]);
  const [draftToDelete, setDraftToDelete] = useState<any>(null);
  const [deletingDraft, setDeletingDraft] = useState(false);
  const [templatePairs, setTemplatePairs] = useState<TemplateLogicalPair[]>(() =>
    catalogCache.peekActiveTemplatePairs()
  );

  useEffect(() => {
    let active = true;
    catalogCache.getActiveTemplatePairs().then((pairs) => {
      if (active && Array.isArray(pairs) && pairs.length > 0) {
        setTemplatePairs(pairs);
      }
    }).catch(() => {});
    const unsub = catalogCache.subscribe("active_template_pairs", (pairs) => {
      if (active && Array.isArray(pairs) && pairs.length > 0) {
        setTemplatePairs(pairs);
      }
    });
    return () => {
      active = false;
      unsub();
    };
  }, []);

  const handleDeleteDraft = (draft: any, e?: any) => {
    if (e && typeof e.stopPropagation === "function") {
      e.stopPropagation();
    }
    if (!(draft?.id || draft?._id)) return;
    setDraftToDelete(draft);
  };

  const confirmDeleteDraft = async () => {
    const draftId = draftToDelete?.id || draftToDelete?._id;
    if (!draftId || deletingDraft) return;
    setDeletingDraft(true);
    try {
      await api.deleteDraft(draftId);
      setCaseDrafts((prev) => prev.filter((d) => (d.id || d._id) !== draftId));
      setDraftToDelete(null);
    } catch (err: any) {
      Alert.alert(t("errorTitle"), err?.message || ui("Could not delete draft", "ડ્રાફ્ટ કાઢી શકાયો નથી"));
    } finally {
      setDeletingDraft(false);
    }
  };

  const load = useCallback(async () => {
    setError(null);
    try {
      const [cs, drs] = await Promise.all([
        api.getCase(String(id)),
        api.drafts().catch(() => []),
      ]);
      setC(cs);
      const caseIdStr = String(id);
      setCaseDrafts(Array.isArray(drs) ? drs.filter((d: any) => String(d?.case_id) === caseIdStr) : []);
      if (cs?.case_type_id) {
        api
          .caseFormConfig(cs.case_type_id)
          .then((cfg) => {
            if (cfg && Array.isArray(cfg.fields)) {
              const map: Record<string, string> = {};
              for (const f of cfg.fields) {
                if (f?.key) map[f.key] = cs.language === "gu" ? f.label_gu || f.label_en : f.label_en;
              }
              setFieldLabels(map);
            }
          })
          .catch(() => {});
      }
    } catch (e: any) {
      setError(e?.message || ui("Could not load this case.", "આ કેસ લોડ કરી શકાયો નથી."));
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load, id, _refresh]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const archive = () => {
    const run = async () => {
      await api.archiveCase(String(id));
      router.replace("/(tabs)/cases");
    };
    if (typeof window !== "undefined" && window.confirm) {
      if (window.confirm(ui("Archive this case? You can restore it later from the archived view.", "આ કેસ આર્કાઇવ કરવો છે? તમે તેને પછીથી પુનઃસ્થાપિત કરી શકો છો."))) run();
    } else {
      Alert.alert(
        ui("Archive Case?", "કેસ આર્કાઇવ કરવો છે?"),
        ui("You can restore it later from the archived view.", "તમે તેને પછીથી આર્કાઇવ કરેલ વિભાગમાંથી પુનઃસ્થાપિત કરી શકો છો."),
        [
          { text: t("cancel"), style: "cancel" },
          { text: ui("Archive", "આર્કાઇવ"), onPress: run },
        ]
      );
    }
  };

  const restore = async () => {
    await api.restoreCase(String(id));
    load();
  };

  const remove = () => {
    const run = async () => {
      await api.deleteCase(String(id));
      router.replace("/(tabs)/cases");
    };
    if (typeof window !== "undefined" && window.confirm) {
      if (window.confirm(ui("Delete this case permanently? This cannot be undone. Consider archiving instead.", "આ કેસ કાયમ માટે કાઢી નાખવો છે? આ પૂર્વવત્ કરી શકાતું નથી. તેના બદલે આર્કાઇવ કરવાનું વિચારો."))) run();
    } else {
      Alert.alert(
        ui("Delete Case?", "કેસ કાઢી નાખવો છે?"),
        ui("This permanently deletes the case. This cannot be undone. Consider archiving instead.", "આ કેસ કાયમ માટે કાઢી નાખવામાં આવશે. આ પૂર્વવત્ કરી શકાતું નથી. તેના બદલે આર્કાઇવ કરવાનું વિચારો."),
        [
          { text: t("cancel"), style: "cancel" },
          { text: t("delete"), style: "destructive", onPress: run },
        ]
      );
    }
  };

  if (!c) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center", padding: Spacing.xl }}>
        {error ? (
          <>
            <Ionicons name="cloud-offline-outline" size={48} color={colors.error || "#B91C1C"} />
            <Text style={{ color: colors.onSurface, fontWeight: "700", marginTop: 12, fontSize: 17 }}>
              {ui("Couldn't load this case", "આ કેસ લોડ કરી શકાયો નથી")}
            </Text>
            <Text style={{ color: colors.muted, fontSize: 13, marginTop: 4, textAlign: "center", maxWidth: 380 }}>{error}</Text>
            <View style={{ flexDirection: "row", gap: 12, marginTop: Spacing.lg }}>
              <Pressable
                testID="case-error-back"
                onPress={() => safeBack("/(tabs)/cases")}
                style={{ paddingHorizontal: Spacing.lg, paddingVertical: 10, borderRadius: Radius.md, borderWidth: 1, borderColor: colors.border }}
              >
                <Text style={{ color: colors.onSurface, fontWeight: "600" }}>{t("back")}</Text>
              </Pressable>
              <Pressable
                testID="case-error-retry"
                onPress={load}
                style={{ paddingHorizontal: Spacing.xl, paddingVertical: 10, borderRadius: Radius.md, backgroundColor: colors.brandPrimary }}
              >
                <Text style={{ color: colors.onBrandPrimary, fontWeight: "700" }}>{t("retry")}</Text>
              </Pressable>
            </View>
          </>
        ) : (
          <ActivityIndicator color={colors.brandPrimary} size="large" />
        )}
      </SafeAreaView>
    );
  }

  const isArchived = c.status === "archived";

  const rows: [string, string | undefined | null][] = [
    [ui("Case Number", "કેસ નંબર"), c.case_number],
    [ui("Case Type", "કેસનો પ્રકાર"), c.case_type_label],
    [ui("Category", "શ્રેણી"), c.category],
    [ui("Complaint", "ફરિયાદ"), c.complaint_label || c.complaint_custom],
    [ui("Applicable Law", "લાગુ કાયદો"), c.law_label],
    [ui("Section", "કલમ"), c.section_label],
    [ui("Party / Client", "પક્ષકાર / અસીલ"), c.party_name],
    [ui("Client Mobile", "અસીલ મોબાઇલ"), c.client_mobile],
    [ui("Client Email", "અસીલ ઈમેલ"), c.client_email],
    [ui("Client Address", "અસીલનું સરનામું"), c.client_address],
    [
      ui("Court", "કોર્ટ"),
      (c.court_source === "custom"
        ? (c.language === "gu" ? c.custom_court_name_gu : c.custom_court_name_en) || c.custom_court_name_gu || c.custom_court_name_en
        : null) || c.court_label || c.court,
    ],
    [ui("District", "જિલ્લો"), c.district_label],
    [ui("Taluka", "તાલુકો"), c.taluka_label],
    [ui("Police Station", "પોલીસ સ્ટેશન"), c.police_station_label || c.police_station],
    [ui("Language", "ભાષા"), c.language === "gu" ? "ગુજરાતી" : "English"],
    [ui("Applications Generated", "તૈયાર કરેલી અરજીઓ"), c.application_count ? String(c.application_count) : null],
  ].filter(([, v]) => !!v) as any;

  const customFieldRows = Object.entries(c.custom_fields || {}).map(([k, v]) => ({
    k,
    lbl: fieldLabels[k] || k,
    v: String(v),
  }));

  // ------------------------- DESKTOP -------------------------
  if (isDesktop) {
    return (
      <ErrorBoundary fallbackTitle={ui("Case Details Error", "કેસ વિગતો પ્રદર્શિત કરવામાં ક્ષતિ")} onRetry={load}>
        <DesktopPage
        sidebarOffset={false}
        onBack={() => safeBack("/(tabs)/cases")}
        title={c.nickname || c.party_name || ui("Case Details", "કેસની વિગતો")}
        subtitle={c.case_number ? `${c.case_number} • ${c.case_type_label || ui("Case", "કેસ")}` : c.case_type_label || ui("Case details", "કેસની વિગતો")}
        actions={
          <>
            <Pressable
              testID="case-edit-btn"
              onPress={() => router.push({ pathname: "/case/edit/[id]", params: { id: c.id } })}
              style={[styles.dBtn, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
            >
              <Ionicons name="create-outline" size={16} color={colors.onSurface} />
              <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 13 }}>{t("edit")}</Text>
            </Pressable>
            {isArchived ? (
              <Pressable
                testID="restore-case-btn"
                onPress={restore}
                style={[styles.dBtn, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
              >
                <Ionicons name="refresh-outline" size={16} color={colors.brandPrimary} />
                <Text style={{ color: colors.brandPrimary, fontWeight: "700", fontSize: 13 }}>{t("restore")}</Text>
              </Pressable>
            ) : (
              <Pressable
                testID="archive-case-btn"
                onPress={archive}
                style={[styles.dBtn, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
              >
                <Ionicons name="archive-outline" size={16} color={colors.onSurfaceSecondary} />
                <Text style={{ color: colors.onSurfaceSecondary, fontWeight: "700", fontSize: 13 }}>{ui("Archive", "આર્કાઇવ")}</Text>
              </Pressable>
            )}
            <Pressable
              testID="delete-case-btn"
              onPress={remove}
              style={[styles.dBtn, { backgroundColor: colors.surfaceSecondary, borderColor: colors.error + "50" }]}
            >
              <Ionicons name="trash-outline" size={16} color={colors.error} />
              <Text style={{ color: colors.error, fontWeight: "700", fontSize: 13 }}>{t("delete")}</Text>
            </Pressable>
          </>
        }
      >
        <View style={{ flexDirection: "row", gap: Spacing.xl, alignItems: "flex-start" }}>
          <View style={{ flex: 1.2, minWidth: 0 }}>
            <View style={[styles.infoCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
              <Text style={[styles.section, { color: colors.brandPrimary }]}>{ui("CASE INFORMATION", "કેસની માહિતી")}</Text>
              {rows.map(([k, v]) => (
                <View key={k as string} style={styles.infoRow}>
                  <Text style={{ color: colors.muted, fontSize: 13, flex: 1 }}>{k}</Text>
                  <Text style={{ color: colors.onSurface, fontSize: 13, fontWeight: "600", flex: 1.4, textAlign: "right" }}>{v}</Text>
                </View>
              ))}
              {customFieldRows.length > 0 && (
                <>
                  <View style={{ height: Spacing.sm }} />
                  <Text style={[styles.section, { color: colors.brandPrimary }]}>{ui("ADMIN CONFIGURED FIELDS", "વધારાની વિગતો")}</Text>
                  {customFieldRows.map((r) => (
                    <View key={r.k} style={styles.infoRow}>
                      <Text style={{ color: colors.muted, fontSize: 13, flex: 1 }}>{r.lbl}</Text>
                      <Text style={{ color: colors.onSurface, fontSize: 13, fontWeight: "600", flex: 1.4, textAlign: "right" }}>{r.v}</Text>
                    </View>
                  ))}
                </>
              )}
            </View>
          </View>

          <View style={{ flex: 1, minWidth: 0 }}>
            {caseDrafts.length > 0 && (
              <View style={[styles.dAppsCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border, marginBottom: Spacing.lg }]}>
                <Text style={[styles.section, { color: colors.brandPrimary }]}>
                  {ui("INCOMPLETE DRAFT APPLICATIONS", "અધૂરી અરજીઓ")}
                </Text>
                <View style={{ gap: Spacing.sm, marginTop: Spacing.xs }}>
                  {caseDrafts.map((d) => (
                    <View
                      key={d.id}
                      style={[styles.dTplRow, { backgroundColor: colors.surface, borderColor: colors.border, justifyContent: "space-between" }]}
                    >
                      <Pressable
                        testID={`case-resume-draft-${d.id}`}
                        onPress={() => router.push({ pathname: "/template/[id]", params: { id: d.template_id, case_id: c.id, lang: d.language || "gu", draft: "1" } })}
                        style={{ flexDirection: "row", alignItems: "center", flex: 1 }}
                      >
                        <View style={[styles.tplIcon, { backgroundColor: "#F59E0B18" }]}>
                          <Ionicons name="time" size={18} color="#D97706" />
                        </View>
                        <View style={{ flex: 1, marginLeft: Spacing.md }}>
                          <Text style={{ color: colors.onSurface, fontWeight: "700" }} numberOfLines={1}>
                            {d.template_name || d.template_id}
                          </Text>
                          <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }}>
                            {ui("Last edited:", "છેલ્લો સુધારો:")} {new Date(d.updated_at).toLocaleString()}
                          </Text>
                        </View>
                      </Pressable>
                      <Pressable
                        testID={`case-del-draft-${d.id}`}
                        onPress={(e) => handleDeleteDraft(d, e)}
                        hitSlop={8}
                        style={{ padding: 8, borderRadius: Radius.sm }}
                      >
                        <Ionicons name="trash-outline" size={17} color={colors.error || "#EF4444"} />
                      </Pressable>
                    </View>
                  ))}
                </View>
              </View>
            )}

            <View style={[styles.dAppsCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
              <Text style={[styles.section, { color: colors.brandPrimary }]}>{ui("CREATE APPLICATION", "અરજી તૈયાર કરો")}</Text>
              <Text style={{ color: colors.muted, fontSize: 12, marginBottom: Spacing.md, marginTop: -4 }}>
                {ui("Choose an application — select language and case data auto-fills.", "અરજી પસંદ કરો — ભાષા પસંદ કરતા કેસની વિગતો આપોઆપ ભરાઈ જશે.")}
              </Text>
              <View style={{ gap: Spacing.sm }}>
                {templatePairs.length === 0 ? (
                  <View style={{ padding: Spacing.lg, alignItems: "center", justifyContent: "center", backgroundColor: colors.surface, borderRadius: Radius.md, borderWidth: 1, borderColor: colors.border }}>
                    <Ionicons name="document-text-outline" size={28} color={colors.muted} />
                    <Text style={{ color: colors.onSurface, fontWeight: "600", marginTop: Spacing.xs, fontSize: 13 }}>{t("noTemplatesAvailable")}</Text>
                  </View>
                ) : (
                  templatePairs.map((pair) => (
                    <Pressable
                      key={pair.baseKey}
                      testID={`case-tpl-${pair.baseKey}`}
                      onPress={() => setSelectedPair(pair)}
                      style={[styles.dTplRow, { backgroundColor: colors.surface, borderColor: colors.border }]}
                    >
                      <View style={[styles.tplIcon, { backgroundColor: colors.brandTertiary }]}>
                        <Ionicons name="document-text" size={18} color={colors.onBrandTertiary} />
                      </View>
                      <View style={{ flex: 1, marginLeft: Spacing.md }}>
                        <Text style={{ color: colors.onSurface, fontWeight: "700" }} numberOfLines={1}>
                          {pair.name_gu}
                        </Text>
                        <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }} numberOfLines={1}>
                          {pair.name_en} • {pair.category}
                        </Text>
                      </View>
                      <Ionicons name="chevron-forward" size={18} color={colors.muted} />
                    </Pressable>
                  ))
                )}
              </View>
            </View>
          </View>
        </View>
        <LanguageSelectModal
          visible={selectedPair !== null}
          onClose={() => setSelectedPair(null)}
          templateNameGu={selectedPair?.name_gu}
          templateNameEn={selectedPair?.name_en}
          category={selectedPair?.category}
          onSelect={(lang) => {
            const pair = selectedPair;
            setSelectedPair(null);
            if (pair) {
              const effectiveId = lang === "gu" ? pair.guId : pair.enId;
              router.push({
                pathname: "/template/[id]",
                params: { id: effectiveId, case_id: c.id, lang },
              });
            }
          }}
        />
        <ConfirmModal
          visible={draftToDelete !== null}
          title={ui("Delete Draft", "ડ્રાફ્ટ કાઢી નાખો")}
          message={ui("Are you sure you want to delete this draft application? This cannot be undone.", "શું તમે આ અધૂરી અરજી કાઢી નાખવા માંગો છો? આ ક્રિયા પૂર્વવત્ કરી શકાતી નથી.")}
          busy={deletingDraft}
          onCancel={() => { if (!deletingDraft) setDraftToDelete(null); }}
          onConfirm={confirmDeleteDraft}
        />
      </DesktopPage>
      </ErrorBoundary>
    );
  }

  // ------------------------- MOBILE -------------------------
  return (
    <ErrorBoundary fallbackTitle={ui("Case Details Error", "કેસ વિગતો પ્રદર્શિત કરવામાં ક્ષતિ")} onRetry={load}>
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Pressable testID="case-back" onPress={() => safeBack("/(tabs)/cases")} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
        </Pressable>
        <Text style={[styles.h1, { color: colors.onSurface }]} numberOfLines={1}>
          {c.nickname || c.party_name || ui("Case Details", "કેસની વિગતો")}
        </Text>
        <Pressable testID="case-edit-btn" onPress={() => router.push({ pathname: "/case/edit/[id]", params: { id: c.id } })} hitSlop={12}>
          <Ionicons name="create-outline" size={22} color={colors.brandPrimary} />
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={{ padding: Spacing.lg, paddingBottom: Spacing.xxxl }}>
        {isArchived && (
          <View style={[styles.archivedBanner, { backgroundColor: colors.brandTertiary, borderColor: colors.brandPrimary + "40" }]}>
            <Ionicons name="archive" size={16} color={colors.onBrandTertiary} />
            <Text style={{ color: colors.onBrandTertiary, fontSize: 12, flex: 1, marginLeft: 8 }}>
              {ui("This case is archived.", "આ કેસ આર્કાઇવ કરેલો છે.")}
            </Text>
            <Pressable testID="restore-case-btn" onPress={restore}>
              <Text style={{ color: colors.brandPrimary, fontWeight: "700", fontSize: 12 }}>{t("restore")}</Text>
            </Pressable>
          </View>
        )}

        {/* Case info */}
        <View style={[styles.infoCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
          <Text style={[styles.section, { color: colors.brandPrimary }]}>{ui("CASE INFORMATION", "કેસની માહિતી")}</Text>
          {rows.map(([k, v]) => (
            <View key={k as string} style={styles.infoRow}>
              <Text style={{ color: colors.muted, fontSize: 12, flex: 1 }}>{k}</Text>
              <Text style={{ color: colors.onSurface, fontSize: 13, fontWeight: "600", flex: 1.4, textAlign: "right" }}>{v}</Text>
            </View>
          ))}
          {customFieldRows.length > 0 && (
            <>
              <View style={{ height: Spacing.sm }} />
              <Text style={[styles.section, { color: colors.brandPrimary }]}>{ui("ADMIN CONFIGURED FIELDS", "વધારાની વિગતો")}</Text>
              {customFieldRows.map((r) => (
                <View key={r.k} style={styles.infoRow}>
                  <Text style={{ color: colors.muted, fontSize: 12, flex: 1 }}>{r.lbl}</Text>
                  <Text style={{ color: colors.onSurface, fontSize: 13, fontWeight: "600", flex: 1.4, textAlign: "right" }}>{r.v}</Text>
                </View>
              ))}
            </>
          )}
        </View>

        {caseDrafts.length > 0 && (
          <View style={{ marginTop: Spacing.lg }}>
            <Text style={[styles.section, { color: colors.onSurface, fontSize: 15 }]}>
              {ui("Incomplete Drafts", "અધૂરી અરજીઓ")}
            </Text>
            <View style={{ gap: Spacing.sm }}>
              {caseDrafts.map((d) => (
                <View
                  key={d.id}
                  style={[styles.tplRow, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border, justifyContent: "space-between" }]}
                >
                  <Pressable
                    testID={`case-resume-draft-${d.id}`}
                    onPress={() => router.push({ pathname: "/template/[id]", params: { id: d.template_id, case_id: c.id, lang: d.language || "gu", draft: "1" } })}
                    style={{ flexDirection: "row", alignItems: "center", flex: 1 }}
                  >
                    <View style={[styles.tplIcon, { backgroundColor: "#F59E0B18" }]}>
                      <Ionicons name="time" size={18} color="#D97706" />
                    </View>
                    <View style={{ flex: 1, marginLeft: Spacing.md }}>
                      <Text style={{ color: colors.onSurface, fontWeight: "700" }} numberOfLines={1}>
                        {d.template_name || d.template_id}
                      </Text>
                      <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }}>
                        {ui("Last edited:", "છેલ્લો સુધારો:")} {new Date(d.updated_at).toLocaleString()}
                      </Text>
                    </View>
                  </Pressable>
                  <Pressable
                    testID={`case-del-draft-${d.id}`}
                    onPress={(e) => handleDeleteDraft(d, e)}
                    hitSlop={8}
                    style={{ padding: 8 }}
                  >
                    <Ionicons name="trash-outline" size={18} color={colors.error || "#EF4444"} />
                  </Pressable>
                </View>
              ))}
            </View>
          </View>
        )}

        <Text style={[styles.section, { color: colors.onSurface, marginTop: Spacing.lg, fontSize: 15 }]}>
          {ui("Create Application", "અરજી તૈયાર કરો")}
        </Text>
        <Text style={{ color: colors.muted, fontSize: 12, marginBottom: Spacing.md }}>
          {ui("Choose an application — select language and case data auto-fills.", "અરજી પસંદ કરો — ભાષા પસંદ કરતા કેસની વિગતો આપોઆપ ભરાઈ જશે.")}
        </Text>

        <View style={{ gap: Spacing.sm }}>
          {templatePairs.length === 0 ? (
            <View style={{ padding: Spacing.lg, alignItems: "center", justifyContent: "center", backgroundColor: colors.surfaceSecondary, borderRadius: Radius.md, borderWidth: 1, borderColor: colors.border }}>
              <Ionicons name="document-text-outline" size={28} color={colors.muted} />
              <Text style={{ color: colors.onSurface, fontWeight: "600", marginTop: Spacing.xs, fontSize: 13 }}>{t("noTemplatesAvailable")}</Text>
            </View>
          ) : (
            templatePairs.map((pair) => (
              <Pressable
                key={pair.baseKey}
                testID={`case-tpl-${pair.baseKey}`}
                onPress={() => setSelectedPair(pair)}
                style={[styles.tplRow, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
              >
                <View style={[styles.tplIcon, { backgroundColor: colors.brandTertiary }]}>
                  <Ionicons name="document-text" size={18} color={colors.onBrandTertiary} />
                </View>
                <View style={{ flex: 1, marginLeft: Spacing.md }}>
                  <Text style={{ color: colors.onSurface, fontWeight: "700" }} numberOfLines={1}>
                    {pair.name_gu}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }} numberOfLines={1}>
                    {pair.name_en} • {pair.category}
                  </Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color={colors.muted} />
              </Pressable>
            ))
          )}
        </View>

        {/* Danger zone */}
        <View style={{ marginTop: Spacing.xl, gap: Spacing.sm }}>
          {!isArchived && (
            <Pressable testID="archive-case-btn" onPress={archive} style={[styles.actionRow, { borderColor: colors.border }]}>
              <Ionicons name="archive-outline" size={18} color={colors.onSurfaceSecondary} />
              <Text style={{ color: colors.onSurfaceSecondary, fontWeight: "700", marginLeft: Spacing.sm }}>{ui("Archive Case", "કેસ આર્કાઇવ કરો")}</Text>
            </Pressable>
          )}
          <Pressable testID="delete-case-btn" onPress={remove} style={[styles.actionRow, { borderColor: colors.error + "50" }]}>
            <Ionicons name="trash-outline" size={18} color={colors.error} />
            <Text style={{ color: colors.error, fontWeight: "700", marginLeft: Spacing.sm }}>{ui("Delete Case", "કેસ કાઢી નાખો")}</Text>
          </Pressable>
        </View>
      </ScrollView>
      <LanguageSelectModal
        visible={selectedPair !== null}
        onClose={() => setSelectedPair(null)}
        templateNameGu={selectedPair?.name_gu}
        templateNameEn={selectedPair?.name_en}
        category={selectedPair?.category}
        onSelect={(lang) => {
          const pair = selectedPair;
          setSelectedPair(null);
          if (pair) {
            const effectiveId = lang === "gu" ? pair.guId : pair.enId;
            router.push({
              pathname: "/template/[id]",
              params: { id: effectiveId, case_id: c.id, lang },
            });
          }
        }}
      />
      <ConfirmModal
        visible={draftToDelete !== null}
        title={ui("Delete Draft", "ડ્રાફ્ટ કાઢી નાખો")}
        message={ui("Are you sure you want to delete this draft application? This cannot be undone.", "શું તમે આ અધૂરી અરજી કાઢી નાખવા માંગો છો? આ ક્રિયા પૂર્વવત્ કરી શકાતી નથી.")}
        busy={deletingDraft}
        onCancel={() => { if (!deletingDraft) setDraftToDelete(null); }}
        onConfirm={confirmDeleteDraft}
      />
    </SafeAreaView>
    </ErrorBoundary>
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
  // Desktop
  dBtn: {
    flexDirection: "row", alignItems: "center", gap: 6,
    paddingHorizontal: Spacing.md, paddingVertical: 9, borderRadius: 999, borderWidth: 1,
  },
  dAppsCard: { padding: Spacing.lg, borderRadius: 14, borderWidth: 1 },
  dTplRow: { flexDirection: "row", alignItems: "center", padding: Spacing.md, borderRadius: 12, borderWidth: 1 },
});

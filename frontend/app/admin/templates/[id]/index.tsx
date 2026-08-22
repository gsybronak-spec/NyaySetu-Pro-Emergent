import React, { useEffect, useState, useCallback } from "react";
import { StyleSheet, Text, View, Pressable, ScrollView } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, router } from "expo-router";
import { AdminLayout } from "@/src/components/admin/AdminLayout";
import { AdminPageHeader } from "@/src/components/admin/AdminPageHeader";
import { AdminStatCard } from "@/src/components/admin/AdminStatCard";
import { AdminDataTable, ColumnDef } from "@/src/components/admin/AdminDataTable";
import { AdminLoadingState, AdminErrorState } from "@/src/components/admin/AdminStates";
import { StatusBadge } from "@/src/components/admin/StatusBadge";
import { ConfirmDialog } from "@/src/components/admin/ConfirmDialog";
import { adminApi } from "@/src/api/adminClient";
import type { AdminTemplateItem, TemplateField } from "@/src/types/admin";

export default function AdminTemplateDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [template, setTemplate] = useState<AdminTemplateItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"fields" | "content_gu" | "content_en" | "settings">("fields");

  // Action State
  const [actionType, setActionType] = useState<"publish" | "unpublish" | "archive" | "restore" | "delete" | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchTemplate = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.getTemplate(id);
      setTemplate(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load legal template.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTemplate();
  }, [fetchTemplate]);

  const handleAction = async () => {
    if (!id || !actionType) return;
    setActionLoading(true);
    try {
      if (actionType === "publish") {
        await adminApi.publishTemplate(id);
      } else if (actionType === "unpublish") {
        await adminApi.unpublishTemplate(id);
      } else if (actionType === "archive") {
        await adminApi.archiveTemplate(id);
      } else if (actionType === "restore") {
        await adminApi.restoreTemplate(id);
      } else if (actionType === "delete") {
        await adminApi.deleteTemplatePermanent(id);
        router.replace("/admin/templates" as any);
        return;
      }
      setActionType(null);
      await fetchTemplate();
    } catch (err: any) {
      alert(err?.message || "Operation failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const fieldColumns: ColumnDef<TemplateField>[] = [
    {
      key: "key",
      header: "Field Key (Placeholder)",
      flex: 1.5,
      render: (f) => (
        <View>
          <Text style={styles.codeText}>{`{{${f.key}}}`}</Text>
          <Text style={styles.cellMutedSm}>{f.key}</Text>
        </View>
      ),
    },
    {
      key: "label_gu",
      header: "Gujarati Label",
      flex: 1.5,
      render: (f) => (
        <Text style={[styles.cellText, { fontFamily: "serif" }]}>{f.label_gu || "—"}</Text>
      ),
    },
    {
      key: "label_en",
      header: "English Label",
      flex: 1.5,
      render: (f) => <Text style={styles.cellText}>{f.label_en || "—"}</Text>,
    },
    {
      key: "type",
      header: "Input Type",
      width: 120,
      render: (f) => (
        <StatusBadge status="active" label={(f.type || "text").toUpperCase()} size="sm" />
      ),
    },
    {
      key: "required",
      header: "Required",
      width: 100,
      render: (f) => (
        <Text style={[styles.cellText, { color: f.required ? "#ECC94B" : "#8B96A9" }]}>
          {f.required ? "Required" : "Optional"}
        </Text>
      ),
    },
  ];

  const t = template;
  const isPublished = t?.status === "published";
  const isArchived = t?.status === "archived";

  return (
    <AdminLayout>
      <AdminPageHeader
        title={t?.name_gu || t?.name_en || `Template ${id}`}
        subtitle={`Canonical ID: ${id} • Category: ${t?.category || "Civil"} • Version: v${t?.version || 1}`}
        breadcrumbs={[
          { label: "Templates", route: "/admin/templates" },
          { label: t?.name_gu || "Template Schema" },
        ]}
        actionLabel={isPublished ? "Unpublish to Draft" : "Publish Version"}
        actionIcon={isPublished ? "pause-outline" : "cloud-upload-outline"}
        onAction={() => setActionType(isPublished ? "unpublish" : "publish")}
        secondaryActionLabel="Revision History"
        onSecondaryAction={() => router.push(`/admin/templates/${id}/revisions` as any)}
      />

      {loading ? (
        <AdminLoadingState message="Loading legal template schema and document settings..." />
      ) : error || !t ? (
        <AdminErrorState message={error || "Template not found."} onRetry={fetchTemplate} />
      ) : (
        <View style={styles.container}>
          {/* Top Metrics */}
          <View style={styles.kpiGrid}>
            <AdminStatCard
              label="Canonical Version"
              value={`v${t.version || 1}`}
              subtitle={`${t.revision_count || 1} immutable snapshots`}
              icon="git-branch"
              color="#C5A059"
              onPress={() => router.push(`/admin/templates/${id}/revisions` as any)}
            />
            <AdminStatCard
              label="Publication Status"
              value={(t.status || "DRAFT").toUpperCase()}
              subtitle={`Source: ${(t.source || "seed").toUpperCase()}`}
              icon="shield-checkmark"
              color={isPublished ? "#48BB78" : "#ECC94B"}
            />
            <AdminStatCard
              label="Schema Fields"
              value={t.fields?.length ?? 0}
              subtitle="Interactive form placeholders"
              icon="list"
              color="#4299E1"
            />
            <AdminStatCard
              label="Page Settings"
              value={t.settings?.page_size || "A4"}
              subtitle={`Margins: ${t.settings?.margin_left_cm || 3.5}cm left`}
              icon="document"
              color="#9F7AEA"
            />
          </View>

          {/* Quick Action Bar for Editor */}
          <View style={styles.editorLaunchCard}>
            <View style={{ flex: 1 }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                <Ionicons name="create" size={20} color="#C5A059" />
                <Text style={styles.editorLaunchTitle}>Word-Like Legal Document Editor</Text>
              </View>
              <Text style={styles.editorLaunchSub}>
                Edit Gujarati and English templates with A4 page view, custom variable chips, tables, and live preview.
              </Text>
            </View>
            <Pressable
              onPress={() => router.push(`/admin/templates/${id}/edit` as any)}
              style={styles.btnLaunchEditor}
            >
              <Ionicons name="open-outline" size={16} color="#061024" style={{ marginRight: 6 }} />
              <Text style={styles.btnLaunchEditorText}>Open Template Editor</Text>
            </Pressable>
          </View>

          {/* Tabbed Inspector Card */}
          <View style={styles.card}>
            {/* Tabs Header */}
            <View style={styles.tabsHeader}>
              <Pressable
                onPress={() => setActiveTab("fields")}
                style={[styles.tabBtn, activeTab === "fields" && styles.tabBtnActive]}
              >
                <Ionicons
                  name="list-outline"
                  size={16}
                  color={activeTab === "fields" ? "#C5A059" : "#8B96A9"}
                />
                <Text style={[styles.tabText, activeTab === "fields" && styles.tabTextActive]}>
                  Form Fields ({t.fields?.length || 0})
                </Text>
              </Pressable>

              <Pressable
                onPress={() => setActiveTab("content_gu")}
                style={[styles.tabBtn, activeTab === "content_gu" && styles.tabBtnActive]}
              >
                <Ionicons
                  name="document-text-outline"
                  size={16}
                  color={activeTab === "content_gu" ? "#C5A059" : "#8B96A9"}
                />
                <Text style={[styles.tabText, activeTab === "content_gu" && styles.tabTextActive]}>
                  Gujarati Template
                </Text>
              </Pressable>

              <Pressable
                onPress={() => setActiveTab("content_en")}
                style={[styles.tabBtn, activeTab === "content_en" && styles.tabBtnActive]}
              >
                <Ionicons
                  name="document-text-outline"
                  size={16}
                  color={activeTab === "content_en" ? "#C5A059" : "#8B96A9"}
                />
                <Text style={[styles.tabText, activeTab === "content_en" && styles.tabTextActive]}>
                  English Template
                </Text>
              </Pressable>

              <Pressable
                onPress={() => setActiveTab("settings")}
                style={[styles.tabBtn, activeTab === "settings" && styles.tabBtnActive]}
              >
                <Ionicons
                  name="settings-outline"
                  size={16}
                  color={activeTab === "settings" ? "#C5A059" : "#8B96A9"}
                />
                <Text style={[styles.tabText, activeTab === "settings" && styles.tabTextActive]}>
                  Document Settings
                </Text>
              </Pressable>
            </View>

            {/* Tab Body */}
            <View style={styles.tabBody}>
              {activeTab === "fields" && (
                <AdminDataTable
                  columns={fieldColumns}
                  data={t.fields || []}
                  keyExtractor={(f) => f.key}
                  emptyTitle="No form fields configured"
                  emptyDescription="Form fields define the interactive placeholders."
                />
              )}

              {activeTab === "content_gu" && (
                <ScrollView style={styles.contentScroll}>
                  <Text style={[styles.bodyText, { fontFamily: "serif" }]}>
                    {t.content_gu || "(No Gujarati body template defined)"}
                  </Text>
                </ScrollView>
              )}

              {activeTab === "content_en" && (
                <ScrollView style={styles.contentScroll}>
                  <Text style={styles.bodyText}>
                    {t.content_en || "(No English body template defined)"}
                  </Text>
                </ScrollView>
              )}

              {activeTab === "settings" && (
                <View style={styles.settingsGrid}>
                  <View style={styles.settingsItem}>
                    <Text style={styles.settingLabel}>Page Size</Text>
                    <Text style={styles.settingVal}>{t.settings?.page_size || "A4"}</Text>
                  </View>
                  <View style={styles.settingsItem}>
                    <Text style={styles.settingLabel}>Left Margin (Legal Binding)</Text>
                    <Text style={styles.settingVal}>{t.settings?.margin_left_cm || 3.5} cm</Text>
                  </View>
                  <View style={styles.settingsItem}>
                    <Text style={styles.settingLabel}>Right Margin</Text>
                    <Text style={styles.settingVal}>{t.settings?.margin_right_cm || 2.0} cm</Text>
                  </View>
                  <View style={styles.settingsItem}>
                    <Text style={styles.settingLabel}>Top Margin</Text>
                    <Text style={styles.settingVal}>{t.settings?.margin_top_cm || 2.5} cm</Text>
                  </View>
                  <View style={styles.settingsItem}>
                    <Text style={styles.settingLabel}>Bottom Margin</Text>
                    <Text style={styles.settingVal}>{t.settings?.margin_bottom_cm || 2.5} cm</Text>
                  </View>
                  <View style={styles.settingsItem}>
                    <Text style={styles.settingLabel}>Primary Gujarati Font</Text>
                    <Text style={styles.settingVal}>{t.settings?.gujarati_font || "Noto Sans Gujarati"}</Text>
                  </View>
                </View>
              )}
            </View>
          </View>
        </View>
      )}

      {/* Confirmation Dialog */}
      <ConfirmDialog
        visible={!!actionType}
        title={
          actionType === "publish"
            ? "Publish New Version"
            : actionType === "unpublish"
            ? "Unpublish to Draft"
            : actionType === "archive"
            ? "Archive Template"
            : actionType === "restore"
            ? "Restore Template"
            : "Permanently Delete Template"
        }
        message={
          actionType === "publish"
            ? `Publishing will bump canonical version to v${(t?.version || 1) + 1} and create an immutable revision record.`
            : actionType === "delete"
            ? `Are you sure you want to permanently delete canonical template "${t?.name_gu || t?.name_en}"?`
            : `Are you sure you want to ${actionType} this template?`
        }
        impactWarning={
          actionType === "delete"
            ? "Historical revision snapshots in template_revisions are strictly preserved and will NOT be deleted."
            : undefined
        }
        confirmVariant={actionType === "delete" ? "danger" : actionType === "unpublish" ? "warning" : "primary"}
        confirmLabel={`${actionType?.toUpperCase()} Template`}
        loading={actionLoading}
        onConfirm={handleAction}
        onCancel={() => setActionType(null)}
      />
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 20,
  },
  kpiGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 16,
  },
  card: {
    backgroundColor: "#0B1B3D",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#1B2A49",
    overflow: "hidden",
  },
  tabsHeader: {
    flexDirection: "row",
    backgroundColor: "#0D182E",
    borderBottomWidth: 1,
    borderBottomColor: "#1B2A49",
    flexWrap: "wrap",
  },
  tabBtn: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 8,
    borderBottomWidth: 2,
    borderBottomColor: "transparent",
  },
  tabBtnActive: {
    borderBottomColor: "#C5A059",
    backgroundColor: "#12203B",
  },
  tabText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#8B96A9",
  },
  tabTextActive: {
    color: "#C5A059",
    fontWeight: "700",
  },
  tabBody: {
    padding: 16,
  },
  codeText: {
    fontFamily: "monospace",
    fontSize: 12,
    color: "#C5A059",
    fontWeight: "600",
  },
  cellText: {
    fontSize: 13,
    color: "#FDFDFD",
  },
  cellMutedSm: {
    fontSize: 10,
    color: "#8B96A9",
    marginTop: 2,
  },
  contentScroll: {
    maxHeight: 400,
    backgroundColor: "#08142D",
    padding: 20,
    borderRadius: 10,
  },
  bodyText: {
    fontSize: 14,
    color: "#FDFDFD",
    lineHeight: 24,
  },
  settingsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 16,
    padding: 10,
  },
  settingsItem: {
    width: "30%",
    minWidth: 200,
    backgroundColor: "#08142D",
    padding: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#162544",
    gap: 4,
  },
  settingLabel: {
    fontSize: 11,
    color: "#8B96A9",
    fontWeight: "600",
    textTransform: "uppercase",
  },
  settingVal: {
    fontSize: 14,
    color: "#FDFDFD",
    fontWeight: "700",
  },
  editorLaunchCard: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#0B1B3D",
    padding: 16,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "rgba(197, 160, 89, 0.4)",
    gap: 16,
  },
  editorLaunchTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#FDFDFD",
  },
  editorLaunchSub: {
    fontSize: 12,
    color: "#8B96A9",
    marginTop: 2,
    lineHeight: 16,
  },
  btnLaunchEditor: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#C5A059",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    flexShrink: 0,
  },
  btnLaunchEditorText: {
    fontSize: 13,
    fontWeight: "800",
    color: "#061024",
  },
});

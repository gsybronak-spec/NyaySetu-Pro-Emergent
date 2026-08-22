import React, { useEffect, useState, useCallback } from "react";
import { StyleSheet, Text, View, Pressable, ScrollView, Modal } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, router } from "expo-router";
import { AdminLayout } from "@/src/components/admin/AdminLayout";
import { AdminPageHeader } from "@/src/components/admin/AdminPageHeader";
import { AdminDataTable, ColumnDef } from "@/src/components/admin/AdminDataTable";
import { AdminLoadingState, AdminErrorState } from "@/src/components/admin/AdminStates";
import { adminApi } from "@/src/api/adminClient";
import type { AdminTemplateRevision } from "@/src/types/admin";

export default function AdminTemplateRevisionsScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [revisions, setRevisions] = useState<AdminTemplateRevision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Snapshot Inspection Modal
  const [inspectSnapshot, setInspectSnapshot] = useState<AdminTemplateRevision | null>(null);

  const fetchRevisions = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.getTemplateRevisions(id);
      setRevisions(res.revisions || []);
    } catch (err: any) {
      setError(err?.message || "Failed to load template revision snapshots.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchRevisions();
  }, [fetchRevisions]);

  const columns: ColumnDef<AdminTemplateRevision>[] = [
    {
      key: "version",
      header: "Revision Version",
      width: 130,
      render: (r) => (
        <View style={styles.versionBadge}>
          <Ionicons name="git-commit-outline" size={14} color="#C5A059" style={{ marginRight: 4 }} />
          <Text style={styles.versionText}>Version {r.version}</Text>
        </View>
      ),
    },
    {
      key: "title",
      header: "Snapshot Title",
      flex: 1.8,
      render: (r) => (
        <View>
          <Text style={styles.cellTitle}>{r.name_gu || r.name_en || r.title}</Text>
          <Text style={styles.cellSub}>Category: {r.category} • {r.fields?.length || 0} fields</Text>
        </View>
      ),
    },
    {
      key: "created_by",
      header: "Published By",
      width: 150,
      render: (r) => (
        <Text style={styles.cellText}>{r.created_by || "Super Admin"}</Text>
      ),
    },
    {
      key: "created_at",
      header: "Snapshot Timestamp",
      width: 170,
      render: (r) => (
        <Text style={styles.cellDate}>
          {r.created_at ? new Date(r.created_at).toLocaleString() : "—"}
        </Text>
      ),
    },
    {
      key: "actions",
      header: "Inspect",
      width: 100,
      align: "right",
      render: (r) => (
        <Pressable
          onPress={() => setInspectSnapshot(r)}
          style={styles.actionIconBtn}
          accessibilityLabel="Inspect Revision Snapshot"
        >
          <Ionicons name="search" size={16} color="#C5A059" />
        </Pressable>
      ),
    },
  ];

  return (
    <AdminLayout>
      <AdminPageHeader
        title={`Template Revisions History`}
        subtitle={`Canonical Template ID: ${id} • Immutable snapshot ledger`}
        breadcrumbs={[
          { label: "Templates", route: "/admin/templates" },
          { label: "Template Detail", route: `/admin/templates/${id}` },
          { label: "Revision Snapshots" },
        ]}
      />

      {loading ? (
        <AdminLoadingState message="Fetching immutable revision snapshots from template_revisions collection..." />
      ) : error ? (
        <AdminErrorState message={error} onRetry={fetchRevisions} />
      ) : (
        <View style={styles.container}>
          {/* Info Banner */}
          <View style={styles.bannerBox}>
            <Ionicons name="shield-checkmark" size={18} color="#C5A059" style={{ marginRight: 10 }} />
            <Text style={styles.bannerText}>
              NyaySetu Pro Phase 1 Immutable Guarantee: All revisions in this table are append-only frozen snapshots. Even if the canonical template is permanently removed, these historical versions remain permanently archived for legal audit compliance.
            </Text>
          </View>

          <AdminDataTable
            columns={columns}
            data={revisions}
            keyExtractor={(r) => r.id || `v${r.version}`}
            emptyTitle="No revision history recorded"
            emptyDescription="Publishing this template will generate its first immutable revision snapshot."
            onRowPress={(r) => setInspectSnapshot(r)}
          />
        </View>
      )}

      {/* Inspect Revision Modal */}
      <Modal
        visible={!!inspectSnapshot}
        transparent
        animationType="fade"
        onRequestClose={() => setInspectSnapshot(null)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <View style={{ flex: 1 }}>
                <Text style={styles.modalTitle}>
                  Revision Snapshot — Version {inspectSnapshot?.version}
                </Text>
                <Text style={styles.modalSub}>
                  {inspectSnapshot?.name_gu || inspectSnapshot?.name_en} • Frozen on{" "}
                  {inspectSnapshot?.created_at ? new Date(inspectSnapshot.created_at).toLocaleString() : "—"}
                </Text>
              </View>
              <Pressable onPress={() => setInspectSnapshot(null)} style={{ padding: 4 }}>
                <Ionicons name="close" size={20} color="#8B96A9" />
              </Pressable>
            </View>

            <ScrollView style={{ maxHeight: 440, padding: 20 }} showsVerticalScrollIndicator={true}>
              <Text style={styles.sectionHeader}>Frozen Gujarati Content:</Text>
              <View style={styles.contentBox}>
                <Text style={[styles.contentText, { fontFamily: "serif" }]}>
                  {inspectSnapshot?.content_gu || "(None)"}
                </Text>
              </View>

              <Text style={[styles.sectionHeader, { marginTop: 16 }]}>Frozen English Content:</Text>
              <View style={styles.contentBox}>
                <Text style={styles.contentText}>
                  {inspectSnapshot?.content_en || "(None)"}
                </Text>
              </View>

              <Text style={[styles.sectionHeader, { marginTop: 16 }]}>
                Configured Schema Placeholders ({inspectSnapshot?.fields?.length || 0}):
              </Text>
              <View style={styles.fieldsList}>
                {inspectSnapshot?.fields?.map((f, i) => (
                  <View key={i} style={styles.fieldItem}>
                    <Text style={styles.fieldKey}>{`{{${f.key}}}`}</Text>
                    <Text style={styles.fieldLabel}>{f.label_gu || f.label_en}</Text>
                  </View>
                ))}
              </View>
            </ScrollView>

            <View style={styles.modalFooter}>
              <Pressable
                onPress={() => setInspectSnapshot(null)}
                style={styles.modalCancelBtn}
              >
                <Text style={styles.modalCancelText}>Close</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 16,
  },
  bannerBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    backgroundColor: "rgba(197, 160, 89, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(197, 160, 89, 0.25)",
    borderRadius: 10,
    padding: 14,
  },
  bannerText: {
    flex: 1,
    fontSize: 12,
    color: "#C5A059",
    lineHeight: 18,
    fontWeight: "500",
  },
  versionBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(197, 160, 89, 0.15)",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    alignSelf: "flex-start",
  },
  versionText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#C5A059",
  },
  cellTitle: {
    fontSize: 13,
    fontWeight: "700",
    color: "#FDFDFD",
  },
  cellSub: {
    fontSize: 11,
    color: "#8B96A9",
    marginTop: 2,
  },
  cellText: {
    fontSize: 12,
    color: "#D1D8E5",
  },
  cellDate: {
    fontSize: 12,
    color: "#8B96A9",
  },
  actionIconBtn: {
    width: 30,
    height: 30,
    borderRadius: 6,
    backgroundColor: "rgba(197, 160, 89, 0.12)",
    alignItems: "center",
    justifyContent: "center",
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(6, 16, 36, 0.85)",
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
  },
  modalCard: {
    backgroundColor: "#12203B",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#253452",
    width: "100%",
    maxWidth: 680,
    overflow: "hidden",
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    padding: 18,
    borderBottomWidth: 1,
    borderBottomColor: "#1B2A49",
    gap: 10,
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FDFDFD",
  },
  modalSub: {
    fontSize: 12,
    color: "#8B96A9",
    marginTop: 2,
  },
  sectionHeader: {
    fontSize: 12,
    fontWeight: "700",
    color: "#8B96A9",
    textTransform: "uppercase",
    marginBottom: 6,
  },
  contentBox: {
    backgroundColor: "#08142D",
    padding: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#162544",
  },
  contentText: {
    fontSize: 13,
    color: "#FDFDFD",
    lineHeight: 22,
  },
  fieldsList: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  fieldItem: {
    backgroundColor: "#0D182E",
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "#1B2A49",
  },
  fieldKey: {
    fontFamily: "monospace",
    fontSize: 11,
    color: "#C5A059",
    fontWeight: "600",
  },
  fieldLabel: {
    fontSize: 10,
    color: "#8B96A9",
    marginTop: 2,
  },
  modalFooter: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "flex-end",
    padding: 16,
    backgroundColor: "#0D182E",
    borderTopWidth: 1,
    borderTopColor: "#1B2A49",
  },
  modalCancelBtn: {
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 8,
    backgroundColor: "#1B2A49",
  },
  modalCancelText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#D1D8E5",
  },
});

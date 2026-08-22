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
import type { CaseDetailResponse, AdminApplicationItem } from "@/src/types/admin";

export default function AdminCaseDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [data, setData] = useState<CaseDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action State
  const [actionType, setActionType] = useState<"archive" | "restore" | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchCaseDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.getCase(id);
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load case details.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchCaseDetail();
  }, [fetchCaseDetail]);

  const handleCaseAction = async () => {
    if (!id || !actionType) return;
    setActionLoading(true);
    try {
      if (actionType === "archive") {
        await adminApi.archiveCase(id);
      } else {
        await adminApi.restoreCase(id);
      }
      setActionType(null);
      await fetchCaseDetail();
    } catch (err: any) {
      alert(err?.message || "Failed to update case status.");
    } finally {
      setActionLoading(false);
    }
  };

  const appColumns: ColumnDef<AdminApplicationItem>[] = [
    {
      key: "template_name",
      header: "Application Template",
      flex: 1.6,
      render: (a) => (
        <View>
          <Text style={styles.cellTitle}>{a.template_name || "Document"}</Text>
          <Text style={styles.cellMutedSm}>{a.filename || a.id}</Text>
        </View>
      ),
    },
    {
      key: "format",
      header: "Format",
      width: 100,
      render: (a) => <StatusBadge status="active" label={(a.format || "PDF").toUpperCase()} size="sm" />,
    },
    {
      key: "language",
      header: "Language",
      width: 100,
      render: (a) => (
        <Text style={styles.cellText}>{a.language === "gu" ? "Gujarati" : "English"}</Text>
      ),
    },
    {
      key: "engine",
      header: "Engine",
      width: 120,
      render: (a) => (
        <Text style={styles.cellText}>{a.engine || "ReportLab"}</Text>
      ),
    },
    {
      key: "created_at",
      header: "Generated Date",
      width: 140,
      render: (a) => (
        <Text style={styles.cellDate}>
          {a.created_at ? new Date(a.created_at).toLocaleDateString() : "—"}
        </Text>
      ),
    },
    {
      key: "actions",
      header: "Action",
      width: 100,
      align: "right",
      render: (a) => (
        <Pressable
          onPress={() => router.push(`/admin/applications/${a.id}` as any)}
          style={styles.actionIconBtn}
        >
          <Ionicons name="eye-outline" size={16} color="#C5A059" />
        </Pressable>
      ),
    },
  ];

  const c = data?.case;
  const owner = data?.owner || c?.owner;
  const isArchived = c?.status === "archived";

  return (
    <AdminLayout>
      <AdminPageHeader
        title={c?.nickname || c?.case_number || `Case ${id}`}
        subtitle={`Case ID: ${id} • Category: ${c?.category || "Civil"}`}
        breadcrumbs={[
          { label: "Cases", route: "/admin/cases" },
          { label: c?.nickname || "Case Details" },
        ]}
        actionLabel={isArchived ? "Restore Case" : "Archive Case"}
        actionIcon={isArchived ? "refresh-outline" : "archive-outline"}
        onAction={() => setActionType(isArchived ? "restore" : "archive")}
      />

      {loading ? (
        <AdminLoadingState message="Loading court case details and applications history..." />
      ) : error || !c ? (
        <AdminErrorState message={error || "Case record not found."} onRetry={fetchCaseDetail} />
      ) : (
        <View style={styles.container}>
          {/* Top Metrics */}
          <View style={styles.kpiGrid}>
            <AdminStatCard
              label="Case Status"
              value={c.status ? c.status.toUpperCase() : "ACTIVE"}
              subtitle={`Created: ${c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}`}
              icon="briefcase"
              color={isArchived ? "#E53E3E" : "#48BB78"}
            />
            <AdminStatCard
              label="Legal Category"
              value={c.category?.toUpperCase() || "CIVIL"}
              subtitle={c.case_type_label || "Court Matter"}
              icon="scale"
              color="#4299E1"
            />
            <AdminStatCard
              label="Associated Documents"
              value={data?.applications?.length ?? 0}
              subtitle="Generated applications"
              icon="document-text"
              color="#9F7AEA"
            />
            <AdminStatCard
              label="Advocate Owner"
              value={owner?.name || owner?.mobile || "Advocate"}
              subtitle={`Bar No: ${(owner as any)?.bar_council_no || "Unregistered"}`}
              icon="person"
              color="#C5A059"
              onPress={owner?.id ? () => router.push(`/admin/users/${owner.id}` as any) : undefined}
            />
          </View>

          {/* Case Metadata & Parties Split */}
          <View style={styles.detailsSplit}>
            {/* Case Details Card */}
            <View style={styles.cardCol}>
              <View style={styles.card}>
                <View style={styles.cardHeader}>
                  <Ionicons name="information-circle-outline" size={20} color="#C5A059" />
                  <Text style={styles.cardTitle}>Jurisdiction & Court Metadata</Text>
                </View>
                <View style={styles.fieldList}>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>Court Name</Text>
                    <Text style={styles.fieldVal}>{c.court_label || c.court || "District Court"}</Text>
                  </View>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>District</Text>
                    <Text style={styles.fieldVal}>{c.district_label || c.district_id || "Gujarat"}</Text>
                  </View>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>Taluka</Text>
                    <Text style={styles.fieldVal}>{c.taluka_label || c.taluka_id || "—"}</Text>
                  </View>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>Case Number</Text>
                    <Text style={styles.fieldVal}>{c.case_number || "Pending Registration"}</Text>
                  </View>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>Case Type</Text>
                    <Text style={styles.fieldVal}>{c.case_type_label || c.case_type_id || "Regular Suit"}</Text>
                  </View>
                </View>
              </View>
            </View>

            {/* Parties Card */}
            <View style={styles.cardCol}>
              <View style={styles.card}>
                <View style={styles.cardHeader}>
                  <Ionicons name="people-outline" size={20} color="#C5A059" />
                  <Text style={styles.cardTitle}>Parties & Litigants</Text>
                </View>
                <View style={styles.fieldList}>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>Primary Party</Text>
                    <View>
                      <Text style={styles.fieldVal}>{c.party_name || "—"}</Text>
                      <Text style={styles.fieldSub}>{c.party_role || "Applicant / Plaintiff"}</Text>
                    </View>
                  </View>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>Opposite Party</Text>
                    <View>
                      <Text style={styles.fieldVal}>{c.opposite_party || "—"}</Text>
                      <Text style={styles.fieldSub}>{c.opposite_party_role || "Opponent / Defendant"}</Text>
                    </View>
                  </View>
                </View>
              </View>
            </View>
          </View>

          {/* Generated Documents Table */}
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <Ionicons name="document-text-outline" size={20} color="#C5A059" />
              <Text style={styles.cardTitle}>Generated Applications for this Case</Text>
            </View>
            <AdminDataTable
              columns={appColumns}
              data={data?.applications || []}
              keyExtractor={(a) => a.id}
              emptyTitle="No generated applications for this case"
              emptyDescription="Documents created for this case will appear here."
              onRowPress={(a) => router.push(`/admin/applications/${a.id}` as any)}
            />
          </View>
        </View>
      )}

      {/* Confirmation Dialog */}
      <ConfirmDialog
        visible={!!actionType}
        title={actionType === "archive" ? "Archive Court Case" : "Restore Court Case"}
        message={
          actionType === "archive"
            ? `Are you sure you want to archive case "${c?.nickname || c?.case_number || id}"?`
            : `Are you sure you want to restore case "${c?.nickname || c?.case_number || id}"?`
        }
        confirmVariant={actionType === "archive" ? "warning" : "primary"}
        confirmLabel={actionType === "archive" ? "Archive Case" : "Restore Case"}
        loading={actionLoading}
        onConfirm={handleCaseAction}
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
  detailsSplit: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 20,
  },
  cardCol: {
    flex: 1,
    minWidth: 320,
  },
  card: {
    backgroundColor: "#0B1B3D",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#1B2A49",
    overflow: "hidden",
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 18,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#162544",
    gap: 10,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#FDFDFD",
  },
  fieldList: {
    padding: 18,
    gap: 14,
  },
  fieldRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    borderBottomWidth: 1,
    borderBottomColor: "#162544",
    paddingBottom: 10,
  },
  fieldLabel: {
    fontSize: 12,
    color: "#8B96A9",
    fontWeight: "600",
  },
  fieldVal: {
    fontSize: 13,
    fontWeight: "600",
    color: "#FDFDFD",
    textAlign: "right",
  },
  fieldSub: {
    fontSize: 11,
    color: "#8B96A9",
    textAlign: "right",
    marginTop: 2,
  },
  cellTitle: {
    fontSize: 13,
    fontWeight: "600",
    color: "#FDFDFD",
  },
  cellText: {
    fontSize: 12,
    color: "#D1D8E5",
  },
  cellMutedSm: {
    fontSize: 10,
    color: "#8B96A9",
    marginTop: 2,
  },
  cellDate: {
    fontSize: 12,
    color: "#8B96A9",
  },
  actionIconBtn: {
    width: 30,
    height: 30,
    borderRadius: 6,
    backgroundColor: "#1B2A49",
    alignItems: "center",
    justifyContent: "center",
  },
});

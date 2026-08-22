import React, { useEffect, useState, useCallback } from "react";
import { StyleSheet, Text, View, Pressable, ScrollView, Modal } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { AdminLayout } from "@/src/components/admin/AdminLayout";
import { AdminDataTable, ColumnDef } from "@/src/components/admin/AdminDataTable";
import { AdminFilterBar, FilterField } from "@/src/components/admin/AdminFilterBar";
import { AdminPagination } from "@/src/components/admin/AdminPagination";
import { StatusBadge } from "@/src/components/admin/StatusBadge";
import { adminApi } from "@/src/api/adminClient";
import type { AdminAuditLogItem, PaginatedResult } from "@/src/types/admin";

export default function AdminAuditLogsScreen() {
  const [data, setData] = useState<PaginatedResult<AdminAuditLogItem> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [entityTypeFilter, setEntityTypeFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Inspection Modal State
  const [inspectLog, setInspectLog] = useState<AdminAuditLogItem | null>(null);

  const fetchAuditLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.listAuditLogs({
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
        action: actionFilter !== "all" ? actionFilter : undefined,
        entity_type: entityTypeFilter !== "all" ? entityTypeFilter : undefined,
      });
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load administrative audit trail.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, actionFilter, entityTypeFilter]);

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  const filterFields: FilterField[] = [
    {
      key: "action",
      label: "Action",
      value: actionFilter,
      options: [
        { label: "Wallet Adjust", value: "wallet_adjust" },
        { label: "User Suspend", value: "user_suspend" },
        { label: "User Activate", value: "user_activate" },
        { label: "User Ban", value: "user_ban" },
        { label: "Template Publish", value: "template_publish" },
        { label: "Template Archive", value: "template_archive" },
        { label: "Catalog Mutate", value: "catalog_mutate" },
        { label: "Plan Update", value: "plan_update" },
      ],
      onChange: (val) => {
        setActionFilter(val);
        setPage(1);
      },
    },
    {
      key: "entity_type",
      label: "Entity",
      value: entityTypeFilter,
      options: [
        { label: "Users", value: "user" },
        { label: "Wallets", value: "wallet" },
        { label: "Templates", value: "template" },
        { label: "Cases", value: "case" },
        { label: "Catalogs", value: "catalog" },
        { label: "Plans", value: "plan" },
      ],
      onChange: (val) => {
        setEntityTypeFilter(val);
        setPage(1);
      },
    },
  ];

  const columns: ColumnDef<AdminAuditLogItem>[] = [
    {
      key: "action",
      header: "Admin Mutation Action",
      width: 170,
      render: (log) => (
        <StatusBadge
          status="admin_adjustment"
          label={log.action?.replace("_", " ").toUpperCase() || "ADMIN ACTION"}
          size="sm"
        />
      ),
    },
    {
      key: "admin_email",
      header: "Administrator",
      flex: 1.4,
      render: (log) => (
        <View>
          <Text style={styles.cellTitle}>{log.admin_name || log.admin_email || "Super Admin"}</Text>
          <Text style={styles.cellSub}>{log.admin_role?.toUpperCase() || "SUPER ADMIN"}</Text>
        </View>
      ),
    },
    {
      key: "entity",
      header: "Target Entity",
      width: 160,
      render: (log) => (
        <View>
          <Text style={styles.cellText}>{log.entity_type?.toUpperCase() || "RECORD"}</Text>
          <Text style={styles.cellMutedSm}>ID: {log.entity_id ? log.entity_id.substring(0, 10) : "—"}</Text>
        </View>
      ),
    },
    {
      key: "reason",
      header: "Reason / Purpose",
      flex: 1.6,
      render: (log) => (
        <Text style={styles.cellText} numberOfLines={2}>
          {log.reason || "System mutation initiated by administrator"}
        </Text>
      ),
    },
    {
      key: "created_at",
      header: "Audit Timestamp",
      width: 160,
      render: (log) => (
        <Text style={styles.cellDate}>
          {log.created_at || log.timestamp ? new Date(log.created_at || log.timestamp!).toLocaleString() : "—"}
        </Text>
      ),
    },
    {
      key: "actions",
      header: "Diff",
      width: 80,
      align: "right",
      render: (log) => (
        <Pressable
          onPress={() => setInspectLog(log)}
          style={styles.actionIconBtn}
          accessibilityLabel="Inspect Mutation Diff"
        >
          <Ionicons name="code-slash" size={15} color="#C5A059" />
        </Pressable>
      ),
    },
  ];

  return (
    <AdminLayout
      title="Administrative Security Audit Trail"
      subtitle="Tamper-evident chronological ledger of all platform administrative mutations and governance events"
    >
      <View style={styles.container}>
        <AdminFilterBar
          search={search}
          onSearchChange={(val) => {
            setSearch(val);
            setPage(1);
          }}
          searchPlaceholder="Search audit events by action, admin, target ID, reason..."
          filters={filterFields}
          onReset={() => {
            setSearch("");
            setActionFilter("all");
            setEntityTypeFilter("all");
            setPage(1);
          }}
          totalCount={data?.total}
        />

        <AdminDataTable
          columns={columns}
          data={data?.items || []}
          keyExtractor={(log) => log.id || `${log.action}-${log.created_at}`}
          loading={loading}
          error={error}
          onRetry={fetchAuditLogs}
          emptyTitle="No audit log records found"
          emptyDescription="Administrative mutations matching your filters will appear here."
          onRowPress={(log) => setInspectLog(log)}
        />

        {data && data.total > 0 ? (
          <AdminPagination
            page={data.page || page}
            pageSize={data.page_size || pageSize}
            total={data.total}
            totalPages={data.total_pages || Math.ceil(data.total / pageSize)}
            onPageChange={setPage}
            onPageSizeChange={(sz) => {
              setPageSize(sz);
              setPage(1);
            }}
          />
        ) : null}
      </View>

      {/* JSON Diff Inspection Modal */}
      <Modal
        visible={!!inspectLog}
        transparent
        animationType="fade"
        onRequestClose={() => setInspectLog(null)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <Ionicons name="shield-checkmark" size={22} color="#C5A059" />
              <View style={{ flex: 1, marginLeft: 8 }}>
                <Text style={styles.modalTitle}>
                  Audit Record — {inspectLog?.action?.toUpperCase()}
                </Text>
                <Text style={styles.modalSub}>
                  Logged on {inspectLog?.created_at ? new Date(inspectLog.created_at).toLocaleString() : "—"}
                </Text>
              </View>
              <Pressable onPress={() => setInspectLog(null)} style={{ padding: 4 }}>
                <Ionicons name="close" size={20} color="#8B96A9" />
              </Pressable>
            </View>

            <ScrollView style={{ maxHeight: 460, padding: 20 }} showsVerticalScrollIndicator={true}>
              <View style={styles.metaRow}>
                <Text style={styles.metaLabel}>Executing Admin:</Text>
                <Text style={styles.metaVal}>{inspectLog?.admin_email || inspectLog?.admin_name || "Super Admin"}</Text>
              </View>
              <View style={styles.metaRow}>
                <Text style={styles.metaLabel}>Target Entity:</Text>
                <Text style={styles.metaVal}>
                  {inspectLog?.entity_type} (ID: {inspectLog?.entity_id})
                </Text>
              </View>
              <View style={styles.metaRow}>
                <Text style={styles.metaLabel}>Stated Reason:</Text>
                <Text style={styles.metaVal}>{inspectLog?.reason || "Administrative governance mutation"}</Text>
              </View>

              <Text style={[styles.sectionHeader, { marginTop: 16 }]}>State Mutation Diff (Before / After):</Text>
              <View style={styles.diffSplit}>
                <View style={styles.diffBox}>
                  <Text style={styles.diffHeader}>Previous State (old_value):</Text>
                  <Text style={styles.diffJson}>
                    {inspectLog?.old_value
                      ? JSON.stringify(inspectLog.old_value, null, 2)
                      : "(None / Initial creation)"}
                  </Text>
                </View>
                <View style={styles.diffBox}>
                  <Text style={[styles.diffHeader, { color: "#48BB78" }]}>New State (new_value):</Text>
                  <Text style={styles.diffJson}>
                    {inspectLog?.new_value
                      ? JSON.stringify(inspectLog.new_value, null, 2)
                      : "(None / Deletion event)"}
                  </Text>
                </View>
              </View>
            </ScrollView>

            <View style={styles.modalFooter}>
              <Pressable
                onPress={() => setInspectLog(null)}
                style={styles.modalCancelBtn}
              >
                <Text style={styles.modalCancelText}>Close Inspector</Text>
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
    width: 28,
    height: 28,
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
    maxWidth: 720,
    overflow: "hidden",
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    padding: 18,
    borderBottomWidth: 1,
    borderBottomColor: "#1B2A49",
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
  metaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: "#162544",
  },
  metaLabel: {
    fontSize: 12,
    color: "#8B96A9",
    fontWeight: "600",
  },
  metaVal: {
    fontSize: 12,
    color: "#FDFDFD",
    fontWeight: "600",
  },
  sectionHeader: {
    fontSize: 12,
    fontWeight: "700",
    color: "#8B96A9",
    textTransform: "uppercase",
    marginBottom: 8,
  },
  diffSplit: {
    gap: 12,
  },
  diffBox: {
    backgroundColor: "#08142D",
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: "#162544",
  },
  diffHeader: {
    fontSize: 11,
    fontWeight: "700",
    color: "#ECC94B",
    marginBottom: 6,
  },
  diffJson: {
    fontFamily: "monospace",
    fontSize: 11,
    color: "#D1D8E5",
    lineHeight: 18,
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

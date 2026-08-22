import React, { useEffect, useState, useCallback } from "react";
import { StyleSheet, Text, View, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { AdminLayout } from "@/src/components/admin/AdminLayout";
import { AdminDataTable, ColumnDef } from "@/src/components/admin/AdminDataTable";
import { AdminFilterBar, FilterField } from "@/src/components/admin/AdminFilterBar";
import { AdminPagination } from "@/src/components/admin/AdminPagination";
import { StatusBadge } from "@/src/components/admin/StatusBadge";
import { ConfirmDialog } from "@/src/components/admin/ConfirmDialog";
import { adminApi } from "@/src/api/adminClient";
import type { AdminCaseItem, PaginatedResult } from "@/src/types/admin";

export default function AdminCasesListScreen() {
  const [data, setData] = useState<PaginatedResult<AdminCaseItem> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Action State
  const [targetCase, setTargetCase] = useState<AdminCaseItem | null>(null);
  const [actionType, setActionType] = useState<"archive" | "restore" | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchCases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.listCases({
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
        category: categoryFilter !== "all" ? categoryFilter : undefined,
      });
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to fetch court cases.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, statusFilter, categoryFilter]);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  const handleCaseAction = async () => {
    if (!targetCase || !actionType) return;
    setActionLoading(true);
    try {
      if (actionType === "archive") {
        await adminApi.archiveCase(targetCase.id);
      } else {
        await adminApi.restoreCase(targetCase.id);
      }
      setTargetCase(null);
      setActionType(null);
      await fetchCases();
    } catch (err: any) {
      alert(err?.message || "Failed to update case status.");
    } finally {
      setActionLoading(false);
    }
  };

  const filterFields: FilterField[] = [
    {
      key: "status",
      label: "Status",
      value: statusFilter,
      options: [
        { label: "Active", value: "active" },
        { label: "Archived", value: "archived" },
      ],
      onChange: (val) => {
        setStatusFilter(val);
        setPage(1);
      },
    },
    {
      key: "category",
      label: "Category",
      value: categoryFilter,
      options: [
        { label: "Civil", value: "Civil" },
        { label: "Criminal", value: "Criminal" },
      ],
      onChange: (val) => {
        setCategoryFilter(val);
        setPage(1);
      },
    },
  ];

  const columns: ColumnDef<AdminCaseItem>[] = [
    {
      key: "case_info",
      header: "Case Title & Matter",
      flex: 1.8,
      render: (c) => (
        <View>
          <Text style={styles.cellTitle}>
            {c.nickname || c.case_number || `Case ${c.id.substring(0, 8)}`}
          </Text>
          <Text style={styles.cellSub} numberOfLines={1}>
            {c.party_name ? `${c.party_name} v. ${c.opposite_party || "—"}` : "No parties configured"}
          </Text>
        </View>
      ),
    },
    {
      key: "owner",
      header: "Advocate Owner",
      flex: 1.2,
      render: (c) => (
        <View>
          <Text style={styles.cellText}>{c.owner?.name || c.owner?.mobile || "Advocate"}</Text>
          <Text style={styles.cellMutedSm}>{c.owner?.email || `+91 ${c.owner?.mobile || "—"}`}</Text>
        </View>
      ),
    },
    {
      key: "court",
      header: "Court & District",
      width: 160,
      render: (c) => (
        <View>
          <Text style={styles.cellText}>{c.court_label || c.court || "District Court"}</Text>
          <Text style={styles.cellMutedSm}>
            {c.district_label || c.district_id || "Gujarat"}
          </Text>
        </View>
      ),
    },
    {
      key: "category",
      header: "Category",
      width: 100,
      render: (c) => (
        <StatusBadge
          status="active"
          label={c.category?.toUpperCase() || "CIVIL"}
          size="sm"
        />
      ),
    },
    {
      key: "status",
      header: "Status",
      width: 100,
      render: (c) => <StatusBadge status={c.status || "active"} size="sm" />,
    },
    {
      key: "created_at",
      header: "Filing Date",
      width: 110,
      render: (c) => (
        <Text style={styles.cellDate}>
          {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
        </Text>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      width: 130,
      align: "right",
      render: (c) => {
        const isArchived = c.status === "archived";
        return (
          <View style={styles.actionRow}>
            <Pressable
              onPress={() => router.push(`/admin/cases/${c.id}` as any)}
              style={styles.actionIconBtn}
              accessibilityLabel="View Case Details"
            >
              <Ionicons name="eye-outline" size={16} color="#8B96A9" />
            </Pressable>

            {isArchived ? (
              <Pressable
                onPress={() => {
                  setTargetCase(c);
                  setActionType("restore");
                }}
                style={[styles.actionIconBtn, { backgroundColor: "rgba(72, 187, 120, 0.15)" }]}
                accessibilityLabel="Restore Case"
              >
                <Ionicons name="refresh-outline" size={16} color="#48BB78" />
              </Pressable>
            ) : (
              <Pressable
                onPress={() => {
                  setTargetCase(c);
                  setActionType("archive");
                }}
                style={[styles.actionIconBtn, { backgroundColor: "rgba(229, 62, 62, 0.15)" }]}
                accessibilityLabel="Archive Case"
              >
                <Ionicons name="archive-outline" size={16} color="#F56565" />
              </Pressable>
            )}
          </View>
        );
      },
    },
  ];

  return (
    <AdminLayout
      title="Court Cases Oversight"
      subtitle="Global overview of active and archived court cases across all registered advocates"
    >
      <View style={styles.container}>
        <AdminFilterBar
          search={search}
          onSearchChange={(val) => {
            setSearch(val);
            setPage(1);
          }}
          searchPlaceholder="Search case title, case number, parties, or advocate..."
          filters={filterFields}
          onReset={() => {
            setSearch("");
            setStatusFilter("all");
            setCategoryFilter("all");
            setPage(1);
          }}
          totalCount={data?.total}
        />

        <AdminDataTable
          columns={columns}
          data={data?.items || []}
          keyExtractor={(c) => c.id}
          loading={loading}
          error={error}
          onRetry={fetchCases}
          emptyTitle="No court cases found"
          emptyDescription="No cases match your search query or filter selection."
          onRowPress={(c) => router.push(`/admin/cases/${c.id}` as any)}
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

      {/* Confirmation Dialog */}
      <ConfirmDialog
        visible={!!targetCase && !!actionType}
        title={actionType === "archive" ? "Archive Court Case" : "Restore Court Case"}
        message={
          actionType === "archive"
            ? `Are you sure you want to archive case "${targetCase?.nickname || targetCase?.case_number || targetCase?.id}"? Advocate can still view it in their archive.`
            : `Are you sure you want to restore case "${targetCase?.nickname || targetCase?.case_number || targetCase?.id}" back to active status?`
        }
        confirmVariant={actionType === "archive" ? "warning" : "primary"}
        confirmLabel={actionType === "archive" ? "Archive Case" : "Restore Case"}
        loading={actionLoading}
        onConfirm={handleCaseAction}
        onCancel={() => {
          setTargetCase(null);
          setActionType(null);
        }}
      />
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
    marginTop: 1,
  },
  cellDate: {
    fontSize: 12,
    color: "#8B96A9",
  },
  actionRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  actionIconBtn: {
    width: 30,
    height: 30,
    borderRadius: 6,
    backgroundColor: "#1B2A49",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "#253452",
  },
});

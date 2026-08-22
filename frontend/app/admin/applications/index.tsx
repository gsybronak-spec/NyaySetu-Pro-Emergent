import React, { useEffect, useState, useCallback } from "react";
import { StyleSheet, Text, View, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { AdminLayout } from "@/src/components/admin/AdminLayout";
import { AdminDataTable, ColumnDef } from "@/src/components/admin/AdminDataTable";
import { AdminFilterBar, FilterField } from "@/src/components/admin/AdminFilterBar";
import { AdminPagination } from "@/src/components/admin/AdminPagination";
import { StatusBadge } from "@/src/components/admin/StatusBadge";
import { adminApi } from "@/src/api/adminClient";
import type { AdminApplicationItem, PaginatedResult } from "@/src/types/admin";

export default function AdminApplicationsListScreen() {
  const [data, setData] = useState<PaginatedResult<AdminApplicationItem> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [formatFilter, setFormatFilter] = useState("all");
  const [languageFilter, setLanguageFilter] = useState("all");
  const [engineFilter, setEngineFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  const fetchApplications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.listApplications({
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
        format: formatFilter !== "all" ? formatFilter : undefined,
        language: languageFilter !== "all" ? languageFilter : undefined,
        engine: engineFilter !== "all" ? engineFilter : undefined,
      });
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to fetch document applications.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, formatFilter, languageFilter, engineFilter]);

  useEffect(() => {
    fetchApplications();
  }, [fetchApplications]);

  const filterFields: FilterField[] = [
    {
      key: "format",
      label: "Format",
      value: formatFilter,
      options: [
        { label: "PDF", value: "pdf" },
        { label: "DOCX", value: "docx" },
        { label: "ODT", value: "odt" },
        { label: "PNG", value: "png" },
      ],
      onChange: (val) => {
        setFormatFilter(val);
        setPage(1);
      },
    },
    {
      key: "language",
      label: "Language",
      value: languageFilter,
      options: [
        { label: "Gujarati", value: "gu" },
        { label: "English", value: "en" },
      ],
      onChange: (val) => {
        setLanguageFilter(val);
        setPage(1);
      },
    },
    {
      key: "engine",
      label: "Engine",
      value: engineFilter,
      options: [
        { label: "ReportLab", value: "reportlab" },
        { label: "LibreOffice", value: "libreoffice" },
      ],
      onChange: (val) => {
        setEngineFilter(val);
        setPage(1);
      },
    },
  ];

  const columns: ColumnDef<AdminApplicationItem>[] = [
    {
      key: "document",
      header: "Legal Template & File",
      flex: 1.8,
      render: (a) => (
        <View>
          <Text style={styles.cellTitle}>{a.template_name || a.filename || "Legal Application"}</Text>
          <Text style={styles.cellSub}>
            File: {a.filename || a.id} • v{a.template_version || 1}
          </Text>
        </View>
      ),
    },
    {
      key: "user_id",
      header: "Advocate Owner",
      width: 140,
      render: (a) => (
        <Pressable
          onPress={() => router.push(`/admin/users/${a.user_id}` as any)}
          style={styles.ownerLink}
        >
          <Text style={styles.ownerLinkText}>
            {a.user_id ? `User: ${a.user_id.substring(0, 8)}...` : "—"}
          </Text>
        </Pressable>
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
      header: "Engine / Font",
      width: 150,
      render: (a) => (
        <View>
          <Text style={styles.cellText}>{a.engine || "ReportLab"}</Text>
          <Text style={styles.cellMutedSm}>{a.font_family || "Noto Sans Gujarati"}</Text>
        </View>
      ),
    },
    {
      key: "created_at",
      header: "Generated Date",
      width: 130,
      render: (a) => (
        <Text style={styles.cellDate}>
          {a.created_at ? new Date(a.created_at).toLocaleDateString() : "—"}
        </Text>
      ),
    },
    {
      key: "actions",
      header: "Inspect",
      width: 90,
      align: "right",
      render: (a) => (
        <Pressable
          onPress={() => router.push(`/admin/applications/${a.id}` as any)}
          style={styles.actionIconBtn}
          accessibilityLabel="Inspect Application"
        >
          <Ionicons name="search" size={16} color="#C5A059" />
        </Pressable>
      ),
    },
  ];

  return (
    <AdminLayout
      title="Generated Document Applications"
      subtitle="Complete ledger of compiled court pleadings, HarfBuzz font shaping digests and document engines"
    >
      <View style={styles.container}>
        <AdminFilterBar
          search={search}
          onSearchChange={(val) => {
            setSearch(val);
            setPage(1);
          }}
          searchPlaceholder="Search template name, filename, user ID, case ID..."
          filters={filterFields}
          onReset={() => {
            setSearch("");
            setFormatFilter("all");
            setLanguageFilter("all");
            setEngineFilter("all");
            setPage(1);
          }}
          totalCount={data?.total}
        />

        <AdminDataTable
          columns={columns}
          data={data?.items || []}
          keyExtractor={(a) => a.id}
          loading={loading}
          error={error}
          onRetry={fetchApplications}
          emptyTitle="No document applications found"
          emptyDescription="Generated court documents matching your filters will appear here."
          onRowPress={(a) => router.push(`/admin/applications/${a.id}` as any)}
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
  ownerLink: {
    paddingVertical: 2,
  },
  ownerLinkText: {
    fontSize: 12,
    color: "#C5A059",
    fontWeight: "500",
  },
  actionIconBtn: {
    width: 30,
    height: 30,
    borderRadius: 6,
    backgroundColor: "rgba(197, 160, 89, 0.12)",
    alignItems: "center",
    justifyContent: "center",
  },
});

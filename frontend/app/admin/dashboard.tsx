import React, { useEffect, useState, useCallback } from "react";
import { StyleSheet, Text, View, Pressable, ScrollView } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { AdminLayout } from "@/src/components/admin/AdminLayout";
import { AdminStatCard } from "@/src/components/admin/AdminStatCard";
import { AdminDataTable, ColumnDef } from "@/src/components/admin/AdminDataTable";
import { AdminLoadingState, AdminErrorState } from "@/src/components/admin/AdminStates";
import { StatusBadge } from "@/src/components/admin/StatusBadge";
import { adminApi } from "@/src/api/adminClient";
import type { AdminDashboardStats } from "@/src/types/admin";

export default function AdminDashboardScreen() {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminApi.getStats();
      setStats(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load dashboard metrics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const recentUserColumns: ColumnDef<any>[] = [
    {
      key: "name",
      header: "Advocate Name",
      flex: 1.5,
      render: (item) => (
        <View>
          <Text style={styles.cellPrimary}>{item.name || item.mobile || "Unnamed User"}</Text>
          <Text style={styles.cellMuted}>{item.email || `+91 ${item.mobile}` || "—"}</Text>
        </View>
      ),
    },
    {
      key: "provider",
      header: "Auth Provider",
      width: 130,
      render: (item) => (
        <StatusBadge status={item.provider || "phone"} label={(item.provider || "OTP").toUpperCase()} size="sm" />
      ),
    },
    {
      key: "created_at",
      header: "Joined Date",
      width: 150,
      render: (item) => (
        <Text style={styles.cellDate}>
          {item.created_at ? new Date(item.created_at).toLocaleDateString() : "—"}
        </Text>
      ),
    },
    {
      key: "actions",
      header: "Action",
      width: 100,
      align: "right",
      render: (item) => (
        <Pressable
          onPress={() => router.push(`/admin/users/${item.id}` as any)}
          style={styles.tableActionBtn}
        >
          <Text style={styles.tableActionText}>View</Text>
          <Ionicons name="chevron-forward" size={14} color="#C5A059" />
        </Pressable>
      ),
    },
  ];

  const recentAppColumns: ColumnDef<any>[] = [
    {
      key: "template_name",
      header: "Template / Document",
      flex: 1.8,
      render: (item) => (
        <View>
          <Text style={styles.cellPrimary}>{item.template_name || "Document"}</Text>
          <Text style={styles.cellMuted}>ID: {item.id?.substring(0, 10)}...</Text>
        </View>
      ),
    },
    {
      key: "format",
      header: "Format",
      width: 100,
      render: (item) => (
        <StatusBadge status="active" label={(item.format || "PDF").toUpperCase()} size="sm" />
      ),
    },
    {
      key: "language",
      header: "Language",
      width: 100,
      render: (item) => (
        <Text style={styles.cellMuted}>{item.language === "gu" ? "Gujarati" : "English"}</Text>
      ),
    },
    {
      key: "created_at",
      header: "Generated",
      width: 150,
      render: (item) => (
        <Text style={styles.cellDate}>
          {item.created_at ? new Date(item.created_at).toLocaleDateString() : "—"}
        </Text>
      ),
    },
    {
      key: "actions",
      header: "Action",
      width: 100,
      align: "right",
      render: (item) => (
        <Pressable
          onPress={() => router.push(`/admin/applications/${item.id}` as any)}
          style={styles.tableActionBtn}
        >
          <Text style={styles.tableActionText}>Inspect</Text>
          <Ionicons name="chevron-forward" size={14} color="#C5A059" />
        </Pressable>
      ),
    },
  ];

  return (
    <AdminLayout
      title="System Overview"
      subtitle="Live operational metrics, registered advocates, document throughput & revenue metrics"
      actions={
        <Pressable onPress={fetchStats} style={styles.refreshHeaderBtn}>
          <Ionicons name="refresh" size={16} color="#C5A059" />
          <Text style={styles.refreshHeaderText}>Refresh</Text>
        </Pressable>
      }
    >
      {loading && !stats ? (
        <AdminLoadingState message="Fetching live administrative statistics..." />
      ) : error ? (
        <AdminErrorState message={error} onRetry={fetchStats} />
      ) : (
        <View style={styles.container}>
          {/* Top KPI Cards Grid */}
          <View style={styles.kpiGrid}>
            <AdminStatCard
              label="Total Registered Users"
              value={stats?.total_users ?? 0}
              subtitle={`${stats?.recent_users_30d ?? 0} new in last 30 days`}
              icon="people"
              color="#48BB78"
              onPress={() => router.push("/admin/users" as any)}
            />
            <AdminStatCard
              label="Total Cases Tracked"
              value={stats?.total_cases ?? 0}
              subtitle="Civil & Criminal court matters"
              icon="briefcase"
              color="#4299E1"
              onPress={() => router.push("/admin/cases" as any)}
            />
            <AdminStatCard
              label="Generated Documents"
              value={stats?.total_documents_generated ?? 0}
              subtitle="PDF, DOCX, ODT legal drafts"
              icon="document-text"
              color="#9F7AEA"
              onPress={() => router.push("/admin/applications" as any)}
            />
            <AdminStatCard
              label="Credits Consumed"
              value={stats?.total_credits_consumed ?? 0}
              subtitle={`${stats?.total_transactions ?? 0} ledger transactions`}
              icon="diamond"
              color="#C5A059"
              onPress={() => router.push("/admin/plans" as any)}
            />
          </View>

          {/* Quick Admin Actions Banner */}
          <View style={styles.quickActionsCard}>
            <Text style={styles.quickActionsTitle}>Quick Administrative Actions</Text>
            <View style={styles.quickActionsRow}>
              <Pressable
                onPress={() => router.push("/admin/users" as any)}
                style={styles.quickActionBtn}
              >
                <Ionicons name="person-add-outline" size={18} color="#C5A059" />
                <Text style={styles.quickActionLabel}>Manage Users & Wallets</Text>
              </Pressable>
              <Pressable
                onPress={() => router.push("/admin/templates" as any)}
                style={styles.quickActionBtn}
              >
                <Ionicons name="copy-outline" size={18} color="#C5A059" />
                <Text style={styles.quickActionLabel}>Template Catalog & Versions</Text>
              </Pressable>
              <Pressable
                onPress={() => router.push("/admin/catalogs" as any)}
                style={styles.quickActionBtn}
              >
                <Ionicons name="library-outline" size={18} color="#C5A059" />
                <Text style={styles.quickActionLabel}>Courts & District Catalogs</Text>
              </Pressable>
              <Pressable
                onPress={() => router.push("/admin/audit-logs" as any)}
                style={styles.quickActionBtn}
              >
                <Ionicons name="shield-checkmark-outline" size={18} color="#C5A059" />
                <Text style={styles.quickActionLabel}>Security Audit Trail</Text>
              </Pressable>
            </View>
          </View>

          {/* Recent Data Tables Split View */}
          <View style={styles.tablesSplit}>
            {/* Recent Advocates Table */}
            <View style={styles.tableCol}>
              <View style={styles.sectionHeaderRow}>
                <View style={styles.sectionTitleWithIcon}>
                  <Ionicons name="person" size={18} color="#C5A059" />
                  <Text style={styles.sectionTitle}>Recent Advocate Registrations</Text>
                </View>
                <Pressable
                  onPress={() => router.push("/admin/users" as any)}
                  style={styles.viewAllBtn}
                >
                  <Text style={styles.viewAllText}>View All</Text>
                  <Ionicons name="arrow-forward" size={12} color="#C5A059" />
                </Pressable>
              </View>
              <AdminDataTable
                columns={recentUserColumns}
                data={stats?.recent_users || []}
                keyExtractor={(item) => item.id}
                emptyTitle="No recent user registrations"
                emptyDescription="New advocate registrations will appear here in real time."
                onRowPress={(item) => router.push(`/admin/users/${item.id}` as any)}
              />
            </View>

            {/* Recent Document Generations Table */}
            <View style={styles.tableCol}>
              <View style={styles.sectionHeaderRow}>
                <View style={styles.sectionTitleWithIcon}>
                  <Ionicons name="document-text" size={18} color="#C5A059" />
                  <Text style={styles.sectionTitle}>Recent Document Applications</Text>
                </View>
                <Pressable
                  onPress={() => router.push("/admin/applications" as any)}
                  style={styles.viewAllBtn}
                >
                  <Text style={styles.viewAllText}>View All</Text>
                  <Ionicons name="arrow-forward" size={12} color="#C5A059" />
                </Pressable>
              </View>
              <AdminDataTable
                columns={recentAppColumns}
                data={stats?.recent_applications || []}
                keyExtractor={(item) => item.id}
                emptyTitle="No document applications generated yet"
                emptyDescription="Generated court applications will appear here."
                onRowPress={(item) => router.push(`/admin/applications/${item.id}` as any)}
              />
            </View>
          </View>
        </View>
      )}
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 24,
  },
  refreshHeaderBtn: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#12203B",
    borderWidth: 1,
    borderColor: "#253452",
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 8,
    gap: 6,
  },
  refreshHeaderText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#C5A059",
  },
  kpiGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 16,
  },
  quickActionsCard: {
    backgroundColor: "#0B1B3D",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#1B2A49",
    padding: 18,
  },
  quickActionsTitle: {
    fontSize: 13,
    fontWeight: "700",
    color: "#8B96A9",
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 12,
  },
  quickActionsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
  },
  quickActionBtn: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#12203B",
    borderWidth: 1,
    borderColor: "#253452",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    gap: 8,
    flex: 1,
    minWidth: 200,
  },
  quickActionLabel: {
    fontSize: 13,
    fontWeight: "600",
    color: "#D1D8E5",
  },
  tablesSplit: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 24,
  },
  tableCol: {
    flex: 1,
    minWidth: 340,
  },
  sectionHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 12,
  },
  sectionTitleWithIcon: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#FDFDFD",
  },
  viewAllBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    padding: 4,
  },
  viewAllText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#C5A059",
  },
  cellPrimary: {
    fontSize: 13,
    fontWeight: "600",
    color: "#FDFDFD",
  },
  cellMuted: {
    fontSize: 11,
    color: "#8B96A9",
    marginTop: 2,
  },
  cellDate: {
    fontSize: 12,
    color: "#D1D8E5",
  },
  tableActionBtn: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
    backgroundColor: "rgba(197, 160, 89, 0.12)",
    gap: 4,
  },
  tableActionText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#C5A059",
  },
});

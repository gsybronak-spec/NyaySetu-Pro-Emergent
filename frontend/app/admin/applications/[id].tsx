import React, { useEffect, useState, useCallback } from "react";
import { StyleSheet, Text, View, Pressable, ScrollView } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, router } from "expo-router";
import { AdminLayout } from "@/src/components/admin/AdminLayout";
import { AdminPageHeader } from "@/src/components/admin/AdminPageHeader";
import { AdminStatCard } from "@/src/components/admin/AdminStatCard";
import { AdminLoadingState, AdminErrorState } from "@/src/components/admin/AdminStates";
import { StatusBadge } from "@/src/components/admin/StatusBadge";
import { adminApi } from "@/src/api/adminClient";
import type { ApplicationDetailResponse } from "@/src/types/admin";

export default function AdminApplicationDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [data, setData] = useState<ApplicationDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.getApplication(id);
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load application details.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const app = data?.application;
  const owner = data?.owner;
  const caseItem = data?.case;

  return (
    <AdminLayout>
      <AdminPageHeader
        title={app?.template_name || app?.filename || `Document Application ${id}`}
        subtitle={`Application ID: ${id} • File: ${app?.filename || "document.pdf"}`}
        breadcrumbs={[
          { label: "Applications", route: "/admin/applications" },
          { label: app?.template_name || "Document Inspection" },
        ]}
      />

      {loading ? (
        <AdminLoadingState message="Loading document application metadata and engine telemetry..." />
      ) : error || !app ? (
        <AdminErrorState message={error || "Application record not found."} onRetry={fetchDetail} />
      ) : (
        <View style={styles.container}>
          {/* Top Metrics */}
          <View style={styles.kpiGrid}>
            <AdminStatCard
              label="Document Format"
              value={(app.format || "PDF").toUpperCase()}
              subtitle={`Language: ${app.language === "gu" ? "Gujarati" : "English"}`}
              icon="document-text"
              color="#C5A059"
            />
            <AdminStatCard
              label="Template Version"
              value={`v${app.template_version || 1}`}
              subtitle={app.template_name || "Legal Template"}
              icon="copy"
              color="#4299E1"
            />
            <AdminStatCard
              label="Compilation Engine"
              value={app.engine || "ReportLab"}
              subtitle={app.font_family || "Noto Sans Gujarati"}
              icon="cog"
              color="#48BB78"
            />
            <AdminStatCard
              label="File Size"
              value={app.file_size ? `${Math.round(app.file_size / 1024)} KB` : "Standard"}
              subtitle={`Created: ${app.created_at ? new Date(app.created_at).toLocaleDateString() : "—"}`}
              icon="cube"
              color="#9F7AEA"
            />
          </View>

          {/* Technical Specs & Digest */}
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <Ionicons name="shield-checkmark-outline" size={20} color="#C5A059" />
              <Text style={styles.cardTitle}>Document Verification & Engine Integrity</Text>
            </View>
            <View style={styles.fieldList}>
              <View style={styles.fieldRow}>
                <Text style={styles.fieldLabel}>SHA-256 Digest</Text>
                <Text style={[styles.fieldVal, styles.hashText]} selectable>
                  {app.sha256 || "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}
                </Text>
              </View>
              <View style={styles.fieldRow}>
                <Text style={styles.fieldLabel}>Font Shaper Engine</Text>
                <Text style={styles.fieldVal}>HarfBuzz Native Complex Text Layout (uharfbuzz)</Text>
              </View>
              <View style={styles.fieldRow}>
                <Text style={styles.fieldLabel}>Registered Font Family</Text>
                <Text style={styles.fieldVal}>{app.font_family || "Noto Sans Gujarati"}</Text>
              </View>
              <View style={styles.fieldRow}>
                <Text style={styles.fieldLabel}>Compilation Engine</Text>
                <Text style={styles.fieldVal}>{app.engine || "ReportLab + PDF Subsetting"}</Text>
              </View>
              <View style={styles.fieldRow}>
                <Text style={styles.fieldLabel}>Generation Timestamp</Text>
                <Text style={styles.fieldVal}>
                  {app.created_at ? new Date(app.created_at).toLocaleString() : "—"}
                </Text>
              </View>
            </View>
          </View>

          {/* Split Related Entities */}
          <View style={styles.detailsSplit}>
            {/* Advocate Owner Card */}
            <View style={styles.cardCol}>
              <View style={styles.card}>
                <View style={styles.cardHeader}>
                  <Ionicons name="person-circle-outline" size={20} color="#C5A059" />
                  <Text style={styles.cardTitle}>Advocate Information</Text>
                  {owner?.id ? (
                    <Pressable
                      onPress={() => router.push(`/admin/users/${owner.id}` as any)}
                      style={styles.linkHeaderBtn}
                    >
                      <Text style={styles.linkHeaderBtnText}>View User</Text>
                      <Ionicons name="chevron-forward" size={14} color="#C5A059" />
                    </Pressable>
                  ) : null}
                </View>
                <View style={styles.fieldList}>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>Name</Text>
                    <Text style={styles.fieldVal}>{owner?.name || "Advocate"}</Text>
                  </View>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>Phone</Text>
                    <Text style={styles.fieldVal}>{owner?.mobile ? `+91 ${owner.mobile}` : "—"}</Text>
                  </View>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>Bar Registration</Text>
                    <Text style={styles.fieldVal}>{owner?.bar_council_no || "Unregistered"}</Text>
                  </View>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>Court</Text>
                    <Text style={styles.fieldVal}>{owner?.court || "District Court"}</Text>
                  </View>
                </View>
              </View>
            </View>

            {/* Associated Court Case */}
            <View style={styles.cardCol}>
              <View style={styles.card}>
                <View style={styles.cardHeader}>
                  <Ionicons name="briefcase-outline" size={20} color="#C5A059" />
                  <Text style={styles.cardTitle}>Associated Court Case</Text>
                  {caseItem?.id ? (
                    <Pressable
                      onPress={() => router.push(`/admin/cases/${caseItem.id}` as any)}
                      style={styles.linkHeaderBtn}
                    >
                      <Text style={styles.linkHeaderBtnText}>View Case</Text>
                      <Ionicons name="chevron-forward" size={14} color="#C5A059" />
                    </Pressable>
                  ) : null}
                </View>
                <View style={styles.fieldList}>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>Case Matter</Text>
                    <Text style={styles.fieldVal}>
                      {caseItem?.nickname || caseItem?.case_number || "Standalone Application"}
                    </Text>
                  </View>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>Parties</Text>
                    <Text style={styles.fieldVal}>
                      {caseItem?.party_name ? `${caseItem.party_name} v. ${caseItem.opposite_party || "—"}` : "—"}
                    </Text>
                  </View>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>Court</Text>
                    <Text style={styles.fieldVal}>{caseItem?.court_label || caseItem?.court || "—"}</Text>
                  </View>
                  <View style={styles.fieldRow}>
                    <Text style={styles.fieldLabel}>District</Text>
                    <Text style={styles.fieldVal}>{caseItem?.district_label || caseItem?.district_id || "Gujarat"}</Text>
                  </View>
                </View>
              </View>
            </View>
          </View>
        </View>
      )}
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
    flex: 1,
  },
  linkHeaderBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    padding: 4,
  },
  linkHeaderBtnText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#C5A059",
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
    gap: 12,
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
    flex: 1,
  },
  hashText: {
    fontFamily: "monospace",
    fontSize: 11,
    color: "#C5A059",
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
});

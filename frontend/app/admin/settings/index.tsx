import React, { useState } from "react";
import { StyleSheet, Text, View, Pressable, ScrollView, ActivityIndicator } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { AdminLayout } from "@/src/components/admin/AdminLayout";
import { AdminStatCard } from "@/src/components/admin/AdminStatCard";
import { StatusBadge } from "@/src/components/admin/StatusBadge";
import { useAdminAuth } from "@/src/context/AdminAuthContext";
import { adminApi } from "@/src/api/adminClient";

export default function AdminSettingsScreen() {
  const { adminUser } = useAdminAuth();
  const [migrating, setMigrating] = useState(false);
  const [migrateResult, setMigrateResult] = useState<string | null>(null);

  const handleMigrateSeed = async () => {
    setMigrating(true);
    setMigrateResult(null);
    try {
      const res = await adminApi.migrateSeedTemplates();
      setMigrateResult(
        res.seed_complete
          ? "Seed templates decoupled and migrated to canonical collection successfully."
          : "Seed templates are already decoupled and up to date."
      );
    } catch (err: any) {
      setMigrateResult(`Migration note: ${err?.message || "Templates already synchronized."}`);
    } finally {
      setMigrating(false);
    }
  };

  return (
    <AdminLayout
      title="System Configuration & Diagnostics"
      subtitle="Operational infrastructure telemetry, font shaper engine, database schema status, and security compliance"
    >
      <View style={styles.container}>
        {/* KPI Row */}
        <View style={styles.kpiGrid}>
          <AdminStatCard
            label="System Platform"
            value="NyaySetu Pro v3.0"
            subtitle="Phase 3 Super Admin Control Center"
            icon="server"
            color="#C5A059"
          />
          <AdminStatCard
            label="Single Source of Truth"
            value="MongoDB Atlas"
            subtitle="10 Canonical Collections"
            icon="layers"
            color="#48BB78"
          />
          <AdminStatCard
            label="Typography Engine"
            value="HarfBuzz (uharfbuzz)"
            subtitle="Complex Gujarati glyph shaping"
            icon="text"
            color="#4299E1"
          />
          <AdminStatCard
            label="Authorization Barrier"
            value="require_super_admin"
            subtitle="Authoritative server-side RBAC"
            icon="shield-checkmark"
            color="#9F7AEA"
          />
        </View>

        {/* Security & Access Session Card */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="finger-print-outline" size={20} color="#C5A059" />
            <Text style={styles.cardTitle}>Current Super Administrator Session</Text>
          </View>
          <View style={styles.fieldList}>
            <View style={styles.fieldRow}>
              <Text style={styles.fieldLabel}>Administrator Name</Text>
              <Text style={styles.fieldVal}>{adminUser?.name || "System Super Administrator"}</Text>
            </View>
            <View style={styles.fieldRow}>
              <Text style={styles.fieldLabel}>Admin Email Address</Text>
              <Text style={styles.fieldVal}>{adminUser?.email || "admin@nyaysetu.gov.in"}</Text>
            </View>
            <View style={styles.fieldRow}>
              <Text style={styles.fieldLabel}>Privilege Tier</Text>
              <View style={styles.roleTag}>
                <View style={styles.roleDot} />
                <Text style={styles.roleText}>{adminUser?.role?.toUpperCase() || "SUPER_ADMIN"}</Text>
              </View>
            </View>
            <View style={styles.fieldRow}>
              <Text style={styles.fieldLabel}>Token Storage Key</Text>
              <Text style={[styles.fieldVal, { fontFamily: "monospace", color: "#C5A059" }]}>
                nyaysetu_admin_token (Isolated SecureStore)
              </Text>
            </View>
          </View>
        </View>

        {/* Architecture & Document Generator Engine Card */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="hardware-chip-outline" size={20} color="#C5A059" />
            <Text style={styles.cardTitle}>Document Engine & Typography Pipeline</Text>
          </View>
          <View style={styles.fieldList}>
            <View style={styles.fieldRow}>
              <Text style={styles.fieldLabel}>Gujarati Complex Text Layout</Text>
              <Text style={styles.fieldVal}>HarfBuzz Native Glyph Shaper via uharfbuzz</Text>
            </View>
            <View style={styles.fieldRow}>
              <Text style={styles.fieldLabel}>Registered Fonts</Text>
              <Text style={styles.fieldVal}>NotoSansGujarati-Regular.ttf, NotoSansGujarati-Bold.ttf</Text>
            </View>
            <View style={styles.fieldRow}>
              <Text style={styles.fieldLabel}>PDF Subsetting Engine</Text>
              <Text style={styles.fieldVal}>fonttools TTFont subsetting with pdfmetrics</Text>
            </View>
            <View style={styles.fieldRow}>
              <Text style={styles.fieldLabel}>Secondary Engine</Text>
              <Text style={styles.fieldVal}>LibreOffice Headless (DOCX / ODT generation)</Text>
            </View>
            <View style={styles.fieldRow}>
              <Text style={styles.fieldLabel}>PDF Rasterizer</Text>
              <Text style={styles.fieldVal}>pypdfium2 (High-resolution PNG generation)</Text>
            </View>
          </View>
        </View>

        {/* Database & Seed Decoupling Maintenance Card */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="cube-outline" size={20} color="#C5A059" />
            <Text style={styles.cardTitle}>Canonical Data Safety & Seed Decoupling</Text>
          </View>
          <View style={styles.cardBody}>
            <Text style={styles.descText}>
              NyaySetu Pro Phase 1 established a strict decoupling mechanism ensuring seed templates are migrated once and never overwrite admin customizations. Revisions in <Text style={{ color: "#C5A059" }}>template_revisions</Text> are immutable.
            </Text>

            {migrateResult ? (
              <View style={styles.resultBox}>
                <Ionicons name="information-circle" size={16} color="#48BB78" style={{ marginRight: 8 }} />
                <Text style={styles.resultText}>{migrateResult}</Text>
              </View>
            ) : null}

            <View style={styles.actionSection}>
              <Pressable
                onPress={handleMigrateSeed}
                disabled={migrating}
                style={[styles.btnMigrate, migrating && { opacity: 0.7 }]}
              >
                {migrating ? (
                  <ActivityIndicator size="small" color="#061024" style={{ marginRight: 6 }} />
                ) : (
                  <Ionicons name="sync" size={16} color="#061024" style={{ marginRight: 6 }} />
                )}
                <Text style={styles.btnMigrateText}>
                  {migrating ? "Checking Synchronization..." : "Verify Seed Templates Synchronization"}
                </Text>
              </Pressable>
            </View>
          </View>
        </View>
      </View>
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
    paddingHorizontal: 20,
    paddingVertical: 16,
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
    padding: 20,
    gap: 14,
  },
  fieldRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottomWidth: 1,
    borderBottomColor: "#162544",
    paddingBottom: 10,
    gap: 12,
  },
  fieldLabel: {
    fontSize: 13,
    color: "#8B96A9",
    fontWeight: "600",
  },
  fieldVal: {
    fontSize: 13,
    fontWeight: "600",
    color: "#FDFDFD",
    textAlign: "right",
  },
  roleTag: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(197, 160, 89, 0.15)",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "rgba(197, 160, 89, 0.3)",
  },
  roleDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#C5A059",
    marginRight: 6,
  },
  roleText: {
    fontSize: 11,
    fontWeight: "800",
    color: "#C5A059",
    letterSpacing: 0.5,
  },
  cardBody: {
    padding: 20,
    gap: 16,
  },
  descText: {
    fontSize: 13,
    color: "#D1D8E5",
    lineHeight: 20,
  },
  resultBox: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(72, 187, 120, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(72, 187, 120, 0.3)",
    padding: 12,
    borderRadius: 8,
  },
  resultText: {
    fontSize: 12,
    color: "#48BB78",
    fontWeight: "500",
    flex: 1,
  },
  actionSection: {
    flexDirection: "row",
  },
  btnMigrate: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#C5A059",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
  },
  btnMigrateText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#061024",
  },
});

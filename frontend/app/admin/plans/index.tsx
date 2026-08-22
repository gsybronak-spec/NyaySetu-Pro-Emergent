import React, { useEffect, useState, useCallback } from "react";
import {
  StyleSheet,
  Text,
  View,
  Pressable,
  TextInput,
  Modal,
  ScrollView,
  ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { AdminLayout } from "@/src/components/admin/AdminLayout";
import { AdminDataTable, ColumnDef } from "@/src/components/admin/AdminDataTable";
import { AdminStatCard } from "@/src/components/admin/AdminStatCard";
import { StatusBadge } from "@/src/components/admin/StatusBadge";
import { ConfirmDialog } from "@/src/components/admin/ConfirmDialog";
import { adminApi } from "@/src/api/adminClient";
import type { AdminPlanItem } from "@/src/types/admin";

export default function AdminPlansScreen() {
  const [plans, setPlans] = useState<AdminPlanItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create / Edit Modal State
  const [modalVisible, setModalVisible] = useState(false);
  const [editingPlan, setEditingPlan] = useState<AdminPlanItem | null>(null);
  const [formName, setFormName] = useState("");
  const [formCredits, setFormCredits] = useState("");
  const [formPrice, setFormPrice] = useState("");
  const [formOriginalPrice, setFormOriginalPrice] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formPopular, setFormPopular] = useState(false);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Status Action State
  const [targetPlan, setTargetPlan] = useState<AdminPlanItem | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchPlans = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.listPlans();
      setPlans(Array.isArray(res) ? res : []);
    } catch (err: any) {
      setError(err?.message || "Failed to load pricing plans.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlans();
  }, [fetchPlans]);

  const openCreateModal = () => {
    setEditingPlan(null);
    setFormName("");
    setFormCredits("50");
    setFormPrice("499");
    setFormOriginalPrice("999");
    setFormDescription("");
    setFormPopular(false);
    setFormError(null);
    setModalVisible(true);
  };

  const openEditModal = (p: AdminPlanItem) => {
    setEditingPlan(p);
    setFormName(p.name || "");
    setFormCredits(String(p.credits || "0"));
    setFormPrice(String(p.price || "0"));
    setFormOriginalPrice(String(p.original_price || p.price || "0"));
    setFormDescription(p.description || "");
    setFormPopular(!!p.popular);
    setFormError(null);
    setModalVisible(true);
  };

  const handleSavePlan = async () => {
    if (!formName.trim()) {
      setFormError("Plan name is required.");
      return;
    }
    const creditsNum = parseInt(formCredits);
    const priceNum = parseFloat(formPrice);
    if (isNaN(creditsNum) || creditsNum <= 0) {
      setFormError("Credits must be a positive integer.");
      return;
    }
    if (isNaN(priceNum) || priceNum < 0) {
      setFormError("Price must be a valid number in INR.");
      return;
    }

    setFormSubmitting(true);
    setFormError(null);
    try {
      const payload: Partial<AdminPlanItem> = {
        name: formName.trim(),
        credits: creditsNum,
        price: priceNum,
        original_price: parseFloat(formOriginalPrice) || priceNum,
        description: formDescription.trim() || undefined,
        popular: formPopular,
        active: true,
      };

      if (editingPlan) {
        await adminApi.updatePlan(editingPlan.id, payload);
      } else {
        await adminApi.createPlan(payload);
      }

      setModalVisible(false);
      await fetchPlans();
    } catch (err: any) {
      setFormError(err?.message || "Failed to save pricing plan.");
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleToggleStatus = async () => {
    if (!targetPlan) return;
    setActionLoading(true);
    try {
      if (targetPlan.active) {
        await adminApi.deactivatePlan(targetPlan.id);
      } else {
        await adminApi.activatePlan(targetPlan.id);
      }
      setTargetPlan(null);
      await fetchPlans();
    } catch (err: any) {
      alert(err?.message || "Failed to toggle plan status.");
    } finally {
      setActionLoading(false);
    }
  };

  const activeCount = plans.filter((p) => p.active).length;

  const columns: ColumnDef<AdminPlanItem>[] = [
    {
      key: "name",
      header: "Plan Name & Details",
      flex: 1.8,
      render: (p) => (
        <View>
          <View style={styles.titleWithBadge}>
            <Text style={styles.cellTitle}>{p.name}</Text>
            {p.popular && (
              <View style={styles.popularBadge}>
                <Text style={styles.popularText}>POPULAR</Text>
              </View>
            )}
          </View>
          <Text style={styles.cellSub}>{p.description || "Credit top-up package"}</Text>
        </View>
      ),
    },
    {
      key: "credits",
      header: "Credits Included",
      width: 140,
      render: (p) => (
        <View style={styles.creditsBadge}>
          <Ionicons name="diamond" size={13} color="#C5A059" style={{ marginRight: 4 }} />
          <Text style={styles.creditsText}>{p.credits} Credits</Text>
        </View>
      ),
    },
    {
      key: "price",
      header: "Price (INR)",
      width: 140,
      render: (p) => (
        <View>
          <Text style={styles.priceText}>₹{p.price}</Text>
          {p.original_price && p.original_price > p.price ? (
            <Text style={styles.strikePrice}>₹{p.original_price}</Text>
          ) : null}
        </View>
      ),
    },
    {
      key: "active",
      header: "Status",
      width: 110,
      render: (p) => (
        <StatusBadge
          status={p.active ? "active" : "disabled"}
          label={p.active ? "ACTIVE" : "INACTIVE"}
          size="sm"
        />
      ),
    },
    {
      key: "actions",
      header: "Actions",
      width: 120,
      align: "right",
      render: (p) => (
        <View style={styles.actionRow}>
          <Pressable
            onPress={() => openEditModal(p)}
            style={styles.actionIconBtn}
            accessibilityLabel="Edit Plan"
          >
            <Ionicons name="create-outline" size={15} color="#C5A059" />
          </Pressable>

          <Pressable
            onPress={() => setTargetPlan(p)}
            style={[
              styles.actionIconBtn,
              { backgroundColor: p.active ? "rgba(236, 201, 75, 0.15)" : "rgba(72, 187, 120, 0.15)" },
            ]}
            accessibilityLabel={p.active ? "Deactivate Plan" : "Activate Plan"}
          >
            <Ionicons
              name={p.active ? "pause-outline" : "play-outline"}
              size={15}
              color={p.active ? "#ECC94B" : "#48BB78"}
            />
          </Pressable>
        </View>
      ),
    },
  ];

  return (
    <AdminLayout
      title="Pricing Plans & Credit Packages"
      subtitle="Configure advocate subscription tiers, credit top-up packages, and payment rates"
      actions={
        <Pressable onPress={openCreateModal} style={styles.createBtn}>
          <Ionicons name="add" size={16} color="#061024" />
          <Text style={styles.createBtnText}>New Package</Text>
        </Pressable>
      }
    >
      <View style={styles.container}>
        {/* KPI Row */}
        <View style={styles.kpiGrid}>
          <AdminStatCard
            label="Total Active Plans"
            value={activeCount}
            subtitle={`${plans.length} total packages in catalog`}
            icon="card"
            color="#48BB78"
          />
          <AdminStatCard
            label="Default Free Credits"
            value="10 Credits"
            subtitle="Granted upon advocate verification"
            icon="gift"
            color="#C5A059"
          />
          <AdminStatCard
            label="Standard Document Rate"
            value="1 Credit"
            subtitle="Per HarfBuzz shaped legal draft"
            icon="document-text"
            color="#4299E1"
          />
        </View>

        {/* Data Table */}
        <AdminDataTable
          columns={columns}
          data={plans}
          keyExtractor={(p) => p.id}
          loading={loading}
          error={error}
          onRetry={fetchPlans}
          emptyTitle="No pricing packages defined"
          emptyDescription="Create your first subscription or credit top-up package."
        />
      </View>

      {/* Confirmation Dialog */}
      <ConfirmDialog
        visible={!!targetPlan}
        title={targetPlan?.active ? "Deactivate Plan" : "Activate Plan"}
        message={
          targetPlan?.active
            ? `Are you sure you want to deactivate package "${targetPlan?.name}"? It will no longer be visible to advocates in the wallet store.`
            : `Are you sure you want to activate package "${targetPlan?.name}"?`
        }
        confirmVariant={targetPlan?.active ? "warning" : "primary"}
        confirmLabel={targetPlan?.active ? "Deactivate Package" : "Activate Package"}
        loading={actionLoading}
        onConfirm={handleToggleStatus}
        onCancel={() => setTargetPlan(null)}
      />

      {/* Create / Edit Plan Modal */}
      <Modal
        visible={modalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <Ionicons name="card-outline" size={20} color="#C5A059" />
              <View style={{ flex: 1, marginLeft: 8 }}>
                <Text style={styles.modalTitle}>
                  {editingPlan ? "Edit Pricing Package" : "Create Pricing Package"}
                </Text>
                <Text style={styles.modalSub}>
                  Set credits amount, pricing in INR, and promotional tags
                </Text>
              </View>
              <Pressable onPress={() => setModalVisible(false)} style={{ padding: 4 }}>
                <Ionicons name="close" size={20} color="#8B96A9" />
              </Pressable>
            </View>

            <View style={styles.modalBody}>
              {formError ? (
                <View style={styles.errorBox}>
                  <Ionicons name="alert-circle" size={16} color="#E53E3E" style={{ marginRight: 6 }} />
                  <Text style={styles.errorText}>{formError}</Text>
                </View>
              ) : null}

              <View style={styles.field}>
                <Text style={styles.fieldLabel}>Package Name *</Text>
                <TextInput
                  style={styles.input}
                  placeholder="E.g. Professional Starter Pack"
                  placeholderTextColor="#6B7280"
                  value={formName}
                  onChangeText={setFormName}
                />
              </View>

              <View style={styles.splitRow}>
                <View style={[styles.field, { flex: 1 }]}>
                  <Text style={styles.fieldLabel}>Credits Included *</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="E.g. 50"
                    placeholderTextColor="#6B7280"
                    keyboardType="numeric"
                    value={formCredits}
                    onChangeText={setFormCredits}
                  />
                </View>

                <View style={[styles.field, { flex: 1 }]}>
                  <Text style={styles.fieldLabel}>Price (₹ INR) *</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="E.g. 499"
                    placeholderTextColor="#6B7280"
                    keyboardType="numeric"
                    value={formPrice}
                    onChangeText={setFormPrice}
                  />
                </View>
              </View>

              <View style={styles.field}>
                <Text style={styles.fieldLabel}>Original Strike-through Price (₹ INR)</Text>
                <TextInput
                  style={styles.input}
                  placeholder="E.g. 999 (shows discount badge)"
                  placeholderTextColor="#6B7280"
                  keyboardType="numeric"
                  value={formOriginalPrice}
                  onChangeText={setFormOriginalPrice}
                />
              </View>

              <View style={styles.field}>
                <Text style={styles.fieldLabel}>Description</Text>
                <TextInput
                  style={[styles.input, { height: 60 }]}
                  placeholder="Short description of this tier..."
                  placeholderTextColor="#6B7280"
                  multiline
                  value={formDescription}
                  onChangeText={setFormDescription}
                />
              </View>

              <Pressable
                onPress={() => setFormPopular(!formPopular)}
                style={styles.checkboxRow}
              >
                <Ionicons
                  name={formPopular ? "checkbox" : "square-outline"}
                  size={18}
                  color={formPopular ? "#C5A059" : "#6B7280"}
                />
                <Text style={styles.checkboxLabel}>Mark as "Popular / Recommended" Plan</Text>
              </Pressable>
            </View>

            <View style={styles.modalFooter}>
              <Pressable
                onPress={() => setModalVisible(false)}
                style={styles.modalCancelBtn}
                disabled={formSubmitting}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </Pressable>
              <Pressable
                onPress={handleSavePlan}
                style={[styles.createBtn, formSubmitting && { opacity: 0.7 }]}
                disabled={formSubmitting}
              >
                {formSubmitting ? (
                  <ActivityIndicator size="small" color="#061024" style={{ marginRight: 6 }} />
                ) : null}
                <Text style={styles.createBtnText}>
                  {formSubmitting ? "Saving..." : editingPlan ? "Update Plan" : "Create Plan"}
                </Text>
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
    gap: 20,
  },
  kpiGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 16,
  },
  createBtn: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#C5A059",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
    gap: 6,
  },
  createBtnText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#061024",
  },
  titleWithBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  cellTitle: {
    fontSize: 13,
    fontWeight: "700",
    color: "#FDFDFD",
  },
  popularBadge: {
    backgroundColor: "rgba(197, 160, 89, 0.2)",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: "rgba(197, 160, 89, 0.4)",
  },
  popularText: {
    fontSize: 9,
    fontWeight: "800",
    color: "#C5A059",
    letterSpacing: 0.5,
  },
  cellSub: {
    fontSize: 11,
    color: "#8B96A9",
    marginTop: 2,
  },
  creditsBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#0D182E",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "#1B2A49",
    alignSelf: "flex-start",
  },
  creditsText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#C5A059",
  },
  priceText: {
    fontSize: 14,
    fontWeight: "700",
    color: "#FDFDFD",
  },
  strikePrice: {
    fontSize: 11,
    color: "#6B7280",
    textDecorationLine: "line-through",
  },
  actionRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  actionIconBtn: {
    width: 28,
    height: 28,
    borderRadius: 6,
    backgroundColor: "#1B2A49",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "#253452",
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
    maxWidth: 480,
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
  modalBody: {
    padding: 20,
    gap: 14,
  },
  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(229, 62, 62, 0.12)",
    borderWidth: 1,
    borderColor: "rgba(229, 62, 62, 0.3)",
    padding: 10,
    borderRadius: 8,
  },
  errorText: {
    fontSize: 12,
    color: "#F56565",
    flex: 1,
  },
  field: {
    gap: 6,
  },
  splitRow: {
    flexDirection: "row",
    gap: 12,
  },
  fieldLabel: {
    fontSize: 12,
    fontWeight: "600",
    color: "#D1D8E5",
  },
  input: {
    backgroundColor: "#0B182E",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#253452",
    paddingHorizontal: 12,
    paddingVertical: 9,
    color: "#FDFDFD",
    fontSize: 13,
  },
  checkboxRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 4,
  },
  checkboxLabel: {
    fontSize: 13,
    color: "#D1D8E5",
    fontWeight: "500",
  },
  modalFooter: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "flex-end",
    padding: 16,
    backgroundColor: "#0D182E",
    borderTopWidth: 1,
    borderTopColor: "#1B2A49",
    gap: 10,
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

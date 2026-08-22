import React, { useEffect, useState, useCallback } from "react";
import {
  StyleSheet,
  Text,
  View,
  Pressable,
  ScrollView,
  TextInput,
  Modal,
  ActivityIndicator,
} from "react-native";
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
import type { UserDetailResponse, TransactionItem } from "@/src/types/admin";

export default function AdminUserDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [data, setData] = useState<UserDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Status Action Modal State
  const [actionType, setActionType] = useState<"suspend" | "activate" | "ban" | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Credit Adjustment Modal State
  const [adjustModalVisible, setAdjustModalVisible] = useState(false);
  const [creditAmount, setCreditAmount] = useState("");
  const [creditReason, setCreditReason] = useState("");
  const [adjustSubmitting, setAdjustSubmitting] = useState(false);
  const [adjustError, setAdjustError] = useState<string | null>(null);

  const fetchUserDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.getUser(id);
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to fetch advocate profile.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchUserDetail();
  }, [fetchUserDetail]);

  const handleStatusChange = async () => {
    if (!id || !actionType) return;
    setActionLoading(true);
    try {
      if (actionType === "suspend") {
        await adminApi.suspendUser(id);
      } else if (actionType === "activate") {
        await adminApi.activateUser(id);
      } else if (actionType === "ban") {
        await adminApi.banUser(id);
      }
      setActionType(null);
      await fetchUserDetail();
    } catch (err: any) {
      alert(err?.message || "Failed to update account status.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleAdjustWallet = async () => {
    if (!id) return;
    const amt = parseFloat(creditAmount);
    if (isNaN(amt) || amt === 0) {
      setAdjustError("Please enter a valid non-zero credit number.");
      return;
    }
    if (!creditReason.trim()) {
      setAdjustError("Mandatory reason required for audit tracking.");
      return;
    }

    setAdjustSubmitting(true);
    setAdjustError(null);
    try {
      await adminApi.adjustUserWallet(id, {
        amount: amt,
        reason: creditReason.trim(),
      });
      setAdjustModalVisible(false);
      setCreditAmount("");
      setCreditReason("");
      await fetchUserDetail();
    } catch (err: any) {
      setAdjustError(err?.message || "Failed to adjust credits ledger.");
    } finally {
      setAdjustSubmitting(false);
    }
  };

  const transactionColumns: ColumnDef<TransactionItem>[] = [
    {
      key: "type",
      header: "Type",
      width: 140,
      render: (t) => <StatusBadge status={t.type} size="sm" />,
    },
    {
      key: "credits",
      header: "Credits Change",
      width: 130,
      render: (t) => {
        const isPositive = (t.credits ?? 0) >= 0;
        return (
          <Text
            style={[
              styles.ledgerAmt,
              { color: isPositive ? "#48BB78" : "#F56565" },
            ]}
          >
            {isPositive ? `+${t.credits}` : t.credits} Cr
          </Text>
        );
      },
    },
    {
      key: "balance",
      header: "Balance After",
      width: 120,
      render: (t) => (
        <Text style={styles.cellText}>
          {t.balance_after !== undefined ? `${t.balance_after} Cr` : "—"}
        </Text>
      ),
    },
    {
      key: "reason",
      header: "Reason / Note",
      flex: 1.5,
      render: (t) => (
        <View>
          <Text style={styles.cellText}>{t.reason || t.reference || "Transaction ledger entry"}</Text>
          {t.admin_email ? (
            <Text style={styles.cellMutedSm}>Admin: {t.admin_email}</Text>
          ) : null}
        </View>
      ),
    },
    {
      key: "created_at",
      header: "Timestamp",
      width: 150,
      render: (t) => (
        <Text style={styles.cellDate}>
          {t.created_at ? new Date(t.created_at).toLocaleString() : "—"}
        </Text>
      ),
    },
  ];

  const user = data?.user;
  const wallet = data?.wallet;
  const isActive = user?.status === "active" || (user?.active && user?.status !== "banned" && user?.status !== "suspended");

  return (
    <AdminLayout>
      <AdminPageHeader
        title={user?.name || user?.advocate_name_en || `Advocate ${user?.mobile || ""}`}
        subtitle={`Advocate ID: ${id} • Bar Council: ${user?.bar_council_no || "Unregistered"}`}
        breadcrumbs={[
          { label: "Users", route: "/admin/users" },
          { label: user?.name || "Advocate Details" },
        ]}
        actionLabel="Adjust Credits"
        actionIcon="diamond-outline"
        onAction={() => {
          setAdjustModalVisible(true);
          setCreditAmount("");
          setCreditReason("");
          setAdjustError(null);
        }}
      />

      {loading ? (
        <AdminLoadingState message="Loading advocate profile and transaction ledger..." />
      ) : error || !user ? (
        <AdminErrorState message={error || "Advocate record not found."} onRetry={fetchUserDetail} />
      ) : (
        <View style={styles.container}>
          {/* Top Metric Cards */}
          <View style={styles.kpiGrid}>
            <AdminStatCard
              label="Wallet Balance"
              value={`${wallet?.balance ?? user?.wallet_balance ?? 0} Credits`}
              subtitle={`Total Used: ${wallet?.total_used ?? 0} Cr`}
              icon="diamond"
              color="#C5A059"
            />
            <AdminStatCard
              label="Active Court Cases"
              value={data?.cases_count ?? 0}
              subtitle="Managed client matters"
              icon="briefcase"
              color="#4299E1"
              onPress={() => router.push(`/admin/cases?user_id=${id}` as any)}
            />
            <AdminStatCard
              label="Generated Applications"
              value={data?.applications_count ?? 0}
              subtitle="Legal draft documents"
              icon="document-text"
              color="#9F7AEA"
              onPress={() => router.push(`/admin/applications?user_id=${id}` as any)}
            />
            <AdminStatCard
              label="Account Status"
              value={user.status ? user.status.toUpperCase() : user.active ? "ACTIVE" : "SUSPENDED"}
              subtitle={`Joined: ${user.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}`}
              icon="shield-checkmark"
              color={isActive ? "#48BB78" : "#E53E3E"}
            />
          </View>

          {/* Profile Overview Card */}
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <View style={styles.cardHeaderLeft}>
                <Ionicons name="person-circle-outline" size={22} color="#C5A059" />
                <Text style={styles.cardTitle}>Advocate Profile & Registration</Text>
              </View>
              <View style={styles.statusGroup}>
                <StatusBadge status={user.status || (user.active ? "active" : "suspended")} />
                {user.profile_completed || user.is_profile_complete ? (
                  <StatusBadge status="verified" label="PROFILE COMPLETE" />
                ) : (
                  <StatusBadge status="pending" label="PROFILE INCOMPLETE" />
                )}
              </View>
            </View>

            <View style={styles.profileGrid}>
              <View style={styles.profileField}>
                <Text style={styles.fieldLabel}>Full Name</Text>
                <Text style={styles.fieldValue}>{user.name || user.advocate_name_en || "—"}</Text>
              </View>

              <View style={styles.profileField}>
                <Text style={styles.fieldLabel}>Mobile Number</Text>
                <Text style={styles.fieldValue}>{user.mobile ? `+91 ${user.mobile}` : "—"}</Text>
              </View>

              <View style={styles.profileField}>
                <Text style={styles.fieldLabel}>Email Address</Text>
                <Text style={styles.fieldValue}>{user.email || "—"}</Text>
              </View>

              <View style={styles.profileField}>
                <Text style={styles.fieldLabel}>Bar Council Registration No</Text>
                <Text style={styles.fieldValue}>{user.bar_council_no || "Not submitted"}</Text>
              </View>

              <View style={styles.profileField}>
                <Text style={styles.fieldLabel}>State & District</Text>
                <Text style={styles.fieldValue}>
                  {user.district || "—"}, {user.state || "Gujarat"}
                </Text>
              </View>

              <View style={styles.profileField}>
                <Text style={styles.fieldLabel}>Primary Court</Text>
                <Text style={styles.fieldValue}>{user.court || "District Court"}</Text>
              </View>
            </View>

            {/* Account Status Control Actions */}
            <View style={styles.cardActions}>
              <Text style={styles.actionSectionTitle}>Administrative Controls:</Text>
              <View style={styles.actionButtons}>
                {isActive ? (
                  <Pressable
                    onPress={() => setActionType("suspend")}
                    style={[styles.btnAction, { backgroundColor: "rgba(236, 201, 75, 0.15)", borderColor: "#ECC94B" }]}
                  >
                    <Ionicons name="pause" size={14} color="#ECC94B" />
                    <Text style={[styles.btnActionText, { color: "#ECC94B" }]}>Suspend Account</Text>
                  </Pressable>
                ) : (
                  <Pressable
                    onPress={() => setActionType("activate")}
                    style={[styles.btnAction, { backgroundColor: "rgba(72, 187, 120, 0.15)", borderColor: "#48BB78" }]}
                  >
                    <Ionicons name="play" size={14} color="#48BB78" />
                    <Text style={[styles.btnActionText, { color: "#48BB78" }]}>Reactivate Account</Text>
                  </Pressable>
                )}

                {user.status !== "banned" && (
                  <Pressable
                    onPress={() => setActionType("ban")}
                    style={[styles.btnAction, { backgroundColor: "rgba(229, 62, 62, 0.15)", borderColor: "#E53E3E" }]}
                  >
                    <Ionicons name="ban" size={14} color="#E53E3E" />
                    <Text style={[styles.btnActionText, { color: "#E53E3E" }]}>Ban Account</Text>
                  </Pressable>
                )}
              </View>
            </View>
          </View>

          {/* Wallet Transaction Ledger */}
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <View style={styles.cardHeaderLeft}>
                <Ionicons name="receipt-outline" size={22} color="#C5A059" />
                <Text style={styles.cardTitle}>Credits Ledger & Transaction History</Text>
              </View>
              <Pressable
                onPress={() => {
                  setAdjustModalVisible(true);
                  setCreditAmount("");
                  setCreditReason("");
                  setAdjustError(null);
                }}
                style={styles.btnSmGold}
              >
                <Ionicons name="add" size={14} color="#061024" />
                <Text style={styles.btnSmGoldText}>Adjust Ledger</Text>
              </Pressable>
            </View>

            <AdminDataTable
              columns={transactionColumns}
              data={data?.recent_transactions || []}
              keyExtractor={(t) => t.id}
              emptyTitle="No wallet transactions recorded"
              emptyDescription="Credits grants, document debits, and adjustments will appear here."
            />
          </View>
        </View>
      )}

      {/* Status Confirmation Modal */}
      <ConfirmDialog
        visible={!!actionType}
        title={
          actionType === "suspend"
            ? "Suspend Advocate Account"
            : actionType === "ban"
            ? "Permanently Ban Advocate Account"
            : "Activate Advocate Account"
        }
        message={`Are you sure you want to change the status of ${user?.name || user?.mobile} to ${actionType?.toUpperCase()}?`}
        impactWarning={
          actionType === "ban"
            ? "Banning revokes all active session tokens and restricts document generation access immediately."
            : undefined
        }
        confirmVariant={actionType === "ban" ? "danger" : actionType === "suspend" ? "warning" : "primary"}
        confirmLabel={`${actionType?.toUpperCase()} Account`}
        loading={actionLoading}
        onConfirm={handleStatusChange}
        onCancel={() => setActionType(null)}
      />

      {/* Credit Adjustment Modal */}
      <Modal
        visible={adjustModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setAdjustModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <View style={styles.modalHeaderIcon}>
                <Ionicons name="diamond" size={20} color="#C5A059" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.modalTitle}>Adjust Advocate Credits</Text>
                <Text style={styles.modalSub}>{user?.name || user?.mobile}</Text>
              </View>
              <Pressable onPress={() => setAdjustModalVisible(false)} style={{ padding: 4 }}>
                <Ionicons name="close" size={20} color="#8B96A9" />
              </Pressable>
            </View>

            <View style={styles.modalBody}>
              {adjustError ? (
                <View style={styles.modalErrorBox}>
                  <Ionicons name="alert-circle" size={16} color="#E53E3E" style={{ marginRight: 6 }} />
                  <Text style={styles.modalErrorText}>{adjustError}</Text>
                </View>
              ) : null}

              <View style={styles.currentBalRow}>
                <Text style={styles.currentBalLabel}>Current Balance:</Text>
                <Text style={styles.currentBalVal}>
                  {(wallet?.balance ?? user?.wallet_balance ?? 0)} Credits
                </Text>
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalFieldLabel}>Adjustment Amount</Text>
                <TextInput
                  style={styles.modalInput}
                  placeholder="E.g. 50 (add) or -20 (deduct)"
                  placeholderTextColor="#6B7280"
                  keyboardType="numeric"
                  value={creditAmount}
                  onChangeText={(val) => {
                    setCreditAmount(val);
                    setAdjustError(null);
                  }}
                />
              </View>

              {creditAmount && !isNaN(parseFloat(creditAmount)) ? (
                <View style={styles.previewBalBox}>
                  <Text style={styles.previewBalLabel}>New Balance:</Text>
                  <Text style={styles.previewBalVal}>
                    {Math.max(
                      0,
                      (wallet?.balance ?? user?.wallet_balance ?? 0) + parseFloat(creditAmount)
                    )}{" "}
                    Credits
                  </Text>
                </View>
              ) : null}

              <View style={styles.modalField}>
                <Text style={styles.modalFieldLabel}>Reason for Adjustment (Mandatory Audit Note)</Text>
                <TextInput
                  style={[styles.modalInput, { height: 70, textAlignVertical: "top" }]}
                  placeholder="E.g. Bar association promotional credit / Case filing credit"
                  placeholderTextColor="#6B7280"
                  multiline
                  value={creditReason}
                  onChangeText={(val) => {
                    setCreditReason(val);
                    setAdjustError(null);
                  }}
                />
              </View>
            </View>

            <View style={styles.modalFooter}>
              <Pressable
                onPress={() => setAdjustModalVisible(false)}
                style={styles.modalCancelBtn}
                disabled={adjustSubmitting}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </Pressable>
              <Pressable
                onPress={handleAdjustWallet}
                style={[styles.modalConfirmBtn, adjustSubmitting && { opacity: 0.7 }]}
                disabled={adjustSubmitting}
              >
                {adjustSubmitting ? (
                  <ActivityIndicator size="small" color="#061024" style={{ marginRight: 6 }} />
                ) : null}
                <Text style={styles.modalConfirmText}>
                  {adjustSubmitting ? "Updating..." : "Commit Credit Adjustment"}
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
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#162544",
    flexWrap: "wrap",
    gap: 12,
  },
  cardHeaderLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FDFDFD",
  },
  statusGroup: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  profileGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    padding: 20,
    gap: 20,
  },
  profileField: {
    width: "30%",
    minWidth: 200,
    gap: 4,
  },
  fieldLabel: {
    fontSize: 12,
    color: "#8B96A9",
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.4,
  },
  fieldValue: {
    fontSize: 14,
    color: "#FDFDFD",
    fontWeight: "600",
  },
  cardActions: {
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderTopWidth: 1,
    borderTopColor: "#162544",
    backgroundColor: "#08142D",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: 12,
  },
  actionSectionTitle: {
    fontSize: 13,
    fontWeight: "600",
    color: "#8B96A9",
  },
  actionButtons: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  btnAction: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 8,
    borderWidth: 1,
    gap: 6,
  },
  btnActionText: {
    fontSize: 12,
    fontWeight: "700",
  },
  btnSmGold: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#C5A059",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    gap: 4,
  },
  btnSmGoldText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#061024",
  },
  cellText: {
    fontSize: 12,
    color: "#D1D8E5",
  },
  cellDate: {
    fontSize: 12,
    color: "#8B96A9",
  },
  cellMutedSm: {
    fontSize: 10,
    color: "#8B96A9",
    marginTop: 2,
  },
  ledgerAmt: {
    fontSize: 13,
    fontWeight: "700",
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
    gap: 12,
  },
  modalHeaderIcon: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: "rgba(197, 160, 89, 0.15)",
    alignItems: "center",
    justifyContent: "center",
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
  modalErrorBox: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(229, 62, 62, 0.12)",
    borderWidth: 1,
    borderColor: "rgba(229, 62, 62, 0.3)",
    padding: 10,
    borderRadius: 8,
  },
  modalErrorText: {
    fontSize: 12,
    color: "#F56565",
    flex: 1,
  },
  currentBalRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#0D182E",
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#1B2A49",
  },
  currentBalLabel: {
    fontSize: 13,
    color: "#8B96A9",
  },
  currentBalVal: {
    fontSize: 15,
    fontWeight: "700",
    color: "#C5A059",
  },
  modalField: {
    gap: 6,
  },
  modalFieldLabel: {
    fontSize: 12,
    fontWeight: "600",
    color: "#D1D8E5",
  },
  modalInput: {
    backgroundColor: "#0B182E",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#253452",
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: "#FDFDFD",
    fontSize: 13,
  },
  previewBalBox: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "rgba(72, 187, 120, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(72, 187, 120, 0.3)",
    padding: 10,
    borderRadius: 8,
  },
  previewBalLabel: {
    fontSize: 12,
    color: "#48BB78",
    fontWeight: "600",
  },
  previewBalVal: {
    fontSize: 14,
    fontWeight: "800",
    color: "#48BB78",
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
  modalConfirmBtn: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#C5A059",
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 8,
  },
  modalConfirmText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#061024",
  },
});

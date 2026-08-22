import React, { useEffect, useState, useCallback } from "react";
import {
  StyleSheet,
  Text,
  View,
  Pressable,
  TextInput,
  Modal,
  ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { AdminLayout } from "@/src/components/admin/AdminLayout";
import { AdminDataTable, ColumnDef } from "@/src/components/admin/AdminDataTable";
import { AdminFilterBar, FilterField } from "@/src/components/admin/AdminFilterBar";
import { AdminPagination } from "@/src/components/admin/AdminPagination";
import { StatusBadge } from "@/src/components/admin/StatusBadge";
import { ConfirmDialog } from "@/src/components/admin/ConfirmDialog";
import { adminApi } from "@/src/api/adminClient";
import type { LawyerUser, PaginatedResult } from "@/src/types/admin";

export default function AdminUsersListScreen() {
  const [data, setData] = useState<PaginatedResult<LawyerUser> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination State
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [stateFilter, setStateFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Selection & Bulk Actions
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [bulkActionType, setBulkActionType] = useState<"suspend" | "activate" | "ban" | null>(null);
  const [bulkReason, setBulkReason] = useState("");
  const [bulkSubmitting, setBulkSubmitting] = useState(false);

  // Single Action Modal State
  const [actionUser, setActionUser] = useState<LawyerUser | null>(null);
  const [actionType, setActionType] = useState<"suspend" | "activate" | "ban" | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Wallet Credit Adjustment Modal State
  const [walletUser, setWalletUser] = useState<LawyerUser | null>(null);
  const [creditAmount, setCreditAmount] = useState("");
  const [creditReason, setCreditReason] = useState("");
  const [walletSubmitting, setWalletSubmitting] = useState(false);
  const [walletError, setWalletError] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.listUsers({
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
        state: stateFilter !== "all" ? stateFilter : undefined,
      });
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load advocates listing.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, statusFilter, stateFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Handle Single Status Action
  const handleConfirmSingleAction = async () => {
    if (!actionUser || !actionType) return;
    setActionLoading(true);
    try {
      if (actionType === "suspend") {
        await adminApi.suspendUser(actionUser.id);
      } else if (actionType === "activate") {
        await adminApi.activateUser(actionUser.id);
      } else if (actionType === "ban") {
        await adminApi.banUser(actionUser.id);
      }
      setActionUser(null);
      setActionType(null);
      await fetchUsers();
    } catch (err: any) {
      alert(err?.message || "Failed to update advocate status.");
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Bulk Status Action
  const handleConfirmBulkAction = async () => {
    if (!bulkActionType || selectedIds.length === 0) return;
    setBulkSubmitting(true);
    try {
      await adminApi.bulkUserStatus({
        user_ids: selectedIds,
        action: bulkActionType,
        reason: bulkReason || `Bulk ${bulkActionType} by Super Admin`,
      });
      setSelectedIds([]);
      setBulkActionType(null);
      setBulkReason("");
      await fetchUsers();
    } catch (err: any) {
      alert(err?.message || "Failed to execute bulk status mutation.");
    } finally {
      setBulkSubmitting(false);
    }
  };

  // Handle Wallet Adjustment
  const handleAdjustWallet = async () => {
    if (!walletUser) return;
    const amt = parseFloat(creditAmount);
    if (isNaN(amt) || amt === 0) {
      setWalletError("Please enter a valid non-zero credit amount (e.g. 50 or -20).");
      return;
    }
    if (!creditReason.trim()) {
      setWalletError("Reason for credit adjustment is mandatory for audit trail.");
      return;
    }

    setWalletSubmitting(true);
    setWalletError(null);
    try {
      await adminApi.adjustUserWallet(walletUser.id, {
        amount: amt,
        reason: creditReason.trim(),
      });
      setWalletUser(null);
      setCreditAmount("");
      setCreditReason("");
      await fetchUsers();
    } catch (err: any) {
      setWalletError(err?.message || "Failed to adjust user wallet.");
    } finally {
      setWalletSubmitting(false);
    }
  };

  const filterFields: FilterField[] = [
    {
      key: "status",
      label: "Status",
      value: statusFilter,
      options: [
        { label: "Active", value: "active" },
        { label: "Suspended", value: "suspended" },
        { label: "Banned", value: "banned" },
      ],
      onChange: (val) => {
        setStatusFilter(val);
        setPage(1);
      },
    },
    {
      key: "state",
      label: "State",
      value: stateFilter,
      options: [
        { label: "Gujarat", value: "Gujarat" },
        { label: "Maharashtra", value: "Maharashtra" },
        { label: "Delhi", value: "Delhi" },
        { label: "Rajasthan", value: "Rajasthan" },
      ],
      onChange: (val) => {
        setStateFilter(val);
        setPage(1);
      },
    },
  ];

  const columns: ColumnDef<LawyerUser>[] = [
    {
      key: "name",
      header: "Advocate Details",
      flex: 1.8,
      render: (u) => (
        <View>
          <Text style={styles.cellTitle}>
            {u.name || u.advocate_name_en || `Advocate ${u.mobile || "User"}`}
          </Text>
          <Text style={styles.cellSub}>
            {u.email ? u.email : `Phone: +91 ${u.mobile || "—"}`}
          </Text>
        </View>
      ),
    },
    {
      key: "bar_council_no",
      header: "Bar Council No",
      width: 140,
      render: (u) => (
        <Text style={styles.cellText}>{u.bar_council_no || "Unregistered"}</Text>
      ),
    },
    {
      key: "district",
      header: "District / Court",
      width: 150,
      render: (u) => (
        <View>
          <Text style={styles.cellText}>{u.district || "Gujarat"}</Text>
          <Text style={styles.cellMutedSm}>{u.court || "District Court"}</Text>
        </View>
      ),
    },
    {
      key: "status",
      header: "Status",
      width: 110,
      render: (u) => <StatusBadge status={u.status || (u.active ? "active" : "suspended")} size="sm" />,
    },
    {
      key: "wallet_balance",
      header: "Credits Balance",
      width: 130,
      render: (u) => {
        const bal = u.wallet?.balance ?? u.wallet_balance ?? 0;
        return (
          <View style={styles.balanceBadge}>
            <Ionicons name="diamond" size={12} color="#C5A059" style={{ marginRight: 4 }} />
            <Text style={styles.balanceText}>{bal} Cr</Text>
          </View>
        );
      },
    },
    {
      key: "created_at",
      header: "Joined",
      width: 110,
      render: (u) => (
        <Text style={styles.cellDate}>
          {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
        </Text>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      width: 220,
      align: "right",
      render: (u) => {
        const isActive = u.status === "active" || (u.active && u.status !== "banned" && u.status !== "suspended");
        const isSuspended = u.status === "suspended";
        const isBanned = u.status === "banned";

        return (
          <View style={styles.actionRow}>
            {/* View Detail */}
            <Pressable
              onPress={() => router.push(`/admin/users/${u.id}` as any)}
              style={styles.actionIconBtn}
              accessibilityLabel="View advocate detail"
            >
              <Ionicons name="eye-outline" size={16} color="#8B96A9" />
            </Pressable>

            {/* Adjust Credits */}
            <Pressable
              onPress={() => {
                setWalletUser(u);
                setCreditAmount("");
                setCreditReason("");
                setWalletError(null);
              }}
              style={[styles.actionIconBtn, { backgroundColor: "rgba(197, 160, 89, 0.15)" }]}
              accessibilityLabel="Adjust Credits"
            >
              <Ionicons name="diamond-outline" size={16} color="#C5A059" />
            </Pressable>

            {/* Activate / Suspend */}
            {isActive && (
              <Pressable
                onPress={() => {
                  setActionUser(u);
                  setActionType("suspend");
                }}
                style={[styles.actionIconBtn, { backgroundColor: "rgba(236, 201, 75, 0.15)" }]}
                accessibilityLabel="Suspend advocate"
              >
                <Ionicons name="pause-outline" size={16} color="#ECC94B" />
              </Pressable>
            )}

            {(isSuspended || isBanned) && (
              <Pressable
                onPress={() => {
                  setActionUser(u);
                  setActionType("activate");
                }}
                style={[styles.actionIconBtn, { backgroundColor: "rgba(72, 187, 120, 0.15)" }]}
                accessibilityLabel="Activate advocate"
              >
                <Ionicons name="play-outline" size={16} color="#48BB78" />
              </Pressable>
            )}

            {!isBanned && (
              <Pressable
                onPress={() => {
                  setActionUser(u);
                  setActionType("ban");
                }}
                style={[styles.actionIconBtn, { backgroundColor: "rgba(229, 62, 62, 0.15)" }]}
                accessibilityLabel="Ban advocate"
              >
                <Ionicons name="ban-outline" size={16} color="#E53E3E" />
              </Pressable>
            )}
          </View>
        );
      },
    },
  ];

  return (
    <AdminLayout
      title="Advocate Users & Wallets"
      subtitle="Manage registered lawyers, status governance, Bar Council verification and credit ledgers"
    >
      <View style={styles.container}>
        {/* Filter Bar */}
        <AdminFilterBar
          search={search}
          onSearchChange={(val) => {
            setSearch(val);
            setPage(1);
          }}
          searchPlaceholder="Search by advocate name, phone, email, Bar No..."
          filters={filterFields}
          onReset={() => {
            setSearch("");
            setStatusFilter("all");
            setStateFilter("all");
            setPage(1);
          }}
          totalCount={data?.total}
        />

        {/* Data Table */}
        <AdminDataTable
          columns={columns}
          data={data?.items || []}
          keyExtractor={(u) => u.id}
          loading={loading}
          error={error}
          onRetry={fetchUsers}
          selectable={true}
          selectedKeys={selectedIds}
          onSelectionChange={setSelectedIds}
          emptyTitle="No advocates found"
          emptyDescription="No registered advocates match the selected filters."
          onRowPress={(u) => router.push(`/admin/users/${u.id}` as any)}
          bulkActions={
            <View style={styles.bulkRow}>
              <Pressable
                onPress={() => setBulkActionType("activate")}
                style={[styles.bulkBtn, { backgroundColor: "#2D5A27" }]}
              >
                <Ionicons name="checkmark-circle-outline" size={14} color="#FFF" />
                <Text style={styles.bulkBtnText}>Activate</Text>
              </Pressable>
              <Pressable
                onPress={() => setBulkActionType("suspend")}
                style={[styles.bulkBtn, { backgroundColor: "#744210" }]}
              >
                <Ionicons name="pause-circle-outline" size={14} color="#FFF" />
                <Text style={styles.bulkBtnText}>Suspend</Text>
              </Pressable>
              <Pressable
                onPress={() => setBulkActionType("ban")}
                style={[styles.bulkBtn, { backgroundColor: "#742A2A" }]}
              >
                <Ionicons name="ban-outline" size={14} color="#FFF" />
                <Text style={styles.bulkBtnText}>Ban</Text>
              </Pressable>
            </View>
          }
        />

        {/* Server-Side Pagination */}
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

      {/* Single Action Confirmation Dialog */}
      <ConfirmDialog
        visible={!!actionUser && !!actionType}
        title={
          actionType === "suspend"
            ? "Suspend Advocate Account"
            : actionType === "ban"
            ? "Permanently Ban Advocate Account"
            : "Activate Advocate Account"
        }
        message={
          actionType === "suspend"
            ? `Are you sure you want to suspend account for advocate ${actionUser?.name || actionUser?.mobile}? The user will be temporarily prevented from generating documents.`
            : actionType === "ban"
            ? `Are you sure you want to BAN account for advocate ${actionUser?.name || actionUser?.mobile}? This is a strict administrative enforcement.`
            : `Are you sure you want to reactivate account for advocate ${actionUser?.name || actionUser?.mobile}?`
        }
        impactWarning={
          actionType === "ban"
            ? "Banning revokes all active authentication tokens and logs the security enforcement event."
            : undefined
        }
        confirmVariant={actionType === "ban" ? "danger" : actionType === "suspend" ? "warning" : "primary"}
        confirmLabel={
          actionType === "suspend" ? "Suspend Account" : actionType === "ban" ? "Ban Account" : "Activate Account"
        }
        loading={actionLoading}
        onConfirm={handleConfirmSingleAction}
        onCancel={() => {
          setActionUser(null);
          setActionType(null);
        }}
      />

      {/* Bulk Action Confirmation Dialog */}
      <ConfirmDialog
        visible={!!bulkActionType && selectedIds.length > 0}
        title={`Bulk ${bulkActionType?.toUpperCase()} (${selectedIds.length} Accounts)`}
        message={`You are about to apply '${bulkActionType}' to ${selectedIds.length} advocate accounts.`}
        impactWarning="All selected users will immediately receive the updated status in their access tokens."
        confirmVariant={bulkActionType === "ban" ? "danger" : "warning"}
        confirmLabel={`Apply ${bulkActionType?.toUpperCase()} to ${selectedIds.length} users`}
        loading={bulkSubmitting}
        onConfirm={handleConfirmBulkAction}
        onCancel={() => setBulkActionType(null)}
      >
        <View style={{ marginTop: 12 }}>
          <Text style={styles.dialogInputLabel}>Mandatory Administrative Reason:</Text>
          <TextInput
            style={styles.dialogTextInput}
            placeholder="E.g. Bar Council verification audit / Compliance review"
            placeholderTextColor="#6B7280"
            value={bulkReason}
            onChangeText={setBulkReason}
          />
        </View>
      </ConfirmDialog>

      {/* Wallet Credit Adjustment Modal */}
      <Modal
        visible={!!walletUser}
        transparent
        animationType="fade"
        onRequestClose={() => setWalletUser(null)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <View style={styles.modalHeaderIcon}>
                <Ionicons name="diamond" size={20} color="#C5A059" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.modalTitle}>Adjust Advocate Credits</Text>
                <Text style={styles.modalSub}>
                  {walletUser?.name || `Advocate ${walletUser?.mobile || ""}`}
                </Text>
              </View>
              <Pressable onPress={() => setWalletUser(null)} style={{ padding: 4 }}>
                <Ionicons name="close" size={20} color="#8B96A9" />
              </Pressable>
            </View>

            <View style={styles.modalBody}>
              {walletError ? (
                <View style={styles.modalErrorBox}>
                  <Ionicons name="alert-circle" size={16} color="#E53E3E" style={{ marginRight: 6 }} />
                  <Text style={styles.modalErrorText}>{walletError}</Text>
                </View>
              ) : null}

              <View style={styles.currentBalRow}>
                <Text style={styles.currentBalLabel}>Current Balance:</Text>
                <Text style={styles.currentBalVal}>
                  {(walletUser?.wallet?.balance ?? walletUser?.wallet_balance ?? 0)} Credits
                </Text>
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalFieldLabel}>Credit Adjustment Amount</Text>
                <TextInput
                  style={styles.modalInput}
                  placeholder="Enter positive (e.g. 50) or negative (e.g. -20)"
                  placeholderTextColor="#6B7280"
                  keyboardType="numeric"
                  value={creditAmount}
                  onChangeText={(val) => {
                    setCreditAmount(val);
                    setWalletError(null);
                  }}
                />
                <Text style={styles.fieldHint}>
                  Positive value adds credits. Negative value deducts credits.
                </Text>
              </View>

              {/* Calculated New Balance */}
              {creditAmount && !isNaN(parseFloat(creditAmount)) ? (
                <View style={styles.previewBalBox}>
                  <Text style={styles.previewBalLabel}>Projected New Balance:</Text>
                  <Text style={styles.previewBalVal}>
                    {Math.max(
                      0,
                      (walletUser?.wallet?.balance ?? walletUser?.wallet_balance ?? 0) +
                        parseFloat(creditAmount)
                    )}{" "}
                    Credits
                  </Text>
                </View>
              ) : null}

              <View style={styles.modalField}>
                <Text style={styles.modalFieldLabel}>Reason for Adjustment (Mandatory Audit Note)</Text>
                <TextInput
                  style={[styles.modalInput, { height: 70, textAlignVertical: "top" }]}
                  placeholder="E.g. Bar association promotional grant / Dispute resolution refund"
                  placeholderTextColor="#6B7280"
                  multiline
                  value={creditReason}
                  onChangeText={(val) => {
                    setCreditReason(val);
                    setWalletError(null);
                  }}
                />
              </View>
            </View>

            <View style={styles.modalFooter}>
              <Pressable
                onPress={() => setWalletUser(null)}
                style={styles.modalCancelBtn}
                disabled={walletSubmitting}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </Pressable>
              <Pressable
                onPress={handleAdjustWallet}
                style={[styles.modalConfirmBtn, walletSubmitting && { opacity: 0.7 }]}
                disabled={walletSubmitting}
              >
                {walletSubmitting ? (
                  <ActivityIndicator size="small" color="#061024" style={{ marginRight: 6 }} />
                ) : null}
                <Text style={styles.modalConfirmText}>
                  {walletSubmitting ? "Updating..." : "Confirm Ledger Adjustment"}
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
  balanceBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(197, 160, 89, 0.12)",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "rgba(197, 160, 89, 0.3)",
    alignSelf: "flex-start",
  },
  balanceText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#C5A059",
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
  bulkRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  bulkBtn: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
    gap: 4,
  },
  bulkBtnText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#FFF",
  },
  dialogInputLabel: {
    fontSize: 12,
    color: "#D1D8E5",
    fontWeight: "600",
    marginBottom: 6,
  },
  dialogTextInput: {
    backgroundColor: "#0B182E",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#253452",
    paddingHorizontal: 12,
    paddingVertical: 8,
    color: "#FDFDFD",
    fontSize: 13,
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
  fieldHint: {
    fontSize: 11,
    color: "#6B7280",
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

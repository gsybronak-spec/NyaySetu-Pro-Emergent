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
import { StatusBadge } from "@/src/components/admin/StatusBadge";
import { ConfirmDialog } from "@/src/components/admin/ConfirmDialog";
import { adminApi } from "@/src/api/adminClient";
import type { CatalogItem, CatalogKind } from "@/src/types/admin";

interface CatalogTabDef {
  kind: CatalogKind;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  description: string;
}

const CATALOG_TABS: CatalogTabDef[] = [
  { kind: "courts", label: "Courts", icon: "business-outline", description: "Gujarat High Court, City Civil, District & Taluka Courts" },
  { kind: "districts", label: "Districts", icon: "map-outline", description: "Gujarat Revenue & Judicial Districts" },
  { kind: "talukas", label: "Talukas", icon: "location-outline", description: "Sub-district judicial talukas and tehsil divisions" },
  { kind: "laws", label: "Acts & Laws", icon: "book-outline", description: "BNS, BNSS, BSA, CPC, CrPC, IPC statutory references" },
  { kind: "police-stations", label: "Police Stations", icon: "shield-outline", description: "Jurisdictional police stations and stations registry" },
  { kind: "case-types", label: "Case Types", icon: "folder-open-outline", description: "Civil Suits, Bail Applications, Petitions, Criminal Appeals" },
];

export default function AdminCatalogsScreen() {
  const [activeTab, setActiveTab] = useState<CatalogKind>("courts");
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  // Create / Edit Modal
  const [modalVisible, setModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState<CatalogItem | null>(null);
  const [formId, setFormId] = useState("");
  const [formNameEn, setFormNameEn] = useState("");
  const [formNameGu, setFormNameGu] = useState("");
  const [formDistrictId, setFormDistrictId] = useState("");
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Status Toggle / Delete Dialog
  const [targetItem, setTargetItem] = useState<CatalogItem | null>(null);
  const [actionType, setActionType] = useState<"toggle" | "delete" | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchCatalog = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.listCatalog(activeTab, search.trim() || undefined);
      setItems(Array.isArray(res) ? res : []);
    } catch (err: any) {
      setError(err?.message || `Failed to fetch ${activeTab} catalog.`);
    } finally {
      setLoading(false);
    }
  }, [activeTab, search]);

  useEffect(() => {
    fetchCatalog();
  }, [fetchCatalog]);

  const openCreateModal = () => {
    setEditingItem(null);
    setFormId("");
    setFormNameEn("");
    setFormNameGu("");
    setFormDistrictId("");
    setFormError(null);
    setModalVisible(true);
  };

  const openEditModal = (item: CatalogItem) => {
    setEditingItem(item);
    setFormId(item.id);
    setFormNameEn(item.name_en || item.en || item.name || "");
    setFormNameGu(item.name_gu || item.gu || "");
    setFormDistrictId(item.district_id || "");
    setFormError(null);
    setModalVisible(true);
  };

  const handleSaveItem = async () => {
    if (!formNameEn.trim() && !formNameGu.trim()) {
      setFormError("Item name is required in English or Gujarati.");
      return;
    }

    setFormSubmitting(true);
    setFormError(null);
    try {
      const payload: any = {
        name_en: formNameEn.trim() || formNameGu.trim(),
        name_gu: formNameGu.trim() || formNameEn.trim(),
        district_id: formDistrictId.trim() || undefined,
        active: true,
      };

      if (editingItem) {
        await adminApi.updateCatalogItem(activeTab, editingItem.id, payload);
      } else {
        if (formId.trim()) payload.id = formId.trim();
        await adminApi.createCatalogItem(activeTab, payload);
      }

      setModalVisible(false);
      await fetchCatalog();
    } catch (err: any) {
      setFormError(err?.message || "Failed to save catalog entry.");
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleExecuteAction = async () => {
    if (!targetItem || !actionType) return;
    setActionLoading(true);
    try {
      if (actionType === "toggle") {
        const nextActive = targetItem.active === false ? true : false;
        await adminApi.setCatalogItemStatus(activeTab, targetItem.id, nextActive);
      } else {
        await adminApi.deleteCatalogItem(activeTab, targetItem.id);
      }
      setTargetItem(null);
      setActionType(null);
      await fetchCatalog();
    } catch (err: any) {
      alert(err?.message || "Operation failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const currentTabDef = CATALOG_TABS.find((t) => t.kind === activeTab) || CATALOG_TABS[0];

  const columns: ColumnDef<CatalogItem>[] = [
    {
      key: "name_gu",
      header: "Gujarati Name",
      flex: 1.8,
      render: (item) => (
        <View>
          <Text style={[styles.cellTitle, { fontFamily: "serif" }]}>
            {item.name_gu || item.gu || item.name || "—"}
          </Text>
          <Text style={styles.cellSub}>ID: {item.id}</Text>
        </View>
      ),
    },
    {
      key: "name_en",
      header: "English Name",
      flex: 1.8,
      render: (item) => (
        <Text style={styles.cellText}>{item.name_en || item.en || item.name || "—"}</Text>
      ),
    },
    {
      key: "district_id",
      header: "District Association",
      width: 170,
      render: (item) => (
        <Text style={styles.cellMuted}>{item.district_id || "State-wide / All"}</Text>
      ),
    },
    {
      key: "active",
      header: "Status",
      width: 100,
      render: (item) => (
        <StatusBadge
          status={item.active !== false ? "active" : "disabled"}
          label={item.active !== false ? "ACTIVE" : "INACTIVE"}
          size="sm"
        />
      ),
    },
    {
      key: "actions",
      header: "Actions",
      width: 120,
      align: "right",
      render: (item) => {
        const isActive = item.active !== false;
        return (
          <View style={styles.actionRow}>
            {/* Edit */}
            <Pressable
              onPress={() => openEditModal(item)}
              style={styles.actionIconBtn}
              accessibilityLabel="Edit Item"
            >
              <Ionicons name="create-outline" size={15} color="#C5A059" />
            </Pressable>

            {/* Toggle Status */}
            <Pressable
              onPress={() => {
                setTargetItem(item);
                setActionType("toggle");
              }}
              style={[
                styles.actionIconBtn,
                { backgroundColor: isActive ? "rgba(236, 201, 75, 0.15)" : "rgba(72, 187, 120, 0.15)" },
              ]}
              accessibilityLabel={isActive ? "Deactivate Item" : "Activate Item"}
            >
              <Ionicons
                name={isActive ? "pause-outline" : "play-outline"}
                size={15}
                color={isActive ? "#ECC94B" : "#48BB78"}
              />
            </Pressable>

            {/* Delete */}
            <Pressable
              onPress={() => {
                setTargetItem(item);
                setActionType("delete");
              }}
              style={[styles.actionIconBtn, { backgroundColor: "rgba(229, 62, 62, 0.15)" }]}
              accessibilityLabel="Delete Item"
            >
              <Ionicons name="trash-outline" size={15} color="#E53E3E" />
            </Pressable>
          </View>
        );
      },
    },
  ];

  return (
    <AdminLayout
      title="Master Lookup Catalogs"
      subtitle="Administrative configuration for courts, districts, talukas, statutory acts, and case types"
      actions={
        <Pressable onPress={openCreateModal} style={styles.createBtn}>
          <Ionicons name="add" size={16} color="#061024" />
          <Text style={styles.createBtnText}>Add to {currentTabDef.label}</Text>
        </Pressable>
      }
    >
      <View style={styles.container}>
        {/* Catalog Navigation Tabs */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabsRail}>
          <View style={styles.tabsRow}>
            {CATALOG_TABS.map((tab) => {
              const active = activeTab === tab.kind;
              return (
                <Pressable
                  key={tab.kind}
                  onPress={() => {
                    setActiveTab(tab.kind);
                    setSearch("");
                  }}
                  style={[styles.tabChip, active && styles.tabChipActive]}
                >
                  <Ionicons
                    name={tab.icon}
                    size={16}
                    color={active ? "#C5A059" : "#8B96A9"}
                    style={{ marginRight: 8 }}
                  />
                  <Text style={[styles.tabChipText, active && styles.tabChipTextActive]}>
                    {tab.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </ScrollView>

        {/* Tab Description Banner */}
        <View style={styles.descBanner}>
          <Ionicons name={currentTabDef.icon} size={20} color="#C5A059" style={{ marginRight: 10 }} />
          <View style={{ flex: 1 }}>
            <Text style={styles.descBannerTitle}>{currentTabDef.label} Catalog</Text>
            <Text style={styles.descBannerSub}>{currentTabDef.description}</Text>
          </View>
          <View style={styles.searchBox}>
            <Ionicons name="search" size={15} color="#8B96A9" style={{ marginRight: 6 }} />
            <TextInput
              style={styles.searchInput}
              placeholder={`Search ${currentTabDef.label}...`}
              placeholderTextColor="#6B7280"
              value={search}
              onChangeText={setSearch}
            />
            {search ? (
              <Pressable onPress={() => setSearch("")} style={{ padding: 2 }}>
                <Ionicons name="close-circle" size={14} color="#8B96A9" />
              </Pressable>
            ) : null}
          </View>
        </View>

        {/* Data Table */}
        <AdminDataTable
          columns={columns}
          data={items}
          keyExtractor={(item) => item.id}
          loading={loading}
          error={error}
          onRetry={fetchCatalog}
          emptyTitle={`No items in ${currentTabDef.label}`}
          emptyDescription={`Add your first entry or adjust your search filter.`}
        />
      </View>

      {/* Confirmation Dialog */}
      <ConfirmDialog
        visible={!!targetItem && !!actionType}
        title={
          actionType === "toggle"
            ? `${targetItem?.active !== false ? "Deactivate" : "Activate"} Catalog Item`
            : "Delete Catalog Item"
        }
        message={
          actionType === "toggle"
            ? `Are you sure you want to change status of "${targetItem?.name_en || targetItem?.name_gu || targetItem?.id}"?`
            : `Are you sure you want to delete "${targetItem?.name_en || targetItem?.name_gu || targetItem?.id}" from ${currentTabDef.label}?`
        }
        impactWarning={
          actionType === "delete"
            ? "Existing case documents already referencing this item will maintain their saved text values."
            : undefined
        }
        confirmVariant={actionType === "delete" ? "danger" : "warning"}
        confirmLabel={actionType === "delete" ? "Delete Item" : "Update Status"}
        loading={actionLoading}
        onConfirm={handleExecuteAction}
        onCancel={() => {
          setTargetItem(null);
          setActionType(null);
        }}
      />

      {/* Add / Edit Item Modal */}
      <Modal
        visible={modalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <Ionicons name={editingItem ? "create" : "add-circle"} size={20} color="#C5A059" />
              <View style={{ flex: 1, marginLeft: 8 }}>
                <Text style={styles.modalTitle}>
                  {editingItem ? `Edit ${currentTabDef.label}` : `Add New ${currentTabDef.label}`}
                </Text>
                <Text style={styles.modalSub}>
                  Configure multilingual naming and jurisdiction tags
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

              {!editingItem && (
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>Custom Slug / ID (Optional)</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="E.g. ahm-city-civil or leave blank for auto ID"
                    placeholderTextColor="#6B7280"
                    value={formId}
                    onChangeText={setFormId}
                  />
                </View>
              )}

              <View style={styles.field}>
                <Text style={styles.fieldLabel}>Gujarati Name (ગુજરાતી નામ) *</Text>
                <TextInput
                  style={[styles.input, { fontFamily: "serif" }]}
                  placeholder="દા.ત. સિટી સિવિલ કોર્ટ, અમદાવાદ"
                  placeholderTextColor="#6B7280"
                  value={formNameGu}
                  onChangeText={setFormNameGu}
                />
              </View>

              <View style={styles.field}>
                <Text style={styles.fieldLabel}>English Name *</Text>
                <TextInput
                  style={styles.input}
                  placeholder="E.g. City Civil Court, Ahmedabad"
                  placeholderTextColor="#6B7280"
                  value={formNameEn}
                  onChangeText={setFormNameEn}
                />
              </View>

              {(activeTab === "courts" || activeTab === "talukas" || activeTab === "police-stations") && (
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>District ID Association</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="E.g. ahmedabad / surat / rajkot"
                    placeholderTextColor="#6B7280"
                    value={formDistrictId}
                    onChangeText={setFormDistrictId}
                  />
                </View>
              )}
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
                onPress={handleSaveItem}
                style={[styles.createBtn, formSubmitting && { opacity: 0.7 }]}
                disabled={formSubmitting}
              >
                {formSubmitting ? (
                  <ActivityIndicator size="small" color="#061024" style={{ marginRight: 6 }} />
                ) : null}
                <Text style={styles.createBtnText}>
                  {formSubmitting ? "Saving..." : editingItem ? "Update Entry" : "Add Entry"}
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
  tabsRail: {
    flexGrow: 0,
  },
  tabsRow: {
    flexDirection: "row",
    gap: 8,
    paddingBottom: 4,
  },
  tabChip: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#12203B",
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#253452",
  },
  tabChipActive: {
    backgroundColor: "rgba(197, 160, 89, 0.15)",
    borderColor: "#C5A059",
  },
  tabChipText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#8B96A9",
  },
  tabChipTextActive: {
    color: "#C5A059",
    fontWeight: "700",
  },
  descBanner: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#0B1B3D",
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#1B2A49",
    flexWrap: "wrap",
    gap: 12,
  },
  descBannerTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: "#FDFDFD",
  },
  descBannerSub: {
    fontSize: 12,
    color: "#8B96A9",
    marginTop: 2,
  },
  searchBox: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#12203B",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#253452",
    paddingHorizontal: 10,
    height: 36,
    minWidth: 220,
  },
  searchInput: {
    flex: 1,
    color: "#FDFDFD",
    fontSize: 12,
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
  cellMuted: {
    fontSize: 12,
    color: "#8B96A9",
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

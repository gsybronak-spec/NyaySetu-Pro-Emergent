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
import { router } from "expo-router";
import { AdminLayout } from "@/src/components/admin/AdminLayout";
import { AdminDataTable, ColumnDef } from "@/src/components/admin/AdminDataTable";
import { AdminFilterBar, FilterField } from "@/src/components/admin/AdminFilterBar";
import { StatusBadge } from "@/src/components/admin/StatusBadge";
import { ConfirmDialog } from "@/src/components/admin/ConfirmDialog";
import { adminApi } from "@/src/api/adminClient";
import type { AdminTemplateItem, PaginatedResult } from "@/src/types/admin";

export default function AdminTemplatesListScreen() {
  const [data, setData] = useState<PaginatedResult<AdminTemplateItem> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  // Modal / Action States
  const [previewTemplate, setPreviewTemplate] = useState<AdminTemplateItem | null>(null);
  const [previewTab, setPreviewTab] = useState<"gu" | "en">("gu");

  const [targetTemplate, setTargetTemplate] = useState<AdminTemplateItem | null>(null);
  const [actionType, setActionType] = useState<
    "publish" | "unpublish" | "archive" | "restore" | "duplicate" | "delete" | null
  >(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Create / Edit Template Modal
  const [formVisible, setFormVisible] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formNameEn, setFormNameEn] = useState("");
  const [formNameGu, setFormNameGu] = useState("");
  const [formCategory, setFormCategory] = useState("Civil");
  const [formSubCategory, setFormSubCategory] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formContentGu, setFormContentGu] = useState("");
  const [formContentEn, setFormContentEn] = useState("");
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.listTemplates({
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
        category: categoryFilter !== "all" ? categoryFilter : undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
      });
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load legal templates catalog.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, categoryFilter, statusFilter]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const handleExecuteAction = async () => {
    if (!targetTemplate || !actionType) return;
    setActionLoading(true);
    try {
      if (actionType === "publish") {
        await adminApi.publishTemplate(targetTemplate.id);
      } else if (actionType === "unpublish") {
        await adminApi.unpublishTemplate(targetTemplate.id);
      } else if (actionType === "archive") {
        await adminApi.archiveTemplate(targetTemplate.id);
      } else if (actionType === "restore") {
        await adminApi.restoreTemplate(targetTemplate.id);
      } else if (actionType === "duplicate") {
        await adminApi.duplicateTemplate(targetTemplate.id, true);
      } else if (actionType === "delete") {
        await adminApi.deleteTemplatePermanent(targetTemplate.id);
      }
      setTargetTemplate(null);
      setActionType(null);
      await fetchTemplates();
    } catch (err: any) {
      alert(err?.message || "Failed to perform template operation.");
    } finally {
      setActionLoading(false);
    }
  };

  const openCreateModal = () => {
    setEditingId(null);
    setFormNameEn("");
    setFormNameGu("");
    setFormCategory("Civil");
    setFormSubCategory("");
    setFormDescription("");
    setFormContentGu("");
    setFormContentEn("");
    setFormError(null);
    setFormVisible(true);
  };

  const openEditModal = (t: AdminTemplateItem) => {
    setEditingId(t.id);
    setFormNameEn(t.name_en || "");
    setFormNameGu(t.name_gu || "");
    setFormCategory(t.category || "Civil");
    setFormSubCategory(t.sub_category || "");
    setFormDescription(t.description || "");
    setFormContentGu(t.content_gu || "");
    setFormContentEn(t.content_en || "");
    setFormError(null);
    setFormVisible(true);
  };

  const handleSaveTemplate = async () => {
    if (!formNameEn.trim() && !formNameGu.trim()) {
      setFormError("Please enter template title in English or Gujarati.");
      return;
    }

    setFormSubmitting(true);
    setFormError(null);
    try {
      const payload: Partial<AdminTemplateItem> = {
        name_en: formNameEn.trim() || formNameGu.trim(),
        name_gu: formNameGu.trim() || formNameEn.trim(),
        category: formCategory,
        sub_category: formSubCategory.trim() || undefined,
        description: formDescription.trim() || undefined,
        content_gu: formContentGu,
        content_en: formContentEn,
      };

      if (editingId) {
        await adminApi.updateTemplate(editingId, payload);
      } else {
        await adminApi.createTemplate(payload);
      }

      setFormVisible(false);
      await fetchTemplates();
    } catch (err: any) {
      setFormError(err?.message || "Failed to save template.");
    } finally {
      setFormSubmitting(false);
    }
  };

  const filterFields: FilterField[] = [
    {
      key: "category",
      label: "Category",
      value: categoryFilter,
      options: [
        { label: "Civil", value: "Civil" },
        { label: "Criminal", value: "Criminal" },
        { label: "Revenue", value: "Revenue" },
        { label: "Family", value: "Family" },
      ],
      onChange: (val) => {
        setCategoryFilter(val);
        setPage(1);
      },
    },
    {
      key: "status",
      label: "Status",
      value: statusFilter,
      options: [
        { label: "Published", value: "published" },
        { label: "Draft", value: "draft" },
        { label: "Archived", value: "archived" },
      ],
      onChange: (val) => {
        setStatusFilter(val);
        setPage(1);
      },
    },
  ];

  const columns: ColumnDef<AdminTemplateItem>[] = [
    {
      key: "name",
      header: "Template Title & Category",
      flex: 2,
      render: (t) => (
        <View>
          <Text style={styles.cellTitle}>{t.name_gu || t.name_en}</Text>
          <Text style={styles.cellSub}>
            {t.name_en ? `${t.name_en} • ` : ""}
            {t.category} {t.sub_category ? `(${t.sub_category})` : ""}
          </Text>
        </View>
      ),
    },
    {
      key: "version",
      header: "Version",
      width: 100,
      render: (t) => (
        <View style={styles.versionTag}>
          <Text style={styles.versionText}>v{t.version || 1}</Text>
        </View>
      ),
    },
    {
      key: "revision_count",
      header: "Revisions",
      width: 130,
      render: (t) => (
        <Pressable
          onPress={() => router.push(`/admin/templates/${t.id}/revisions` as any)}
          style={styles.revisionBadge}
        >
          <Ionicons name="time-outline" size={12} color="#C5A059" style={{ marginRight: 4 }} />
          <Text style={styles.revisionText}>{t.revision_count || 1} snapshots</Text>
        </Pressable>
      ),
    },
    {
      key: "status",
      header: "Status",
      width: 110,
      render: (t) => <StatusBadge status={t.status || "published"} size="sm" />,
    },
    {
      key: "source",
      header: "Source",
      width: 110,
      render: (t) => (
        <StatusBadge
          status={t.source === "seed" ? "seed" : "active"}
          label={(t.source || "seed").toUpperCase()}
          size="sm"
        />
      ),
    },
    {
      key: "actions",
      header: "Actions",
      width: 250,
      align: "right",
      render: (t) => {
        const isPublished = t.status === "published";
        const isArchived = t.status === "archived";

        return (
          <View style={styles.actionRow}>
            {/* Preview */}
            <Pressable
              onPress={() => {
                setPreviewTemplate(t);
                setPreviewTab("gu");
              }}
              style={styles.actionIconBtn}
              accessibilityLabel="Preview Template"
            >
              <Ionicons name="eye-outline" size={15} color="#8B96A9" />
            </Pressable>

            {/* Edit in Word-Like Editor */}
            <Pressable
              onPress={() => router.push(`/admin/templates/${t.id}/edit` as any)}
              style={styles.actionIconBtn}
              accessibilityLabel="Edit in Word-Like Editor"
            >
              <Ionicons name="create-outline" size={15} color="#C5A059" />
            </Pressable>

            {/* Revisions */}
            <Pressable
              onPress={() => router.push(`/admin/templates/${t.id}/revisions` as any)}
              style={styles.actionIconBtn}
              accessibilityLabel="View Revision History"
            >
              <Ionicons name="git-branch-outline" size={15} color="#4299E1" />
            </Pressable>

            {/* Publish / Unpublish */}
            {!isPublished ? (
              <Pressable
                onPress={() => {
                  setTargetTemplate(t);
                  setActionType("publish");
                }}
                style={[styles.actionIconBtn, { backgroundColor: "rgba(72, 187, 120, 0.15)" }]}
                accessibilityLabel="Publish Template"
              >
                <Ionicons name="cloud-upload-outline" size={15} color="#48BB78" />
              </Pressable>
            ) : (
              <Pressable
                onPress={() => {
                  setTargetTemplate(t);
                  setActionType("unpublish");
                }}
                style={[styles.actionIconBtn, { backgroundColor: "rgba(236, 201, 75, 0.15)" }]}
                accessibilityLabel="Unpublish to Draft"
              >
                <Ionicons name="pause-outline" size={15} color="#ECC94B" />
              </Pressable>
            )}

            {/* Duplicate */}
            <Pressable
              onPress={() => {
                setTargetTemplate(t);
                setActionType("duplicate");
              }}
              style={styles.actionIconBtn}
              accessibilityLabel="Duplicate as New Template"
            >
              <Ionicons name="copy-outline" size={15} color="#9F7AEA" />
            </Pressable>

            {/* Archive / Restore */}
            {isArchived ? (
              <Pressable
                onPress={() => {
                  setTargetTemplate(t);
                  setActionType("restore");
                }}
                style={[styles.actionIconBtn, { backgroundColor: "rgba(72, 187, 120, 0.15)" }]}
                accessibilityLabel="Restore Template"
              >
                <Ionicons name="refresh-outline" size={15} color="#48BB78" />
              </Pressable>
            ) : (
              <Pressable
                onPress={() => {
                  setTargetTemplate(t);
                  setActionType("archive");
                }}
                style={styles.actionIconBtn}
                accessibilityLabel="Archive Template"
              >
                <Ionicons name="archive-outline" size={15} color="#8B96A9" />
              </Pressable>
            )}

            {/* Delete Permanent */}
            <Pressable
              onPress={() => {
                setTargetTemplate(t);
                setActionType("delete");
              }}
              style={[styles.actionIconBtn, { backgroundColor: "rgba(229, 62, 62, 0.15)" }]}
              accessibilityLabel="Delete Template Permanently"
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
      title="Canonical Legal Templates Catalog"
      subtitle="Template schema governance, linear versioning, immutable revision snapshots and document shaper rules"
      actions={
        <Pressable onPress={openCreateModal} style={styles.createBtn}>
          <Ionicons name="add" size={16} color="#061024" />
          <Text style={styles.createBtnText}>New Template</Text>
        </Pressable>
      }
    >
      <View style={styles.container}>
        <AdminFilterBar
          search={search}
          onSearchChange={(val) => {
            setSearch(val);
            setPage(1);
          }}
          searchPlaceholder="Search template name in English or Gujarati..."
          filters={filterFields}
          onReset={() => {
            setSearch("");
            setCategoryFilter("all");
            setStatusFilter("all");
            setPage(1);
          }}
          totalCount={data?.total}
        />

        <AdminDataTable
          columns={columns}
          data={data?.items || []}
          keyExtractor={(t) => t.id}
          loading={loading}
          error={error}
          onRetry={fetchTemplates}
          emptyTitle="No templates found"
          emptyDescription="Create a new template or reset your filters."
          onRowPress={(t) => router.push(`/admin/templates/${t.id}` as any)}
        />
      </View>

      {/* Action Confirmation Modal */}
      <ConfirmDialog
        visible={!!targetTemplate && !!actionType}
        title={
          actionType === "publish"
            ? "Publish Template & Create Linear Revision"
            : actionType === "unpublish"
            ? "Unpublish Template to Draft"
            : actionType === "archive"
            ? "Archive Template"
            : actionType === "restore"
            ? "Restore Template"
            : actionType === "duplicate"
            ? "Duplicate as New Template"
            : "Permanently Delete Template"
        }
        message={
          actionType === "publish"
            ? `Publishing "${targetTemplate?.name_gu || targetTemplate?.name_en}" will increment its version to v${(targetTemplate?.version || 1) + 1} and write an immutable snapshot to template_revisions.`
            : actionType === "delete"
            ? `Are you sure you want to permanently delete template "${targetTemplate?.name_gu || targetTemplate?.name_en}"?`
            : `Are you sure you want to ${actionType} template "${targetTemplate?.name_gu || targetTemplate?.name_en}"?`
        }
        impactWarning={
          actionType === "delete"
            ? "CRITICAL SAFETY GUARANTEE: Permanent template deletion will NOT delete historical template_revisions. All generated document references will remain valid and intact."
            : actionType === "publish"
            ? "Published templates become immediately available to advocates in the document generation studio."
            : undefined
        }
        confirmVariant={actionType === "delete" ? "danger" : actionType === "unpublish" || actionType === "archive" ? "warning" : "primary"}
        confirmLabel={
          actionType === "publish"
            ? "Publish & Snapshot Version"
            : actionType === "delete"
            ? "Delete Template"
            : `${actionType?.toUpperCase()} Template`
        }
        loading={actionLoading}
        onConfirm={handleExecuteAction}
        onCancel={() => {
          setTargetTemplate(null);
          setActionType(null);
        }}
      />

      {/* Preview Modal */}
      <Modal
        visible={!!previewTemplate}
        transparent
        animationType="fade"
        onRequestClose={() => setPreviewTemplate(null)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalCard, { maxWidth: 700 }]}>
            <View style={styles.modalHeader}>
              <View style={{ flex: 1 }}>
                <Text style={styles.modalTitle}>
                  {previewTemplate?.name_gu || previewTemplate?.name_en}
                </Text>
                <Text style={styles.modalSub}>
                  {previewTemplate?.category} • Version v{previewTemplate?.version || 1} • {previewTemplate?.status?.toUpperCase()}
                </Text>
              </View>
              <Pressable onPress={() => setPreviewTemplate(null)} style={{ padding: 4 }}>
                <Ionicons name="close" size={20} color="#8B96A9" />
              </Pressable>
            </View>

            <View style={styles.previewTabs}>
              <Pressable
                onPress={() => setPreviewTab("gu")}
                style={[styles.previewTabBtn, previewTab === "gu" && styles.previewTabBtnActive]}
              >
                <Text style={[styles.previewTabBtnText, previewTab === "gu" && styles.previewTabBtnTextActive]}>
                  Gujarati Body (મુખ્ય વિગત)
                </Text>
              </Pressable>
              <Pressable
                onPress={() => setPreviewTab("en")}
                style={[styles.previewTabBtn, previewTab === "en" && styles.previewTabBtnActive]}
              >
                <Text style={[styles.previewTabBtnText, previewTab === "en" && styles.previewTabBtnTextActive]}>
                  English Body
                </Text>
              </Pressable>
            </View>

            <ScrollView style={styles.previewContentBox}>
              <Text style={styles.previewContentText}>
                {previewTab === "gu"
                  ? previewTemplate?.content_gu || "(No Gujarati body template defined)"
                  : previewTemplate?.content_en || "(No English body template defined)"}
              </Text>
            </ScrollView>

            <View style={styles.modalFooter}>
              <Pressable
                onPress={() => setPreviewTemplate(null)}
                style={styles.modalCancelBtn}
              >
                <Text style={styles.modalCancelText}>Close Preview</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>

      {/* Create / Edit Modal */}
      <Modal
        visible={formVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setFormVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalCard, { maxWidth: 640 }]}>
            <View style={styles.modalHeader}>
              <Ionicons name={editingId ? "create" : "add-circle"} size={22} color="#C5A059" />
              <View style={{ flex: 1, marginLeft: 8 }}>
                <Text style={styles.modalTitle}>
                  {editingId ? "Edit Legal Template" : "Create New Legal Template"}
                </Text>
                <Text style={styles.modalSub}>
                  {editingId
                    ? "Modifying canonical template fields. Publishing will trigger a new version snapshot."
                    : "Establish a new canonical template in the legal catalog."}
                </Text>
              </View>
              <Pressable onPress={() => setFormVisible(false)} style={{ padding: 4 }}>
                <Ionicons name="close" size={20} color="#8B96A9" />
              </Pressable>
            </View>

            <ScrollView style={{ maxHeight: 480, padding: 20 }} showsVerticalScrollIndicator={true}>
              {formError ? (
                <View style={styles.formErrorBox}>
                  <Ionicons name="alert-circle" size={16} color="#E53E3E" style={{ marginRight: 6 }} />
                  <Text style={styles.formErrorText}>{formError}</Text>
                </View>
              ) : null}

              <View style={styles.formGrid}>
                <View style={styles.formField}>
                  <Text style={styles.formLabel}>Gujarati Title (ગુજરાતી શીર્ષક) *</Text>
                  <TextInput
                    style={styles.formInput}
                    placeholder="દા.ત. મુદત અરજી (C.P.C. O-17 R-1)"
                    placeholderTextColor="#6B7280"
                    value={formNameGu}
                    onChangeText={setFormNameGu}
                  />
                </View>

                <View style={styles.formField}>
                  <Text style={styles.formLabel}>English Title *</Text>
                  <TextInput
                    style={styles.formInput}
                    placeholder="E.g. Adjournment Application"
                    placeholderTextColor="#6B7280"
                    value={formNameEn}
                    onChangeText={setFormNameEn}
                  />
                </View>

                <View style={styles.formField}>
                  <Text style={styles.formLabel}>Category</Text>
                  <TextInput
                    style={styles.formInput}
                    placeholder="Civil / Criminal / Revenue"
                    placeholderTextColor="#6B7280"
                    value={formCategory}
                    onChangeText={setFormCategory}
                  />
                </View>

                <View style={styles.formField}>
                  <Text style={styles.formLabel}>Sub Category</Text>
                  <TextInput
                    style={styles.formInput}
                    placeholder="E.g. Interim Applications"
                    placeholderTextColor="#6B7280"
                    value={formSubCategory}
                    onChangeText={setFormSubCategory}
                  />
                </View>

                <View style={styles.formFieldFull}>
                  <Text style={styles.formLabel}>Description</Text>
                  <TextInput
                    style={[styles.formInput, { height: 60 }]}
                    placeholder="Brief description of application scope..."
                    placeholderTextColor="#6B7280"
                    multiline
                    value={formDescription}
                    onChangeText={setFormDescription}
                  />
                </View>

                <View style={styles.formFieldFull}>
                  <Text style={styles.formLabel}>Gujarati Content Template</Text>
                  <TextInput
                    style={[styles.formInput, { height: 110, fontFamily: "serif" }]}
                    placeholder="આથી અરજદાર/વાદી તરફે નમ્ર નિવેદન છે કે..."
                    placeholderTextColor="#6B7280"
                    multiline
                    value={formContentGu}
                    onChangeText={setFormContentGu}
                  />
                </View>

                <View style={styles.formFieldFull}>
                  <Text style={styles.formLabel}>English Content Template</Text>
                  <TextInput
                    style={[styles.formInput, { height: 110 }]}
                    placeholder="The applicant / plaintiff most respectfully submits that..."
                    placeholderTextColor="#6B7280"
                    multiline
                    value={formContentEn}
                    onChangeText={setFormContentEn}
                  />
                </View>
              </View>
            </ScrollView>

            <View style={styles.modalFooter}>
              <Pressable
                onPress={() => setFormVisible(false)}
                style={styles.modalCancelBtn}
                disabled={formSubmitting}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </Pressable>
              <Pressable
                onPress={handleSaveTemplate}
                style={[styles.createBtn, formSubmitting && { opacity: 0.7 }]}
                disabled={formSubmitting}
              >
                {formSubmitting ? (
                  <ActivityIndicator size="small" color="#061024" style={{ marginRight: 6 }} />
                ) : null}
                <Text style={styles.createBtnText}>
                  {formSubmitting ? "Saving..." : editingId ? "Update Template" : "Create Template"}
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
  versionTag: {
    backgroundColor: "rgba(197, 160, 89, 0.15)",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    alignSelf: "flex-start",
  },
  versionText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#C5A059",
  },
  revisionBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#1B2A49",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "#253452",
    alignSelf: "flex-start",
  },
  revisionText: {
    fontSize: 11,
    color: "#D1D8E5",
    fontWeight: "500",
  },
  actionRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
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
    overflow: "hidden",
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    padding: 18,
    borderBottomWidth: 1,
    borderBottomColor: "#1B2A49",
    gap: 10,
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
  previewTabs: {
    flexDirection: "row",
    borderBottomWidth: 1,
    borderBottomColor: "#1B2A49",
    backgroundColor: "#0D182E",
  },
  previewTabBtn: {
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderBottomWidth: 2,
    borderBottomColor: "transparent",
  },
  previewTabBtnActive: {
    borderBottomColor: "#C5A059",
    backgroundColor: "#12203B",
  },
  previewTabBtnText: {
    fontSize: 13,
    color: "#8B96A9",
    fontWeight: "600",
  },
  previewTabBtnTextActive: {
    color: "#C5A059",
    fontWeight: "700",
  },
  previewContentBox: {
    maxHeight: 380,
    padding: 20,
    backgroundColor: "#08142D",
  },
  previewContentText: {
    fontSize: 14,
    color: "#FDFDFD",
    lineHeight: 24,
    fontFamily: "serif",
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
  formErrorBox: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(229, 62, 62, 0.12)",
    borderWidth: 1,
    borderColor: "rgba(229, 62, 62, 0.3)",
    padding: 10,
    borderRadius: 8,
    marginBottom: 14,
  },
  formErrorText: {
    fontSize: 12,
    color: "#F56565",
    flex: 1,
  },
  formGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 14,
  },
  formField: {
    width: "48%",
    minWidth: 240,
    gap: 6,
  },
  formFieldFull: {
    width: "100%",
    gap: 6,
  },
  formLabel: {
    fontSize: 12,
    fontWeight: "600",
    color: "#D1D8E5",
  },
  formInput: {
    backgroundColor: "#0B182E",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#253452",
    paddingHorizontal: 12,
    paddingVertical: 9,
    color: "#FDFDFD",
    fontSize: 13,
  },
});

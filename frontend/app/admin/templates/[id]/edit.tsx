import React, { useEffect, useState, useRef, useCallback } from "react";
import {
  StyleSheet,
  Text,
  View,
  Pressable,
  ActivityIndicator,
  Modal,
  ScrollView,
  Platform,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { AdminLayout } from "@/src/components/admin/AdminLayout";
import { StatusBadge } from "@/src/components/admin/StatusBadge";
import { ConfirmDialog } from "@/src/components/admin/ConfirmDialog";
import {
  AdminTemplateEditor,
  AdminTemplateEditorRef,
} from "@/src/components/admin/editor/AdminTemplateEditor";
import { adminApi } from "@/src/api/adminClient";
import { AdminTemplateItem } from "@/src/types/admin";

export default function AdminTemplateEditScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [template, setTemplate] = useState<AdminTemplateItem | null>(null);

  // Active language tab: "gu" | "en"
  const [activeLang, setActiveLang] = useState<"gu" | "en">("gu");

  // Editor refs for each language
  const guEditorRef = useRef<AdminTemplateEditorRef>(null);
  const enEditorRef = useRef<AdminTemplateEditorRef>(null);

  // Cached editor JSON state for switching tabs smoothly
  const [guJson, setGuJson] = useState<any>(null);
  const [enJson, setEnJson] = useState<any>(null);

  // Actions state
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);
  const [unpublishDialogOpen, setUnpublishDialogOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Preview modal state
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState<{
    en: { content: string; blocks: any[] };
    gu: { content: string; blocks: any[] };
  } | null>(null);
  const [previewTab, setPreviewTab] = useState<"gu" | "en">("gu");

  // Fetch template data
  const fetchTemplate = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await adminApi.getTemplate(id);
      setTemplate(data);
      setGuJson(data.editor_content_gu || null);
      setEnJson(data.editor_content_en || null);
    } catch (err: any) {
      setError(err?.message || "Failed to load template data.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTemplate();
  }, [fetchTemplate]);

  // Synchronize active editor JSON before switching tabs or saving
  const syncCurrentEditorState = () => {
    if (activeLang === "gu" && guEditorRef.current) {
      setGuJson(guEditorRef.current.getJSON());
    } else if (activeLang === "en" && enEditorRef.current) {
      setEnJson(enEditorRef.current.getJSON());
    }
  };

  const handleSwitchTab = (lang: "gu" | "en") => {
    if (lang === activeLang) return;
    syncCurrentEditorState();
    setActiveLang(lang);
  };

  // ── SAVE DRAFT ──
  const handleSaveDraft = async () => {
    if (!template || !id) return;
    syncCurrentEditorState();
    setSaving(true);
    setSaveSuccess(null);
    setActionError(null);

    try {
      // Get current content from refs or cached states
      const finalGuJson =
        activeLang === "gu" && guEditorRef.current
          ? guEditorRef.current.getJSON()
          : guJson;
      const finalGuText =
        activeLang === "gu" && guEditorRef.current
          ? guEditorRef.current.getPlainText()
          : template.content_gu || "";

      const finalEnJson =
        activeLang === "en" && enEditorRef.current
          ? enEditorRef.current.getJSON()
          : enJson;
      const finalEnText =
        activeLang === "en" && enEditorRef.current
          ? enEditorRef.current.getPlainText()
          : template.content_en || "";

      await adminApi.updateTemplate(id, {
        content_gu: finalGuText,
        content_en: finalEnText,
        editor_content_gu: finalGuJson,
        editor_content_en: finalEnJson,
      });

      setSaveSuccess("Draft saved successfully at " + new Date().toLocaleTimeString());
      // Refresh template
      const updated = await adminApi.getTemplate(id);
      setTemplate(updated);
    } catch (err: any) {
      setActionError(err?.message || "Failed to save draft.");
    } finally {
      setSaving(false);
    }
  };

  // ── PREVIEW ──
  const handleOpenPreview = async () => {
    if (!template || !id) return;
    syncCurrentEditorState();
    setPreviewOpen(true);
    setPreviewLoading(true);
    setPreviewTab(activeLang);

    try {
      const currentGuText =
        activeLang === "gu" && guEditorRef.current
          ? guEditorRef.current.getPlainText()
          : template.content_gu || "";
      const currentEnText =
        activeLang === "en" && enEditorRef.current
          ? enEditorRef.current.getPlainText()
          : template.content_en || "";

      const res = await adminApi.previewTemplate(id, {
        content_gu: currentGuText,
        content_en: currentEnText,
        fields: template.fields,
        name_en: template.name_en,
        name_gu: template.name_gu,
      });

      setPreviewData(res.preview);
    } catch (err: any) {
      setActionError(err?.message || "Failed to generate preview.");
    } finally {
      setPreviewLoading(false);
    }
  };

  // ── PUBLISH ──
  const handlePublishConfirm = async () => {
    if (!template || !id) return;
    setActionLoading(true);
    setActionError(null);

    try {
      // First save current editor state
      const currentGuText =
        activeLang === "gu" && guEditorRef.current
          ? guEditorRef.current.getPlainText()
          : template.content_gu || "";
      const currentEnText =
        activeLang === "en" && enEditorRef.current
          ? enEditorRef.current.getPlainText()
          : template.content_en || "";
      const currentGuJson =
        activeLang === "gu" && guEditorRef.current
          ? guEditorRef.current.getJSON()
          : guJson;
      const currentEnJson =
        activeLang === "en" && enEditorRef.current
          ? enEditorRef.current.getJSON()
          : enJson;

      await adminApi.updateTemplate(id, {
        content_gu: currentGuText,
        content_en: currentEnText,
        editor_content_gu: currentGuJson,
        editor_content_en: currentEnJson,
      });

      // Now publish
      await adminApi.publishTemplate(id);
      setPublishDialogOpen(false);
      router.push(`/admin/templates/${id}` as any);
    } catch (err: any) {
      setActionError(err?.message || "Failed to publish template.");
    } finally {
      setActionLoading(false);
    }
  };

  // ── UNPUBLISH ──
  const handleUnpublishConfirm = async () => {
    if (!template || !id) return;
    setActionLoading(true);
    setActionError(null);
    try {
      await adminApi.unpublishTemplate(id);
      setUnpublishDialogOpen(false);
      await fetchTemplate();
    } catch (err: any) {
      setActionError(err?.message || "Failed to unpublish template.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <AdminLayout title="Template Editor" subtitle="Loading template content...">
        <View style={styles.centerBox}>
          <ActivityIndicator size="large" color="#C5A059" />
          <Text style={styles.loadingText}>Loading document template...</Text>
        </View>
      </AdminLayout>
    );
  }

  if (error || !template) {
    return (
      <AdminLayout title="Template Editor" subtitle="Error loading template">
        <View style={styles.centerBox}>
          <Ionicons name="alert-circle" size={48} color="#E53E3E" />
          <Text style={styles.errorTitle}>Could not load template</Text>
          <Text style={styles.errorSub}>{error || "Template not found"}</Text>
          <Pressable
            onPress={() => router.push("/admin/templates" as any)}
            style={styles.btnSecondary}
          >
            <Text style={styles.btnSecondaryText}>Return to Templates</Text>
          </Pressable>
        </View>
      </AdminLayout>
    );
  }

  const isPublished = template.status === "published";

  return (
    <AdminLayout
      title={`Edit: ${template.name_gu || template.name_en}`}
      subtitle={`Canonical ID: ${template.id} • Version v${template.version || 1} • Status: ${template.status.toUpperCase()}`}
      actions={
        <View style={styles.headerActions}>
          <Pressable
            onPress={() => router.push(`/admin/templates/${template.id}` as any)}
            style={styles.btnCancel}
          >
            <Ionicons name="arrow-back" size={16} color="#8B96A9" style={{ marginRight: 6 }} />
            <Text style={styles.btnCancelText}>Cancel</Text>
          </Pressable>

          <Pressable
            onPress={handleOpenPreview}
            style={styles.btnPreview}
          >
            <Ionicons name="eye-outline" size={16} color="#4299E1" style={{ marginRight: 6 }} />
            <Text style={styles.btnPreviewText}>Live Preview</Text>
          </Pressable>

          {isPublished ? (
            <Pressable
              onPress={() => setUnpublishDialogOpen(true)}
              style={styles.btnUnpublish}
            >
              <Ionicons name="lock-open-outline" size={16} color="#ED8936" style={{ marginRight: 6 }} />
              <Text style={styles.btnUnpublishText}>Unpublish to Edit</Text>
            </Pressable>
          ) : (
            <>
              <Pressable
                onPress={handleSaveDraft}
                disabled={saving}
                style={[styles.btnSave, saving && { opacity: 0.7 }]}
              >
                {saving ? (
                  <ActivityIndicator size="small" color="#FDFDFD" style={{ marginRight: 6 }} />
                ) : (
                  <Ionicons name="save-outline" size={16} color="#FDFDFD" style={{ marginRight: 6 }} />
                )}
                <Text style={styles.btnSaveText}>{saving ? "Saving..." : "Save Draft"}</Text>
              </Pressable>

              <Pressable
                onPress={() => setPublishDialogOpen(true)}
                style={styles.btnPublish}
              >
                <Ionicons name="cloud-upload" size={16} color="#061024" style={{ marginRight: 6 }} />
                <Text style={styles.btnPublishText}>Publish Version</Text>
              </Pressable>
            </>
          )}
        </View>
      }
    >
      <View style={styles.editorRoot}>
        {/* Status Banners */}
        {isPublished && (
          <View style={styles.publishedBanner}>
            <Ionicons name="shield-checkmark" size={18} color="#C5A059" style={{ marginRight: 8 }} />
            <Text style={styles.publishedBannerText}>
              This template is currently <Text style={{ fontWeight: "700" }}>PUBLISHED</Text> and locked to prevent accidental modifications to live lawyer documents. Click "Unpublish to Edit" to create a new editable draft.
            </Text>
          </View>
        )}

        {saveSuccess && (
          <View style={styles.successBanner}>
            <Ionicons name="checkmark-circle" size={18} color="#48BB78" style={{ marginRight: 8 }} />
            <Text style={styles.successBannerText}>{saveSuccess}</Text>
          </View>
        )}

        {actionError && (
          <View style={styles.errorBanner}>
            <Ionicons name="alert-circle" size={18} color="#E53E3E" style={{ marginRight: 8 }} />
            <Text style={styles.errorBannerText}>{actionError}</Text>
          </View>
        )}

        {/* Language Tabs & Variable Info Bar */}
        <View style={styles.tabBar}>
          <View style={styles.tabGroup}>
            <Pressable
              onPress={() => handleSwitchTab("gu")}
              style={[styles.langTab, activeLang === "gu" && styles.langTabActive]}
            >
              <Text
                style={[
                  styles.langTabText,
                  activeLang === "gu" && styles.langTabTextActive,
                ]}
              >
                ગુજરાતી Template (Primary)
              </Text>
            </Pressable>

            <Pressable
              onPress={() => handleSwitchTab("en")}
              style={[styles.langTab, activeLang === "en" && styles.langTabActive]}
            >
              <Text
                style={[
                  styles.langTabText,
                  activeLang === "en" && styles.langTabTextActive,
                ]}
              >
                English Template
              </Text>
            </Pressable>
          </View>

          <View style={styles.schemaInfo}>
            <Text style={styles.schemaInfoText}>
              <Text style={{ color: "#C5A059", fontWeight: "700" }}>
                {template.fields?.length ?? 0}
              </Text>{" "}
              Schema Fields Configured
            </Text>
          </View>
        </View>

        {/* Tiptap Editor Canvas */}
        <View style={styles.canvasContainer}>
          {activeLang === "gu" ? (
            <AdminTemplateEditor
              ref={guEditorRef}
              key="gu-editor"
              initialContent={guJson}
              initialPlainText={template.content_gu}
              language="gu"
              fields={template.fields || []}
            />
          ) : (
            <AdminTemplateEditor
              ref={enEditorRef}
              key="en-editor"
              initialContent={enJson}
              initialPlainText={template.content_en}
              language="en"
              fields={template.fields || []}
            />
          )}
        </View>
      </View>

      {/* ── PUBLISH CONFIRMATION DIALOG ── */}
      <ConfirmDialog
        visible={publishDialogOpen}
        title={`Publish Template Version ${template.version || 1}?`}
        message={`Publishing will make version ${template.version || 1} active for all lawyers generating this application. An immutable revision snapshot will be permanently preserved in template_revisions.`}
        impactWarning="This action locks the current version. Any subsequent edits will increment the version number."
        confirmLabel="Publish Version"
        confirmVariant="primary"
        loading={actionLoading}
        onConfirm={handlePublishConfirm}
        onCancel={() => setPublishDialogOpen(false)}
      />

      {/* ── UNPUBLISH CONFIRMATION DIALOG ── */}
      <ConfirmDialog
        visible={unpublishDialogOpen}
        title="Unpublish Template to Draft?"
        message="Unpublishing will revert this template to draft status so you can edit its content and schema fields. Lawyers will temporarily not see this template in the catalog until republished."
        confirmVariant="warning"
        confirmLabel="Unpublish to Draft"
        loading={actionLoading}
        onConfirm={handleUnpublishConfirm}
        onCancel={() => setUnpublishDialogOpen(false)}
      />

      {/* ── LIVE PREVIEW MODAL ── */}
      <Modal visible={previewOpen} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <View style={styles.modalHeaderTitleRow}>
                <Ionicons name="document-text" size={20} color="#C5A059" />
                <Text style={styles.modalTitle}>
                  Live Template Preview — Sample Values Applied
                </Text>
              </View>
              <Pressable onPress={() => setPreviewOpen(false)} style={styles.modalCloseBtn}>
                <Ionicons name="close" size={20} color="#8B96A9" />
              </Pressable>
            </View>

            {/* Preview Tabs */}
            <View style={styles.previewTabBar}>
              <Pressable
                onPress={() => setPreviewTab("gu")}
                style={[
                  styles.previewTabBtn,
                  previewTab === "gu" && styles.previewTabBtnActive,
                ]}
              >
                <Text
                  style={[
                    styles.previewTabBtnText,
                    previewTab === "gu" && styles.previewTabBtnTextActive,
                  ]}
                >
                  Gujarati Document Preview
                </Text>
              </Pressable>
              <Pressable
                onPress={() => setPreviewTab("en")}
                style={[
                  styles.previewTabBtn,
                  previewTab === "en" && styles.previewTabBtnActive,
                ]}
              >
                <Text
                  style={[
                    styles.previewTabBtnText,
                    previewTab === "en" && styles.previewTabBtnTextActive,
                  ]}
                >
                  English Document Preview
                </Text>
              </Pressable>
            </View>

            {previewLoading ? (
              <View style={styles.previewLoadingBox}>
                <ActivityIndicator size="large" color="#C5A059" />
                <Text style={styles.previewLoadingText}>
                  Rendering legal document with HarfBuzz shaping...
                </Text>
              </View>
            ) : previewData ? (
              <ScrollView style={styles.previewBodyScroll} contentContainerStyle={styles.previewBody}>
                <View style={styles.previewPage}>
                  {(previewTab === "gu"
                    ? previewData.gu?.blocks
                    : previewData.en?.blocks
                  )?.map((block: any, idx: number) => {
                    const isCenter = block.align === "center";
                    const isRight = block.align === "right";
                    const isBold = block.bold;
                    const isSpacer = block.section === "spacer" || !block.text;
                    const isPageBreak = block.section === "page_break";

                    if (isPageBreak) {
                      return (
                        <View key={idx} style={styles.previewPageBreak}>
                          <Text style={styles.previewPageBreakText}>— PAGE BREAK —</Text>
                        </View>
                      );
                    }

                    if (isSpacer) {
                      return <View key={idx} style={{ height: 12 }} />;
                    }

                    return (
                      <Text
                        key={idx}
                        style={[
                          styles.previewText,
                          isCenter && { textAlign: "center" },
                          isRight && { textAlign: "right" },
                          isBold && { fontWeight: "700" },
                          block.indent && { textIndent: 24 },
                          previewTab === "gu" && { fontFamily: Platform.OS === "web" ? "'AnekGujarati', serif" : "serif" },
                        ]}
                      >
                        {block.text}
                      </Text>
                    );
                  })}
                </View>
              </ScrollView>
            ) : (
              <View style={styles.previewLoadingBox}>
                <Text style={{ color: "#8B96A9" }}>No preview data generated.</Text>
              </View>
            )}

            <View style={styles.modalFooter}>
              <Pressable
                onPress={() => setPreviewOpen(false)}
                style={styles.btnSecondary}
              >
                <Text style={styles.btnSecondaryText}>Close Preview</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  centerBox: {
    padding: 60,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
  },
  loadingText: {
    color: "#8B96A9",
    fontSize: 14,
  },
  errorTitle: {
    color: "#FDFDFD",
    fontSize: 18,
    fontWeight: "700",
    marginTop: 8,
  },
  errorSub: {
    color: "#8B96A9",
    fontSize: 13,
  },
  headerActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  btnCancel: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "#1B2A49",
    backgroundColor: "#0B1B3D",
  },
  btnCancelText: {
    color: "#8B96A9",
    fontSize: 13,
    fontWeight: "600",
  },
  btnPreview: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "rgba(66, 153, 225, 0.4)",
    backgroundColor: "rgba(66, 153, 225, 0.1)",
  },
  btnPreviewText: {
    color: "#4299E1",
    fontSize: 13,
    fontWeight: "700",
  },
  btnSave: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "#2B3C5E",
    backgroundColor: "#162544",
  },
  btnSaveText: {
    color: "#FDFDFD",
    fontSize: 13,
    fontWeight: "700",
  },
  btnPublish: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
    backgroundColor: "#C5A059",
  },
  btnPublishText: {
    color: "#061024",
    fontSize: 13,
    fontWeight: "800",
  },
  btnUnpublish: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "rgba(237, 137, 54, 0.4)",
    backgroundColor: "rgba(237, 137, 54, 0.1)",
  },
  btnUnpublishText: {
    color: "#ED8936",
    fontSize: 13,
    fontWeight: "700",
  },
  editorRoot: {
    gap: 12,
    flex: 1,
  },
  publishedBanner: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(197, 160, 89, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(197, 160, 89, 0.3)",
    padding: 12,
    borderRadius: 8,
  },
  publishedBannerText: {
    fontSize: 13,
    color: "#FDFDFD",
    flex: 1,
    lineHeight: 18,
  },
  successBanner: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(72, 187, 120, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(72, 187, 120, 0.3)",
    padding: 10,
    borderRadius: 8,
  },
  successBannerText: {
    fontSize: 13,
    color: "#48BB78",
    fontWeight: "600",
  },
  errorBanner: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(229, 62, 62, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(229, 62, 62, 0.3)",
    padding: 10,
    borderRadius: 8,
  },
  errorBannerText: {
    fontSize: 13,
    color: "#E53E3E",
    fontWeight: "600",
  },
  tabBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#0B1B3D",
    borderRadius: 8,
    padding: 4,
    borderWidth: 1,
    borderColor: "#1B2A49",
  },
  tabGroup: {
    flexDirection: "row",
    gap: 4,
  },
  langTab: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
  },
  langTabActive: {
    backgroundColor: "#162544",
  },
  langTabText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#8B96A9",
  },
  langTabTextActive: {
    color: "#C5A059",
    fontWeight: "700",
  },
  schemaInfo: {
    paddingRight: 12,
  },
  schemaInfoText: {
    fontSize: 12,
    color: "#8B96A9",
  },
  canvasContainer: {
    minHeight: 700,
    flex: 1,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.75)",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  modalContent: {
    width: "100%",
    maxWidth: 860,
    maxHeight: "90%",
    backgroundColor: "#0B1B3D",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#1B2A49",
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#162544",
  },
  modalHeaderTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  modalTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#FDFDFD",
  },
  modalCloseBtn: {
    padding: 4,
  },
  previewTabBar: {
    flexDirection: "row",
    backgroundColor: "#061024",
    borderBottomWidth: 1,
    borderBottomColor: "#162544",
    paddingHorizontal: 16,
    paddingTop: 8,
    gap: 8,
  },
  previewTabBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderBottomWidth: 2,
    borderBottomColor: "transparent",
  },
  previewTabBtnActive: {
    borderBottomColor: "#C5A059",
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
  previewLoadingBox: {
    padding: 60,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
  },
  previewLoadingText: {
    color: "#8B96A9",
    fontSize: 13,
  },
  previewBodyScroll: {
    flex: 1,
    backgroundColor: "#3A4050",
  },
  previewBody: {
    padding: 24,
    alignItems: "center",
  },
  previewPage: {
    width: "100%",
    maxWidth: 700,
    minHeight: 800,
    backgroundColor: "#FFFFFF",
    padding: 48,
    borderRadius: 4,
    shadowColor: "#000",
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 6,
    gap: 6,
  },
  previewText: {
    fontSize: 13,
    lineHeight: 20,
    color: "#1A1A1A",
  },
  previewPageBreak: {
    marginVertical: 16,
    paddingVertical: 8,
    borderTopWidth: 2,
    borderBottomWidth: 2,
    borderStyle: "dashed",
    borderColor: "#8B96A9",
    alignItems: "center",
  },
  previewPageBreakText: {
    fontSize: 11,
    fontWeight: "700",
    color: "#8B96A9",
    letterSpacing: 2,
  },
  modalFooter: {
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: "#162544",
    flexDirection: "row",
    justifyContent: "flex-end",
  },
  btnSecondary: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
    backgroundColor: "#162544",
  },
  btnSecondaryText: {
    color: "#D1D8E5",
    fontSize: 13,
    fontWeight: "600",
  },
});

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { api, invalidateApiCache } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";
import { useKeyboardHeight } from "@/src/hooks/useKeyboardHeight";
import { DesktopPage } from "@/src/components/DesktopPage";
import { ConfirmModal } from "@/src/components/ConfirmModal";
import { saveDocument, shareDocumentFile } from "@/src/utils/download";
import { safeBack } from "@/src/utils/navigation";

type VaultTab = "all" | "documents" | "drafts";

function fmtDate(iso?: string) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso.slice(0, 10);
  return (
    d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) +
    " · " +
    d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })
  );
}

function fmtFileSize(bytes?: number) {
  if (!bytes || bytes <= 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentVault() {
  const { colors } = useTheme();
  const { isDesktop } = useResponsive();
  const params = useLocalSearchParams<{ tab?: string; filter?: string }>();

  const initialTab: VaultTab =
    params.tab === "drafts" || params.filter === "drafts"
      ? "drafts"
      : params.tab === "documents" || params.filter === "documents"
      ? "documents"
      : "all";

  const [activeTab, setActiveTab] = useState<VaultTab>(initialTab);
  const [searchQuery, setSearchQuery] = useState("");
  const { keyboardHeight } = useKeyboardHeight();
  const [documents, setDocuments] = useState<any[]>([]);
  const [drafts, setDrafts] = useState<any[]>([]);
  const [selectedDraftIds, setSelectedDraftIds] = useState<Set<string>>(new Set());
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [confirmModal, setConfirmModal] = useState<{
    title: string;
    message: string;
    confirmLabel?: string;
    onConfirm: () => Promise<void>;
  } | null>(null);
  const [confirmBusy, setConfirmBusy] = useState(false);

  useEffect(() => {
    const t = params.tab || (params.filter === "drafts" ? "drafts" : params.filter === "documents" ? "documents" : null);
    if (t && (t === "all" || t === "documents" || t === "drafts")) {
      setActiveTab(t as VaultTab);
    }
  }, [params.tab, params.filter]);

  const loadData = useCallback(async () => {
    try {
      const [docsRes, draftsRes] = await Promise.all([
        api.history().catch(() => []),
        api.drafts().catch(() => []),
      ]);
      setDocuments(Array.isArray(docsRes) ? docsRes : []);
      setDrafts(Array.isArray(draftsRes) ? draftsRes : []);
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadData();
    }, [loadData])
  );

  const onRefresh = async () => {
    setRefreshing(true);
    invalidateApiCache("/applications/history");
    invalidateApiCache("/drafts");
    await loadData();
    setRefreshing(false);
  };

  const isDraftEligible = useCallback((d: any) => {
    const isCompleted = d.is_completed || d.status === "completed" || d.submitted || d.is_submitted;
    return !isCompleted && Boolean(d.id || d._id);
  }, []);

  const handleConfirmProceed = async () => {
    if (!confirmModal || confirmBusy) return;
    setConfirmBusy(true);
    try {
      await confirmModal.onConfirm();
      setConfirmModal(null);
    } finally {
      setConfirmBusy(false);
    }
  };

  const handleDeleteDocument = (doc: any) => {
    const docId = doc.id || doc._id;
    if (!docId) return;
    setConfirmModal({
      title: "Delete Document",
      message: "Remove this generated/downloaded application from your Vault?",
      confirmLabel: "Delete",
      onConfirm: async () => {
        try {
          await api.deleteApplication(docId);
          setDocuments((prev) => prev.filter((d) => (d.id || d._id) !== docId));
        } catch (err: any) {
          Alert.alert("Error", err?.message || "Could not delete document");
        }
      },
    });
  };

  const handleDeleteDraft = (draft: any) => {
    const draftId = draft.id || draft._id;
    if (!draftId) return;
    setConfirmModal({
      title: "Delete Draft",
      message: "Are you sure you want to permanently delete this saved draft?",
      confirmLabel: "Delete",
      onConfirm: async () => {
        try {
          await api.deleteDraft(draftId);
          setDrafts((prev) => prev.filter((d) => (d.id || d._id) !== draftId));
          setSelectedDraftIds((prev) => {
            const next = new Set(prev);
            next.delete(draftId);
            return next;
          });
        } catch (err: any) {
          Alert.alert("Error", err?.message || "Could not delete draft");
        }
      },
    });
  };

  const executeBulkDelete = async () => {
    const toDeleteIds = Array.from(selectedDraftIds);
    if (toDeleteIds.length === 0) return;
    setIsBulkDeleting(true);

    const successfulIds: string[] = [];
    const failedIds: string[] = [];

    await Promise.all(
      toDeleteIds.map(async (id) => {
        try {
          await api.deleteDraft(id);
          successfulIds.push(id);
        } catch {
          failedIds.push(id);
        }
      })
    );

    if (successfulIds.length > 0) {
      setDrafts((prev) => prev.filter((d) => !successfulIds.includes(d.id || d._id)));
      setSelectedDraftIds((prev) => {
        const next = new Set(prev);
        successfulIds.forEach((id) => next.delete(id));
        return next;
      });
    }

    setIsBulkDeleting(false);

    if (failedIds.length > 0) {
      Alert.alert(
        "Partial Failure",
        `Deleted ${successfulIds.length} draft(s). Failed to delete ${failedIds.length} draft(s). Please try again.`
      );
    }
  };

  const handleBulkDelete = () => {
    const count = selectedDraftIds.size;
    if (count === 0) return;
    setConfirmModal({
      title: "Delete Selected Drafts",
      message: `Are you sure you want to permanently delete ${count} selected draft(s)? This action cannot be undone.`,
      confirmLabel: `Delete (${count})`,
      onConfirm: executeBulkDelete,
    });
  };

  const handleReDownload = async (doc: any) => {
    const docId = doc.id || doc._id;
    setDownloadingId(docId);
    const savedValues = doc.values || doc.form_values || {};
    const hasSavedValues = Object.keys(savedValues).length > 0;
    try {
      const payload: any = {
        application_id: docId,
        template_id: doc.template_id,
        template_version: doc.template_version,
        case_id: doc.case_id || undefined,
        language: doc.language || "gu",
        format: doc.format || "pdf",
        filename: doc.filename || "legal_document",
        values: savedValues,
        form_values: doc.form_values || undefined,
      };
      const res = await api.downloadApp(payload);
      if (res && res.base64) {
        const dlPayload = {
          filename: res.filename || doc.filename,
          mime_type: res.mime_type,
          base64: res.base64,
        };
        const fmt = (doc.format || "pdf") as "pdf" | "docx" | "odt" | "png";
        await saveDocument(dlPayload, fmt);
        if (Platform.OS !== "web") {
          Alert.alert(
            "Saved to Device",
            `${dlPayload.filename} has been saved to your device folder.`,
            [
              {
                text: "Share / Open",
                onPress: () => {
                  shareDocumentFile(dlPayload, fmt).catch(() => {});
                },
              },
              { text: "OK" },
            ]
          );
        } else {
          Alert.alert("Download Complete", `${dlPayload.filename} has been downloaded.`);
        }
      } else {
        throw new Error("The server returned an empty document. Please try again.");
      }
    } catch (err: any) {
      const msg = String(err?.message || "");
      const looksMissingFields =
        !hasSavedValues &&
        (msg.toLowerCase().includes("missing") ||
          msg.toLowerCase().includes("required") ||
          msg.includes("400") ||
          msg.includes("422"));
      if (looksMissingFields) {
        router.push({
          pathname: "/template/[id]",
          params: {
            id: doc.template_id,
            case_id: doc.case_id || "",
            lang: doc.language || "gu",
            application_id: docId,
          },
        } as any);
      } else {
        Alert.alert("Download Failed", msg || "Could not save document to your device.");
      }
    } finally {
      setDownloadingId(null);
    }
  };

  const q = searchQuery.trim().toLowerCase();

  const filteredDocs = documents.filter((d) => {
    if (!q) return true;
    return (
      (d.template_name || "").toLowerCase().includes(q) ||
      (d.filename || "").toLowerCase().includes(q) ||
      (d.case_id || "").toLowerCase().includes(q) ||
      (d.format || "").toLowerCase().includes(q)
    );
  });

  const filteredDrafts = drafts.filter((d) => {
    if (!q) return true;
    return (
      (d.template_name || d.template_id || "").toLowerCase().includes(q) ||
      (d.case_number || d.case_id || "").toLowerCase().includes(q) ||
      (d.party_name || "").toLowerCase().includes(q)
    );
  });

  const eligibleDrafts = useMemo(() => {
    return filteredDrafts.filter(isDraftEligible);
  }, [filteredDrafts, isDraftEligible]);

  const isAllSelected = eligibleDrafts.length > 0 && eligibleDrafts.every((d) => selectedDraftIds.has(d.id || d._id));

  const toggleDraftSelection = (id: string) => {
    setSelectedDraftIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleToggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedDraftIds(new Set());
    } else {
      const allEligibleIds = eligibleDrafts.map((d) => d.id || d._id).filter(Boolean);
      setSelectedDraftIds(new Set(allEligibleIds));
    }
  };

  const renderDocumentCard = (doc: any) => {
    const docId = doc.id || doc._id;
    const isDocx = doc.format === "docx";
    const isOdt = doc.format === "odt";
    const iconColor = isDocx ? "#2563EB" : isOdt ? "#0D9488" : "#B91C1C";
    const isDownloading = downloadingId === docId;

    return (
      <View
        key={`doc-${docId}`}
        style={[
          styles.card,
          { backgroundColor: colors.surfaceSecondary, borderColor: colors.border },
        ]}
      >
        <View style={[styles.iconBox, { backgroundColor: iconColor + "18" }]}>
          <Ionicons
            name={isDocx ? "document-text" : isOdt ? "newspaper" : "document"}
            size={22}
            color={iconColor}
          />
        </View>

        <View style={{ flex: 1, minWidth: 0, marginHorizontal: Spacing.sm }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
            <Text style={[styles.cardTitle, { color: colors.onSurface }]} numberOfLines={1}>
              {doc.template_name || doc.filename || "Legal Document"}
            </Text>
            <View style={[styles.pill, { backgroundColor: iconColor + "20" }]}>
              <Text style={[styles.pillText, { color: iconColor }]}>
                {(doc.format || "pdf").toUpperCase()}
              </Text>
            </View>
            <View style={[styles.pill, { backgroundColor: colors.border }]}>
              <Text style={[styles.pillText, { color: colors.muted }]}>
                {doc.language === "gu" ? "ગુજરાતી" : "English"}
              </Text>
            </View>
          </View>

          <Text style={[styles.cardMeta, { color: colors.muted }]} numberOfLines={1}>
            {doc.filename || "document"} • {fmtFileSize(doc.file_size)} • {fmtDate(doc.created_at)}
          </Text>

          {doc.case_id ? (
            <Text style={[styles.cardCase, { color: colors.brandPrimary }]} numberOfLines={1}>
              Linked Case: {doc.case_id}
            </Text>
          ) : null}
        </View>

        <View style={styles.actionCol}>
          <Pressable
            testID={`vault-download-${docId}`}
            onPress={() => handleReDownload(doc)}
            disabled={isDownloading}
            style={[
              styles.actionBtn,
              { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
            ]}
          >
            {isDownloading ? (
              <ActivityIndicator size="small" color={colors.onBrandPrimary} />
            ) : (
              <>
                <Ionicons name="cloud-download-outline" size={15} color={colors.onBrandPrimary} />
                <Text style={[styles.actionBtnText, { color: colors.onBrandPrimary }]}>Download</Text>
              </>
            )}
          </Pressable>

          <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
            <Pressable
              testID={`vault-open-${docId}`}
              onPress={() =>
                router.push({
                  pathname: "/template/[id]",
                  params: {
                    id: doc.template_id,
                    case_id: doc.case_id || "",
                    lang: doc.language || "gu",
                    application_id: docId,
                  },
                } as any)
              }
              style={[styles.actionBtnSecondary, { borderColor: colors.border }]}
            >
              <Ionicons name="create-outline" size={14} color={colors.onSurface} />
              <Text style={[styles.actionBtnSecondaryText, { color: colors.onSurface }]}>Edit</Text>
            </Pressable>

            <Pressable
              testID={`vault-del-doc-${docId}`}
              onPress={() => handleDeleteDocument(doc)}
              hitSlop={6}
              style={[styles.actionBtnDanger, { borderColor: colors.error + "40" }]}
            >
              <Ionicons name="trash-outline" size={14} color={colors.error} />
            </Pressable>
          </View>
        </View>
      </View>
    );
  };

  const renderDraftCard = (draft: any) => {
    const draftId = draft.id || draft._id;
    const isSelected = selectedDraftIds.has(draftId);
    const isEligible = isDraftEligible(draft);

    return (
      <View
        key={`draft-${draftId}`}
        style={[
          styles.card,
          {
            backgroundColor: colors.surfaceSecondary,
            borderColor: isSelected ? colors.brandPrimary : colors.border,
          },
        ]}
      >
        {isEligible && (
          <Pressable
            testID={`vault-draft-checkbox-${draftId}`}
            onPress={() => toggleDraftSelection(draftId)}
            hitSlop={8}
            style={styles.checkboxTouch}
          >
            <Ionicons
              name={isSelected ? "checkbox" : "square-outline"}
              size={20}
              color={isSelected ? colors.brandPrimary : colors.muted}
            />
          </Pressable>
        )}

        <View style={[styles.iconBox, { backgroundColor: "#F59E0B18" }]}>
          <Ionicons name="time" size={22} color="#D97706" />
        </View>

        <View style={{ flex: 1, minWidth: 0, marginHorizontal: Spacing.sm }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
            <Text style={[styles.cardTitle, { color: colors.onSurface }]} numberOfLines={1}>
              {draft.template_name || draft.template_id || "Unfinished Draft"}
            </Text>
            <View style={[styles.pill, { backgroundColor: "#FEF3C7" }]}>
              <Text style={[styles.pillText, { color: "#B45309" }]}>DRAFT</Text>
            </View>
          </View>

          <Text style={[styles.cardMeta, { color: colors.muted }]} numberOfLines={1}>
            Last edited: {fmtDate(draft.updated_at || draft.created_at)}
          </Text>

          {draft.case_number || draft.case_id ? (
            <Text style={[styles.cardCase, { color: colors.brandPrimary }]} numberOfLines={1}>
              Case: {draft.case_number || draft.case_id}
            </Text>
          ) : null}
        </View>

        <View style={styles.actionCol}>
          <Pressable
            testID={`vault-resume-${draftId}`}
            onPress={() =>
              router.push(
                `/template/${draft.template_id}?case_id=${draft.case_id || ""}&lang=${
                  draft.language || "gu"
                }&draft=1` as any
              )
            }
            style={[
              styles.actionBtn,
              { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
            ]}
          >
            <Ionicons name="arrow-forward" size={15} color={colors.onBrandPrimary} />
            <Text style={[styles.actionBtnText, { color: colors.onBrandPrimary }]}>Resume</Text>
          </Pressable>

          <Pressable
            testID={`vault-del-draft-${draftId}`}
            onPress={() => handleDeleteDraft(draft)}
            style={[styles.actionBtnDanger, { borderColor: colors.error + "40" }]}
          >
            <Ionicons name="trash-outline" size={14} color={colors.error} />
          </Pressable>
        </View>
      </View>
    );
  };

  const content = (
    <View style={isDesktop ? { maxWidth: 960, width: "100%", alignSelf: "center" } : { flex: 1 }}>
      {/* Search and filter header */}
      <View style={{ paddingHorizontal: Spacing.md, paddingTop: Spacing.sm }}>
        <View
          style={[
            styles.searchBar,
            { backgroundColor: colors.surfaceSecondary, borderColor: colors.border },
          ]}
        >
          <Ionicons name="search" size={18} color={colors.muted} />
          <TextInput
            testID="vault-search-input"
            value={searchQuery}
            onChangeText={setSearchQuery}
            placeholder="Search documents, drafts, cases..."
            placeholderTextColor={colors.muted}
            style={[styles.searchInput, { color: colors.onSurface }]}
          />
          {searchQuery ? (
            <Pressable onPress={() => setSearchQuery("")} hitSlop={8}>
              <Ionicons name="close-circle" size={18} color={colors.muted} />
            </Pressable>
          ) : null}
        </View>

        {/* Tab Pills */}
        <View style={styles.tabRow}>
          {[
            { id: "all", label: `All (${documents.length + drafts.length})` },
            { id: "documents", label: `Generated (${documents.length})` },
            { id: "drafts", label: `Drafts (${drafts.length})` },
          ].map((t) => {
            const active = activeTab === t.id;
            return (
              <Pressable
                key={t.id}
                testID={`vault-tab-${t.id}`}
                onPress={() => setActiveTab(t.id as VaultTab)}
                style={[
                  styles.tabChip,
                  {
                    backgroundColor: active ? colors.brandPrimary : colors.surfaceSecondary,
                    borderColor: active ? colors.brandPrimary : colors.border,
                  },
                ]}
              >
                <Text
                  style={[
                    styles.tabChipText,
                    { color: active ? colors.onBrandPrimary : colors.onSurface },
                  ]}
                >
                  {t.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      {/* Main List */}
      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.brandPrimary} />
          <Text style={{ color: colors.muted, marginTop: Spacing.md }}>Loading vault...</Text>
        </View>
      ) : (
        <ScrollView
          style={{ flex: 1 }}
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={{ padding: Spacing.md, paddingBottom: 100 + (keyboardHeight > 0 ? keyboardHeight : 0) }}
        >
          {(activeTab === "all" || activeTab === "drafts") && filteredDrafts.length > 0 && (
            <View style={{ marginBottom: Spacing.lg }}>
              <View
                style={[
                  styles.sectionHeader,
                  { justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: Spacing.xs },
                ]}
              >
                <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                  <Ionicons name="time-outline" size={16} color={colors.brandPrimary} />
                  <Text style={[styles.sectionTitle, { color: colors.onSurface }]}>
                    Unsaved Drafts ({filteredDrafts.length})
                  </Text>
                </View>

                {eligibleDrafts.length > 0 && (
                  <View style={{ flexDirection: "row", alignItems: "center", gap: Spacing.sm }}>
                    <Pressable
                      testID="vault-select-all-btn"
                      onPress={handleToggleSelectAll}
                      style={[
                        styles.bulkActionBtn,
                        { borderColor: colors.border, backgroundColor: colors.surfaceSecondary },
                      ]}
                    >
                      <Ionicons
                        name={isAllSelected ? "checkbox" : "square-outline"}
                        size={16}
                        color={isAllSelected ? colors.brandPrimary : colors.muted}
                      />
                      <Text style={[styles.bulkActionText, { color: colors.onSurface }]}>
                        {isAllSelected ? "Deselect All" : "Select All"}
                      </Text>
                    </Pressable>

                    {selectedDraftIds.size > 0 && (
                      <Pressable
                        testID="vault-bulk-delete-btn"
                        onPress={handleBulkDelete}
                        disabled={isBulkDeleting}
                        style={[
                          styles.bulkDeleteBtn,
                          { backgroundColor: colors.error },
                        ]}
                      >
                        {isBulkDeleting ? (
                          <ActivityIndicator size="small" color="#FFFFFF" />
                        ) : (
                          <>
                            <Ionicons name="trash-outline" size={14} color="#FFFFFF" />
                            <Text style={styles.bulkDeleteText}>
                              Delete Selected ({selectedDraftIds.size})
                            </Text>
                          </>
                        )}
                      </Pressable>
                    )}
                  </View>
                )}
              </View>
              {filteredDrafts.map(renderDraftCard)}
            </View>
          )}

          {(activeTab === "all" || activeTab === "documents") && filteredDocs.length > 0 && (
            <View>
              <View style={styles.sectionHeader}>
                <Ionicons name="document-text-outline" size={16} color={colors.brandPrimary} />
                <Text style={[styles.sectionTitle, { color: colors.onSurface }]}>
                  Generated Documents & Downloads ({filteredDocs.length})
                </Text>
              </View>
              {filteredDocs.map(renderDocumentCard)}
            </View>
          )}

          {filteredDocs.length === 0 && filteredDrafts.length === 0 && (
            <View style={styles.emptyState}>
              <Ionicons name="file-tray-outline" size={54} color={colors.muted} />
              <Text style={[styles.emptyTitle, { color: colors.onSurface }]}>
                {searchQuery ? "No matching records found" : "Your Vault is empty"}
              </Text>
              <Text style={[styles.emptySubtitle, { color: colors.muted }]}>
                {searchQuery
                  ? "Try searching for a different keyword or check spelling."
                  : "All documents you generate or draft will automatically appear here for quick access."}
              </Text>
              <Pressable
                testID="vault-goto-templates"
                onPress={() => router.push("/(tabs)/templates")}
                style={[
                  styles.emptyBtn,
                  { backgroundColor: colors.brandPrimary },
                ]}
              >
                <Text style={[styles.emptyBtnText, { color: colors.onBrandPrimary }]}>
                  Explore Templates
                </Text>
              </Pressable>
            </View>
          )}
        </ScrollView>
      )}

      <ConfirmModal
        visible={confirmModal !== null}
        title={confirmModal?.title || ""}
        message={confirmModal?.message || ""}
        confirmLabel={confirmModal?.confirmLabel}
        busy={confirmBusy}
        onCancel={() => {
          if (!confirmBusy) setConfirmModal(null);
        }}
        onConfirm={handleConfirmProceed}
      />
    </View>
  );

  if (isDesktop) {
    return (
      <DesktopPage
        sidebarOffset={false}
        onBack={() => safeBack("/(tabs)/home")}
        title="Document Vault"
        subtitle="Manage generated legal documents, download history, and unfinished drafts"
      >
        {content}
      </DesktopPage>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <View style={[styles.mobileHeader, { borderBottomColor: colors.border }]}>
        <Pressable testID="vault-back" onPress={() => safeBack("/(tabs)/home")} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
        </Pressable>
        <Text style={[styles.mobileTitle, { color: colors.onSurface }]}>Document Vault</Text>
        <View style={{ width: 24 }} />
      </View>
      {content}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  mobileHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: Spacing.md,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  mobileTitle: {
    fontSize: 18,
    fontWeight: "700",
  },
  searchBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: Spacing.md,
    paddingVertical: Platform.OS === "ios" ? 10 : 6,
    borderRadius: Radius.md,
    borderWidth: 1,
    marginBottom: Spacing.sm,
  },
  searchInput: {
    flex: 1,
    fontSize: 14,
    marginLeft: Spacing.sm,
  },
  tabRow: {
    flexDirection: "row",
    gap: Spacing.xs,
    marginBottom: Spacing.sm,
  },
  tabChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: Radius.full,
    borderWidth: 1,
  },
  tabChipText: {
    fontSize: 12,
    fontWeight: "700",
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: Spacing.xs,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  card: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
    marginBottom: Spacing.sm,
  },
  iconBox: {
    width: 44,
    height: 44,
    borderRadius: Radius.md,
    alignItems: "center",
    justifyContent: "center",
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: "700",
  },
  pill: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: Radius.sm,
  },
  pillText: {
    fontSize: 10,
    fontWeight: "800",
  },
  cardMeta: {
    fontSize: 12,
    marginTop: 3,
  },
  cardCase: {
    fontSize: 12,
    fontWeight: "600",
    marginTop: 2,
  },
  actionCol: {
    gap: 6,
    alignItems: "flex-end",
  },
  actionBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: Radius.sm,
    borderWidth: 1,
  },
  actionBtnText: {
    fontSize: 12,
    fontWeight: "700",
  },
  actionBtnSecondary: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: Radius.sm,
    borderWidth: 1,
  },
  actionBtnSecondaryText: {
    fontSize: 12,
    fontWeight: "600",
  },
  actionBtnDanger: {
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: Radius.sm,
    borderWidth: 1,
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 60,
  },
  emptyState: {
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 60,
    paddingHorizontal: Spacing.xl,
  },
  emptyTitle: {
    fontSize: 17,
    fontWeight: "700",
    marginTop: Spacing.md,
  },
  emptySubtitle: {
    fontSize: 13,
    textAlign: "center",
    marginTop: Spacing.xs,
    lineHeight: 18,
    maxWidth: 380,
  },
  emptyBtn: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: 10,
    borderRadius: Radius.md,
    marginTop: Spacing.lg,
  },
  emptyBtnText: {
    fontSize: 14,
    fontWeight: "700",
  },
  bulkActionBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: Radius.sm,
    borderWidth: 1,
  },
  bulkActionText: {
    fontSize: 12,
    fontWeight: "600",
  },
  bulkDeleteBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: Radius.sm,
  },
  bulkDeleteText: {
    color: "#FFFFFF",
    fontSize: 12,
    fontWeight: "700",
  },
  checkboxTouch: {
    marginRight: Spacing.xs,
    justifyContent: "center",
    alignItems: "center",
    padding: 2,
  },
});

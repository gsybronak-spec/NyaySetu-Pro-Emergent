import React from "react";
import {
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTheme } from "@/src/theme/ThemeContext";
import { Radius, Spacing } from "@/src/theme/tokens";

interface LanguageSelectModalProps {
  visible: boolean;
  onClose: () => void;
  onSelect: (lang: "gu" | "en") => void;
  templateNameGu?: string;
  templateNameEn?: string;
  category?: string;
}

export function LanguageSelectModal({
  visible,
  onClose,
  onSelect,
  templateNameGu,
  templateNameEn,
  category,
}: LanguageSelectModalProps) {
  const { colors } = useTheme();

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <Pressable style={styles.overlay} onPress={onClose}>
        <Pressable
          style={[
            styles.modalContainer,
            { backgroundColor: colors.surface, borderColor: colors.border },
          ]}
          onPress={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <View style={styles.header}>
            <View style={{ flex: 1 }}>
              <Text style={[styles.headerTitle, { color: colors.onSurface }]}>
                Select Document Language
              </Text>
              <Text style={[styles.headerSub, { color: colors.muted }]}>
                દસ્તાવેજની ભાષા પસંદ કરો
              </Text>
            </View>
            <Pressable
              testID="close-language-modal"
              onPress={onClose}
              hitSlop={10}
              style={[styles.closeBtn, { backgroundColor: colors.surfaceSecondary }]}
            >
              <Ionicons name="close" size={20} color={colors.muted} />
            </Pressable>
          </View>

          {/* Template Info Preview */}
          {(templateNameGu || templateNameEn) && (
            <View
              style={[
                styles.tplPreview,
                { backgroundColor: colors.surfaceSecondary, borderColor: colors.border },
              ]}
            >
              <View style={[styles.tplIconBadge, { backgroundColor: colors.brandPrimary + "18" }]}>
                <Ionicons name="document-text" size={18} color={colors.brandPrimary} />
              </View>
              <View style={{ flex: 1, marginLeft: Spacing.sm }}>
                {templateNameGu ? (
                  <Text style={[styles.tplGu, { color: colors.onSurface }]} numberOfLines={1}>
                    {templateNameGu}
                  </Text>
                ) : null}
                {templateNameEn ? (
                  <Text style={[styles.tplEn, { color: colors.muted }]} numberOfLines={1}>
                    {templateNameEn} {category ? `• ${category}` : ""}
                  </Text>
                ) : null}
              </View>
            </View>
          )}

          {/* Language Options */}
          <View style={styles.optionsList}>
            {/* Gujarati Option */}
            <Pressable
              testID="select-lang-gu"
              onPress={() => {
                onClose();
                onSelect("gu");
              }}
              style={({ pressed }) => [
                styles.optionCard,
                {
                  borderColor: colors.brandPrimary,
                  backgroundColor: colors.surfaceSecondary,
                },
                pressed && { opacity: 0.85, transform: [{ scale: 0.99 }] },
              ]}
            >
              <View style={[styles.langBadge, { backgroundColor: colors.brandPrimary }]}>
                <Text style={[styles.langBadgeText, { color: colors.onBrandPrimary }]}>ગુ</Text>
              </View>
              <View style={{ flex: 1, marginLeft: Spacing.md }}>
                <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                  <Text style={[styles.optionTitle, { color: colors.onSurface }]}>
                    ગુજરાતી
                  </Text>
                  <Text style={{ fontSize: 13, color: colors.muted }}>(Gujarati)</Text>
                </View>
                <Text style={[styles.optionDesc, { color: colors.muted }]}>
                  ગુજરાતી કોર્ટ અરજી ફોર્મેટ • માન્ય શૈલી
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={colors.brandPrimary} />
            </Pressable>

            {/* English Option */}
            <Pressable
              testID="select-lang-en"
              onPress={() => {
                onClose();
                onSelect("en");
              }}
              style={({ pressed }) => [
                styles.optionCard,
                {
                  borderColor: colors.border,
                  backgroundColor: colors.surfaceSecondary,
                },
                pressed && { opacity: 0.85, transform: [{ scale: 0.99 }] },
              ]}
            >
              <View style={[styles.langBadge, { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border }]}>
                <Text style={[styles.langBadgeText, { color: colors.brandPrimary }]}>EN</Text>
              </View>
              <View style={{ flex: 1, marginLeft: Spacing.md }}>
                <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                  <Text style={[styles.optionTitle, { color: colors.onSurface }]}>
                    English
                  </Text>
                  <Text style={{ fontSize: 13, color: colors.muted }}>(અંગ્રેજી)</Text>
                </View>
                <Text style={[styles.optionDesc, { color: colors.muted }]}>
                  Standard English legal court format
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={colors.muted} />
            </Pressable>
          </View>

          {/* Cancel footer */}
          <Pressable
            testID="cancel-language-modal"
            onPress={onClose}
            style={({ pressed }) => [
              styles.cancelBtn,
              { borderColor: colors.border },
              pressed && { opacity: 0.7 },
            ]}
          >
            <Text style={[styles.cancelBtnText, { color: colors.muted }]}>Cancel / રદ કરો</Text>
          </Pressable>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.55)",
    justifyContent: "center",
    alignItems: "center",
    padding: Spacing.lg,
  },
  modalContainer: {
    width: "100%",
    maxWidth: 460,
    borderRadius: Radius.lg,
    borderWidth: 1,
    padding: Spacing.xl,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.25,
    shadowRadius: 24,
    elevation: 10,
  },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    marginBottom: Spacing.md,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: "700",
    letterSpacing: 0.2,
  },
  headerSub: {
    fontSize: 13,
    marginTop: 2,
  },
  closeBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: "center",
    alignItems: "center",
  },
  tplPreview: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.sm,
    borderRadius: Radius.md,
    borderWidth: 1,
    marginBottom: Spacing.lg,
  },
  tplIconBadge: {
    width: 34,
    height: 34,
    borderRadius: 8,
    justifyContent: "center",
    alignItems: "center",
  },
  tplGu: {
    fontSize: 14,
    fontWeight: "700",
  },
  tplEn: {
    fontSize: 12,
    marginTop: 2,
  },
  optionsList: {
    gap: Spacing.md,
    marginBottom: Spacing.lg,
  },
  optionCard: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1.5,
  },
  langBadge: {
    width: 44,
    height: 44,
    borderRadius: 10,
    justifyContent: "center",
    alignItems: "center",
  },
  langBadgeText: {
    fontSize: 16,
    fontWeight: "800",
  },
  optionTitle: {
    fontSize: 16,
    fontWeight: "700",
  },
  optionDesc: {
    fontSize: 12,
    marginTop: 2,
  },
  cancelBtn: {
    paddingVertical: Spacing.sm,
    borderRadius: Radius.md,
    alignItems: "center",
    justifyContent: "center",
  },
  cancelBtnText: {
    fontSize: 13,
    fontWeight: "600",
  },
});

import React from "react";
import { ActivityIndicator, Modal, Pressable, StyleSheet, Text, View } from "react-native";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAppLanguage } from "@/src/context/AppLanguageContext";
import { Radius, Spacing } from "@/src/theme/tokens";

interface ConfirmModalProps {
  visible: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  busy?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmModal({
  visible,
  title,
  message,
  confirmLabel,
  busy = false,
  onCancel,
  onConfirm,
}: ConfirmModalProps) {
  const { colors } = useTheme();
  const { t } = useAppLanguage();
  const effectiveConfirmLabel = confirmLabel || t("delete");

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={() => {
        if (!busy) onCancel();
      }}
    >
      <View style={styles.backdrop}>
        <View style={[styles.box, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <Text style={[styles.title, { color: colors.onSurface }]}>{title}</Text>
          <Text style={[styles.message, { color: colors.muted }]}>{message}</Text>
          <View style={styles.actions}>
            <Pressable
              testID="confirm-modal-cancel"
              disabled={busy}
              onPress={onCancel}
              style={[styles.btn, { borderColor: colors.border, backgroundColor: colors.surfaceSecondary }]}
            >
              <Text style={{ color: colors.onSurface, fontWeight: "600", fontSize: 13 }}>{t("cancel")}</Text>
            </Pressable>
            <Pressable
              testID="confirm-modal-confirm"
              disabled={busy}
              onPress={onConfirm}
              style={[styles.btn, { borderColor: colors.error, backgroundColor: colors.error }]}
            >
              {busy ? (
                <ActivityIndicator size="small" color="#FFFFFF" />
              ) : (
                <Text style={{ color: "#FFFFFF", fontWeight: "700", fontSize: 13 }}>{effectiveConfirmLabel}</Text>
              )}
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.5)",
    alignItems: "center",
    justifyContent: "center",
    padding: Spacing.lg,
  },
  box: {
    width: "100%",
    maxWidth: 380,
    borderRadius: Radius.lg,
    borderWidth: 1,
    padding: Spacing.lg,
  },
  title: {
    fontSize: 16,
    fontWeight: "700",
    marginBottom: Spacing.xs,
  },
  message: {
    fontSize: 13,
    lineHeight: 19,
    marginBottom: Spacing.lg,
  },
  actions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: Spacing.sm,
  },
  btn: {
    paddingHorizontal: Spacing.md,
    paddingVertical: 9,
    borderRadius: Radius.sm,
    borderWidth: 1,
    minWidth: 82,
    alignItems: "center",
  },
});

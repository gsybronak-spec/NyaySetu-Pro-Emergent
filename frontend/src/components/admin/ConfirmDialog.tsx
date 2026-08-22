import React from "react";
import { Modal, StyleSheet, Text, View, Pressable, ActivityIndicator } from "react-native";
import { Ionicons } from "@expo/vector-icons";

interface ConfirmDialogProps {
  visible: boolean;
  title: string;
  message: string | React.ReactNode;
  impactWarning?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmVariant?: "primary" | "danger" | "warning";
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  children?: React.ReactNode;
}

export function ConfirmDialog({
  visible,
  title,
  message,
  impactWarning,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  confirmVariant = "primary",
  loading = false,
  onConfirm,
  onCancel,
  children,
}: ConfirmDialogProps) {
  if (!visible) return null;

  let btnColor = "#C5A059";
  let btnTextColor = "#061024";
  let iconName: keyof typeof Ionicons.glyphMap = "information-circle-outline";
  let iconColor = "#C5A059";

  if (confirmVariant === "danger") {
    btnColor = "#E53E3E";
    btnTextColor = "#FDFDFD";
    iconName = "alert-circle-outline";
    iconColor = "#E53E3E";
  } else if (confirmVariant === "warning") {
    btnColor = "#D69E2E";
    btnTextColor = "#061024";
    iconName = "warning-outline";
    iconColor = "#ECC94B";
  }

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel}>
      <View style={styles.overlay}>
        <View style={styles.dialog}>
          {/* Header */}
          <View style={styles.header}>
            <View style={[styles.iconBox, { backgroundColor: `${iconColor}1A` }]}>
              <Ionicons name={iconName} size={22} color={iconColor} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.title}>{title}</Text>
            </View>
            <Pressable onPress={onCancel} disabled={loading} style={styles.closeBtn}>
              <Ionicons name="close" size={20} color="#8B96A9" />
            </Pressable>
          </View>

          {/* Body */}
          <View style={styles.body}>
            {typeof message === "string" ? <Text style={styles.message}>{message}</Text> : message}

            {impactWarning ? (
              <View style={styles.impactBox}>
                <Ionicons name="warning" size={16} color="#ECC94B" style={{ marginRight: 8, marginTop: 2 }} />
                <Text style={styles.impactText}>{impactWarning}</Text>
              </View>
            ) : null}

            {children}
          </View>

          {/* Footer Actions */}
          <View style={styles.footer}>
            <Pressable
              disabled={loading}
              onPress={onCancel}
              style={({ pressed }) => [styles.cancelBtn, pressed && { opacity: 0.8 }]}
            >
              <Text style={styles.cancelBtnText}>{cancelLabel}</Text>
            </Pressable>

            <Pressable
              disabled={loading}
              onPress={onConfirm}
              style={({ pressed }) => [
                styles.confirmBtn,
                { backgroundColor: btnColor },
                pressed && { opacity: 0.85 },
                loading && { opacity: 0.7 },
              ]}
            >
              {loading ? (
                <ActivityIndicator size="small" color={btnTextColor} style={{ marginRight: 8 }} />
              ) : null}
              <Text style={[styles.confirmBtnText, { color: btnTextColor }]}>{confirmLabel}</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(6, 16, 36, 0.85)",
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
  },
  dialog: {
    backgroundColor: "#12203B",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#253452",
    width: "100%",
    maxWidth: 500,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.5,
    shadowRadius: 20,
    elevation: 10,
    overflow: "hidden",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    padding: 18,
    borderBottomWidth: 1,
    borderBottomColor: "#1B2A49",
  },
  iconBox: {
    width: 38,
    height: 38,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  title: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FDFDFD",
  },
  closeBtn: {
    padding: 4,
  },
  body: {
    padding: 20,
  },
  message: {
    fontSize: 14,
    color: "#D1D8E5",
    lineHeight: 22,
  },
  impactBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    backgroundColor: "rgba(236, 201, 75, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(236, 201, 75, 0.3)",
    borderRadius: 8,
    padding: 12,
    marginTop: 16,
  },
  impactText: {
    flex: 1,
    fontSize: 12,
    color: "#ECC94B",
    lineHeight: 18,
    fontWeight: "500",
  },
  footer: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "flex-end",
    padding: 16,
    backgroundColor: "#0D182E",
    borderTopWidth: 1,
    borderTopColor: "#1B2A49",
    gap: 10,
  },
  cancelBtn: {
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 8,
    backgroundColor: "#1B2A49",
    borderWidth: 1,
    borderColor: "#253452",
  },
  cancelBtnText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#D1D8E5",
  },
  confirmBtn: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 18,
    paddingVertical: 9,
    borderRadius: 8,
  },
  confirmBtnText: {
    fontSize: 13,
    fontWeight: "700",
  },
});

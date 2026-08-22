import React from "react";
import { ActivityIndicator, StyleSheet, Text, View, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";

interface AdminEmptyStateProps {
  title?: string;
  description?: string;
  icon?: keyof typeof Ionicons.glyphMap;
  actionLabel?: string;
  onAction?: () => void;
}

export function AdminEmptyState({
  title = "No records found",
  description = "There are no entries matching your current search or filters.",
  icon = "file-tray-outline",
  actionLabel,
  onAction,
}: AdminEmptyStateProps) {
  return (
    <View style={styles.emptyContainer}>
      <View style={styles.emptyIconCircle}>
        <Ionicons name={icon} size={32} color="#8B96A9" />
      </View>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.emptyDesc}>{description}</Text>
      {actionLabel && onAction ? (
        <Pressable onPress={onAction} style={styles.actionBtn}>
          <Text style={styles.actionBtnText}>{actionLabel}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

interface AdminLoadingStateProps {
  message?: string;
}

export function AdminLoadingState({ message = "Loading records..." }: AdminLoadingStateProps) {
  return (
    <View style={styles.loadingContainer}>
      <ActivityIndicator size="large" color="#C5A059" />
      <Text style={styles.loadingText}>{message}</Text>
    </View>
  );
}

interface AdminErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export function AdminErrorState({
  message = "An error occurred while communicating with the Admin API.",
  onRetry,
}: AdminErrorStateProps) {
  return (
    <View style={styles.errorContainer}>
      <Ionicons name="alert-circle-outline" size={36} color="#E53E3E" style={{ marginBottom: 10 }} />
      <Text style={styles.errorTitle}>Failed to Load Data</Text>
      <Text style={styles.errorDesc}>{message}</Text>
      {onRetry ? (
        <Pressable onPress={onRetry} style={styles.retryBtn}>
          <Ionicons name="refresh" size={14} color="#FDFDFD" style={{ marginRight: 6 }} />
          <Text style={styles.retryBtnText}>Try Again</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  emptyContainer: {
    padding: 48,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 280,
  },
  emptyIconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "#1B2A49",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FDFDFD",
    marginBottom: 6,
  },
  emptyDesc: {
    fontSize: 13,
    color: "#8B96A9",
    textAlign: "center",
    maxWidth: 380,
    lineHeight: 20,
  },
  actionBtn: {
    marginTop: 16,
    backgroundColor: "#1B2A49",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#C5A059",
  },
  actionBtnText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#C5A059",
  },
  loadingContainer: {
    padding: 48,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 280,
  },
  loadingText: {
    marginTop: 14,
    fontSize: 13,
    color: "#8B96A9",
    fontWeight: "500",
  },
  errorContainer: {
    padding: 40,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 280,
    backgroundColor: "rgba(163, 42, 42, 0.08)",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "rgba(229, 62, 62, 0.2)",
    margin: 16,
  },
  errorTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#F56565",
    marginBottom: 6,
  },
  errorDesc: {
    fontSize: 13,
    color: "#D1D8E5",
    textAlign: "center",
    maxWidth: 420,
    lineHeight: 20,
    marginBottom: 16,
  },
  retryBtn: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#E53E3E",
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 8,
  },
  retryBtnText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#FDFDFD",
  },
});

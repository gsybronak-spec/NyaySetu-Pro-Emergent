import React from "react";
import { StyleSheet, Text, View, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

interface Breadcrumb {
  label: string;
  route?: string;
}

interface AdminPageHeaderProps {
  title: string;
  subtitle?: string;
  breadcrumbs?: Breadcrumb[];
  actionLabel?: string;
  actionIcon?: keyof typeof Ionicons.glyphMap;
  onAction?: () => void;
  secondaryActionLabel?: string;
  onSecondaryAction?: () => void;
}

export function AdminPageHeader({
  title,
  subtitle,
  breadcrumbs,
  actionLabel,
  actionIcon,
  onAction,
  secondaryActionLabel,
  onSecondaryAction,
}: AdminPageHeaderProps) {
  return (
    <View style={styles.container}>
      {/* Breadcrumbs */}
      {breadcrumbs && breadcrumbs.length > 0 ? (
        <View style={styles.breadcrumbs}>
          <Pressable onPress={() => router.push("/admin/dashboard" as any)}>
            <Text style={styles.breadcrumbLink}>Admin</Text>
          </Pressable>
          {breadcrumbs.map((b, i) => (
            <React.Fragment key={i}>
              <Ionicons name="chevron-forward" size={12} color="#6B7280" style={{ marginHorizontal: 4 }} />
              {b.route ? (
                <Pressable onPress={() => router.push(b.route as any)}>
                  <Text style={styles.breadcrumbLink}>{b.label}</Text>
                </Pressable>
              ) : (
                <Text style={styles.breadcrumbCurrent}>{b.label}</Text>
              )}
            </React.Fragment>
          ))}
        </View>
      ) : null}

      {/* Main Title Row */}
      <View style={styles.titleRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>{title}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>

        {/* Actions */}
        <View style={styles.actions}>
          {secondaryActionLabel && onSecondaryAction ? (
            <Pressable
              onPress={onSecondaryAction}
              style={({ pressed }) => [styles.secondaryBtn, pressed && { opacity: 0.8 }]}
            >
              <Text style={styles.secondaryBtnText}>{secondaryActionLabel}</Text>
            </Pressable>
          ) : null}

          {actionLabel && onAction ? (
            <Pressable
              onPress={onAction}
              style={({ pressed }) => [styles.primaryBtn, pressed && { opacity: 0.85 }]}
            >
              {actionIcon ? (
                <Ionicons name={actionIcon} size={16} color="#061024" style={{ marginRight: 6 }} />
              ) : null}
              <Text style={styles.primaryBtnText}>{actionLabel}</Text>
            </Pressable>
          ) : null}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 20,
  },
  breadcrumbs: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  breadcrumbLink: {
    fontSize: 12,
    color: "#C5A059",
    fontWeight: "500",
  },
  breadcrumbCurrent: {
    fontSize: 12,
    color: "#8B96A9",
    fontWeight: "500",
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: 12,
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: "#FDFDFD",
    letterSpacing: -0.3,
  },
  subtitle: {
    fontSize: 13,
    color: "#8B96A9",
    marginTop: 4,
  },
  actions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  primaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#C5A059",
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 8,
  },
  primaryBtnText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#061024",
  },
  secondaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#1B2A49",
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#253452",
  },
  secondaryBtnText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#D1D8E5",
  },
});

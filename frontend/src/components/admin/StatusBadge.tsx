import React from "react";
import { StyleSheet, Text, View, ViewStyle } from "react-native";

interface StatusBadgeProps {
  status?: string | boolean | null;
  label?: string;
  size?: "sm" | "md";
  style?: ViewStyle;
}

export function StatusBadge({ status, label, size = "md", style }: StatusBadgeProps) {
  const norm = String(status ?? "").toLowerCase().trim();

  let bg = "#1B2A49";
  let text = "#A6B1C2";
  let border = "#253452";
  let displayLabel = label || norm;

  if (norm === "active" || norm === "published" || norm === "success" || norm === "true" || norm === "verified") {
    bg = "rgba(45, 92, 48, 0.25)";
    text = "#48BB78";
    border = "rgba(72, 187, 120, 0.4)";
    displayLabel = label || (norm === "true" ? "Active" : norm.toUpperCase());
  } else if (norm === "suspended" || norm === "draft" || norm === "pending" || norm === "seed") {
    bg = "rgba(197, 160, 89, 0.2)";
    text = "#ECC94B";
    border = "rgba(236, 201, 75, 0.4)";
    displayLabel = label || (norm === "seed" ? "SEED" : norm.toUpperCase());
  } else if (norm === "banned" || norm === "archived" || norm === "failed" || norm === "false" || norm === "disabled") {
    bg = "rgba(163, 42, 42, 0.25)";
    text = "#F56565";
    border = "rgba(245, 101, 101, 0.4)";
    displayLabel = label || (norm === "false" ? "Inactive" : norm.toUpperCase());
  } else if (norm === "admin_adjustment" || norm === "purchase") {
    bg = "rgba(66, 153, 225, 0.2)";
    text = "#63B3ED";
    border = "rgba(99, 179, 237, 0.4)";
    displayLabel = label || norm.replace("_", " ").toUpperCase();
  }

  const isSmall = size === "sm";

  return (
    <View
      style={[
        styles.badge,
        { backgroundColor: bg, borderColor: border },
        isSmall && styles.badgeSm,
        style,
      ]}
    >
      <View style={[styles.dot, { backgroundColor: text }]} />
      <Text style={[styles.text, { color: text }, isSmall && styles.textSm]}>
        {displayLabel}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1,
    alignSelf: "flex-start",
  },
  badgeSm: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 6,
  },
  text: {
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.4,
  },
  textSm: {
    fontSize: 10,
    fontWeight: "600",
  },
});

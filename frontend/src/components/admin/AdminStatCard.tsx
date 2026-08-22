import React from "react";
import { Pressable, StyleSheet, Text, View, ViewStyle } from "react-native";
import { Ionicons } from "@expo/vector-icons";

interface AdminStatCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  icon: keyof typeof Ionicons.glyphMap;
  color?: string;
  onPress?: () => void;
  style?: ViewStyle;
}

export function AdminStatCard({
  label,
  value,
  subtitle,
  icon,
  color = "#C5A059",
  onPress,
  style,
}: AdminStatCardProps) {
  const content = (
    <View style={[styles.card, style]}>
      <View style={styles.headerRow}>
        <Text style={styles.label} numberOfLines={1}>
          {label}
        </Text>
        <View style={[styles.iconContainer, { backgroundColor: `${color}1A` }]}>
          <Ionicons name={icon} size={20} color={color} />
        </View>
      </View>
      <Text style={styles.value}>{value}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );

  if (onPress) {
    return (
      <Pressable
        onPress={onPress}
        style={({ pressed }) => [{ flex: 1, minWidth: 200 }, pressed && { opacity: 0.85 }]}
      >
        {content}
      </Pressable>
    );
  }

  return <View style={{ flex: 1, minWidth: 200 }}>{content}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#12203B",
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: "#253452",
    minHeight: 110,
    justifyContent: "space-between",
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: "#A6B1C2",
    letterSpacing: 0.3,
    flex: 1,
  },
  iconContainer: {
    width: 36,
    height: 36,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    marginLeft: 8,
  },
  value: {
    fontSize: 24,
    fontWeight: "700",
    color: "#FDFDFD",
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 12,
    color: "#6B7280",
    fontWeight: "500",
  },
});

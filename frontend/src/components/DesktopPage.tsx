import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";

import { useTheme } from "@/src/theme/ThemeContext";
import { Spacing } from "@/src/theme/tokens";

import { NotificationCenter } from "./NotificationCenter";

/** Fixed width of the desktop sidebar — DesktopPage offsets content by it. */
export const DESKTOP_SIDEBAR_WIDTH = 264;

interface Props {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  maxWidth?: number;
  /** Disable the outer scroll (when the screen manages its own scrolling). */
  scroll?: boolean;
  /** Stack screens (case detail, application form) have no sidebar — no left offset. */
  sidebarOffset?: boolean;
  /** Optional back handler for desktop screens outside the sidebar tabs. */
  onBack?: () => void;
}

/**
 * Desktop screen scaffold: full-height surface offset by the fixed sidebar,
 * with a consistent page header (title + actions) and a centered scrollable
 * content column. Mobile screens do NOT use this — they keep their app-like
 * SafeAreaView layout.
 */
export function DesktopPage({ title, subtitle, actions, children, maxWidth = 1200, scroll = true, sidebarOffset = true, onBack }: Props) {
  const { colors } = useTheme();

  const header = (
    <View style={[styles.header, { borderBottomColor: colors.border, backgroundColor: colors.surface }]}>
      <View style={styles.headerInner}>
        {onBack ? (
          <Pressable
            testID="desktop-page-back"
            onPress={onBack}
            hitSlop={10}
            style={({ pressed }: any) => [
              styles.backBtn,
              { backgroundColor: colors.surfaceSecondary, borderColor: colors.border, opacity: pressed ? 0.8 : 1 },
            ]}
          >
            <Ionicons name="arrow-back" size={18} color={colors.onSurface} />
          </Pressable>
        ) : null}
        <View style={{ flex: 1, minWidth: 200, paddingRight: Spacing.lg }}>
          <Text style={[styles.title, { color: colors.onSurface }]} numberOfLines={2}>{title}</Text>
          {subtitle ? (
            <Text style={{ color: colors.muted, fontSize: 13, marginTop: 2 }} numberOfLines={2}>{subtitle}</Text>
          ) : null}
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
          <NotificationCenter />
          {actions ? <View style={styles.actions}>{actions}</View> : null}
        </View>
      </View>
    </View>
  );

  const body = (
    <View style={[styles.content, { maxWidth, width: "100%" }]}>{children}</View>
  );

  return (
    <View style={[styles.root, { backgroundColor: colors.surface, paddingLeft: sidebarOffset ? DESKTOP_SIDEBAR_WIDTH : 0 }]}>
      {header}
      {scroll ? (
        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={{ alignItems: "center", paddingHorizontal: Spacing.xl, paddingVertical: Spacing.xl, paddingBottom: Spacing.xxxl }}
        >
          {body}
        </ScrollView>
      ) : (
        <View style={[styles.noScroll, { alignItems: "center", paddingHorizontal: Spacing.xl }]}>{body}</View>
      )}
    </View>
  );
}

/** Small stat card used on the desktop dashboard. */
export function StatCard({
  label,
  value,
  icon,
  tone,
  onPress,
  testID,
}: {
  label: string;
  value: string | number;
  icon: keyof typeof Ionicons.glyphMap;
  tone?: "gold" | "navy" | "red" | "green";
  onPress?: () => void;
  testID?: string;
}) {
  const { colors, isDark } = useTheme();
  const iconColor =
    tone === "gold" ? "#C5A059" : tone === "red" ? "#B3261E" : tone === "green" ? "#1B7F4D" : isDark ? "#A6B1C2" : "#1D2D50";

  const cardContent = (
    <>
      <View style={[styles.statIcon, { backgroundColor: iconColor + "1A" }]}>
        <Ionicons name={icon} size={20} color={iconColor} />
      </View>
      <View style={{ marginLeft: Spacing.md, flex: 1 }}>
        <Text style={[styles.statValue, { color: colors.onSurface }]}>{value}</Text>
        <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }} numberOfLines={1}>
          {label}
        </Text>
      </View>
    </>
  );

  if (onPress) {
    return (
      <Pressable
        testID={testID}
        onPress={onPress}
        style={({ pressed }: any) => [
          styles.stat,
          {
            backgroundColor: isDark ? colors.surfaceSecondary : "#FFFFFF",
            borderColor: colors.border,
            opacity: pressed ? 0.85 : 1,
            cursor: "pointer",
          },
        ]}
      >
        {cardContent}
      </Pressable>
    );
  }

  return (
    <View
      style={[
        styles.stat,
        { backgroundColor: isDark ? colors.surfaceSecondary : "#FFFFFF", borderColor: colors.border },
      ]}
    >
      {cardContent}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  header: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.lg,
  },
  headerInner: {
    flexDirection: "row",
    alignItems: "center",
    maxWidth: 1200,
    width: "100%",
    alignSelf: "center",
  },
  title: { fontSize: 24, fontWeight: "800", fontFamily: "serif" },
  backBtn: {
    width: 38,
    height: 38,
    borderRadius: 10,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    marginRight: Spacing.md,
  },
  actions: { flexDirection: "row", alignItems: "center", gap: Spacing.md, flexShrink: 1, minWidth: 0, flexWrap: "wrap" },
  content: { gap: Spacing.lg },
  noScroll: { flex: 1, paddingBottom: Spacing.xxxl },
  stat: {
    flex: 1,
    minWidth: 200,
    minHeight: 88,
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.lg,
    borderRadius: 14,
    borderWidth: 1,
  },
  statIcon: { width: 44, height: 44, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  statValue: { fontSize: 24, fontWeight: "800", fontFamily: "serif" },
});

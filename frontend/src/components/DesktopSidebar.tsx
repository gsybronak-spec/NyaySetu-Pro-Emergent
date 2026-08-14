import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { BottomTabBarProps } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { formatAdvocateName } from "@/src/utils/advocate";
import { DESKTOP_SIDEBAR_WIDTH } from "@/src/components/DesktopPage";

const NAV_ITEMS: { route: string; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { route: "home", label: "Home", icon: "home" },
  { route: "cases", label: "My Cases", icon: "folder-open" },
  { route: "templates", label: "Templates", icon: "document-text" },
  { route: "subscription", label: "Plans & Wallet", icon: "diamond" },
  { route: "profile", label: "Profile", icon: "person-circle" },
];

/**
 * Desktop navigation rail (web >= 1024px only). Replaces the mobile bottom
 * tab bar — the screens below are exactly the same tab routes, so desktop and
 * mobile share every screen and all backend logic.
 */
export function DesktopSidebar({ state, navigation }: BottomTabBarProps) {
  const { colors } = useTheme();
  const { user, signOut } = useAuth();

  const activeRoute = state.routes[state.index]?.name;

  const go = (route: string) => {
    navigation.navigate(route);
  };

  return (
    <View style={[styles.rail, { backgroundColor: "#0B1B3D" }]}>
      {/* Brand */}
      <View style={styles.brand}>
        <View style={styles.brandBadge}>
          <Ionicons name="scale" size={18} color="#C5A059" />
        </View>
        <View>
          <Text style={styles.brandName}>
            NyaySetu <Text style={{ color: "#C5A059" }}>Pro</Text>
          </Text>
          <Text style={styles.brandTag}>Legal Workspace</Text>
        </View>
      </View>

      {/* New Case CTA */}
      <Pressable
        testID="desktop-new-case"
        onPress={() => router.push("/case/new")}
        style={({ pressed }) => [styles.cta, pressed && { opacity: 0.85 }]}
      >
        <Ionicons name="add" size={18} color="#0B1B3D" />
        <Text style={styles.ctaText}>New Case</Text>
      </Pressable>

      {/* Nav */}
      <View style={styles.nav}>
        {NAV_ITEMS.map((item) => {
          const active = activeRoute === item.route;
          return (
            <Pressable
              key={item.route}
              testID={`desktop-nav-${item.route}`}
              onPress={() => go(item.route)}
              style={({ pressed }) => [
                styles.navItem,
                active && { backgroundColor: "rgba(197,160,89,0.16)", borderLeftColor: "#C5A059" },
                pressed && { opacity: 0.8 },
              ]}
            >
              <Ionicons name={item.icon} size={19} color={active ? "#C5A059" : "#A6B1C2"} />
              <Text style={[styles.navLabel, { color: active ? "#FDFDFD" : "#A6B1C2" }]}>{item.label}</Text>
              {active ? <View style={styles.activeDot} /> : null}
            </Pressable>
          );
        })}

        <Pressable
          testID="desktop-nav-search"
          onPress={() => router.push("/search")}
          style={({ pressed }) => [styles.navItem, pressed && { opacity: 0.8 }]}
        >
          <Ionicons name="search" size={19} color={"#A6B1C2"} />
          <Text style={[styles.navLabel, { color: "#A6B1C2" }]}>Search</Text>
        </Pressable>
      </View>

      {/* User footer */}
      <View style={[styles.footer, { borderTopColor: "rgba(255,255,255,0.08)" }]}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{(user?.name || user?.mobile || "A").charAt(0).toUpperCase()}</Text>
        </View>
        <View style={{ flex: 1, marginLeft: 10, minWidth: 0 }}>
          <Text style={styles.userName} numberOfLines={1}>
            {formatAdvocateName(user?.name) || "Advocate"}
          </Text>
          <Text style={styles.userMobile} numberOfLines={1}>
            +91 {user?.mobile}
          </Text>
        </View>
        <Pressable
          testID="desktop-signout"
          onPress={() => {
            if (typeof window !== "undefined" && window.confirm("Sign out? You will need to login again to continue.")) {
              signOut().then(() => router.replace("/(auth)/login")).catch(() => router.replace("/(auth)/login"));
            }
          }}
          hitSlop={10}
        >
          <Ionicons name="log-out-outline" size={19} color="#A6B1C2" />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  rail: {
    position: "fixed",
    left: 0,
    top: 0,
    bottom: 0,
    width: DESKTOP_SIDEBAR_WIDTH,
    paddingVertical: 24,
    paddingHorizontal: 16,
    zIndex: 100,
  },
  brand: { flexDirection: "row", alignItems: "center", paddingHorizontal: 8, marginBottom: 24 },
  brandBadge: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: "rgba(197,160,89,0.15)",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 10,
  },
  brandName: { color: "#FDFDFD", fontSize: 17, fontWeight: "800", fontFamily: "serif" },
  brandTag: { color: "#8B96A9", fontSize: 11, marginTop: 1, letterSpacing: 0.3 },
  cta: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#C5A059",
    borderRadius: 12,
    paddingVertical: 12,
    gap: 6,
    marginBottom: 20,
  },
  ctaText: { color: "#0B1B3D", fontWeight: "800", fontSize: 14 },
  nav: { flex: 1, gap: 2 },
  navItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 11,
    paddingHorizontal: 12,
    borderRadius: 10,
    borderLeftWidth: 3,
    borderLeftColor: "transparent",
    gap: 12,
  },
  navLabel: { fontSize: 14, fontWeight: "600", flex: 1 },
  activeDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: "#C5A059" },
  footer: {
    flexDirection: "row",
    alignItems: "center",
    paddingTop: 16,
    borderTopWidth: 1,
    paddingHorizontal: 8,
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#C5A059",
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { color: "#0B1B3D", fontWeight: "800", fontSize: 16 },
  userName: { color: "#FDFDFD", fontSize: 13, fontWeight: "700" },
  userMobile: { color: "#8B96A9", fontSize: 11, marginTop: 1 },
});

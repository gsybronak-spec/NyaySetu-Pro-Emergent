import React from "react";
import { StyleSheet, Text, View, Pressable, ScrollView, Platform } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { router, usePathname } from "expo-router";
import { useAdminAuth } from "@/src/context/AdminAuthContext";

export const ADMIN_SIDEBAR_WIDTH = 260;

export interface NavItem {
  key: string;
  label: string;
  route: string;
  icon: keyof typeof Ionicons.glyphMap;
  badge?: string | number;
}

export const ADMIN_NAV_ITEMS: NavItem[] = [
  { key: "dashboard", label: "Dashboard", route: "/admin/dashboard", icon: "grid-outline" },
  { key: "users", label: "Users", route: "/admin/users", icon: "people-outline" },
  { key: "cases", label: "Cases", route: "/admin/cases", icon: "briefcase-outline" },
  { key: "applications", label: "Applications", route: "/admin/applications", icon: "document-text-outline" },
  { key: "templates", label: "Templates", route: "/admin/templates", icon: "copy-outline" },
  { key: "catalogs", label: "Catalogs", route: "/admin/catalogs", icon: "library-outline" },
  { key: "plans", label: "Plans & Credits", route: "/admin/plans", icon: "card-outline" },
  { key: "audit-logs", label: "Audit Logs", route: "/admin/audit-logs", icon: "shield-checkmark-outline" },
  { key: "settings", label: "System Settings", route: "/admin/settings", icon: "settings-outline" },
];

interface AdminSidebarProps {
  onCloseMobileDrawer?: () => void;
  isMobileDrawer?: boolean;
}

export function AdminSidebar({ onCloseMobileDrawer, isMobileDrawer = false }: AdminSidebarProps) {
  const { adminUser, signOut } = useAdminAuth();
  const pathname = usePathname();

  const handleNavigate = (route: string) => {
    onCloseMobileDrawer?.();
    router.push(route as any);
  };

  const handleSignOut = async () => {
    if (
      typeof window !== "undefined" &&
      !window.confirm("Are you sure you want to sign out of the Super Admin Control Center?")
    ) {
      return;
    }
    await signOut();
    router.replace("/admin" as any);
  };

  const isCurrentActive = (route: string) => {
    if (route === "/admin/dashboard" && (pathname === "/admin" || pathname === "/admin/" || pathname === "/admin/dashboard" || pathname === "/admin/dashboard/")) {
      return true;
    }
    return pathname.startsWith(route);
  };

  return (
    <View style={[styles.container, isMobileDrawer && styles.containerMobile]}>
      {/* Brand Header */}
      <View style={styles.brandHeader}>
        <View style={styles.brandBadge}>
          <Ionicons name="shield-half-outline" size={22} color="#C5A059" />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.brandTitle}>
            NyaySetu <Text style={{ color: "#C5A059" }}>Pro</Text>
          </Text>
          <View style={styles.roleBadge}>
            <View style={styles.roleDot} />
            <Text style={styles.roleText}>SUPER ADMIN</Text>
          </View>
        </View>
        {isMobileDrawer && (
          <Pressable onPress={onCloseMobileDrawer} style={styles.closeDrawerBtn}>
            <Ionicons name="close" size={22} color="#8B96A9" />
          </Pressable>
        )}
      </View>

      {/* Navigation Links */}
      <ScrollView style={styles.navScrollView} showsVerticalScrollIndicator={false}>
        <Text style={styles.sectionLabel}>CONTROL CENTER</Text>
        <View style={styles.navGroup}>
          {ADMIN_NAV_ITEMS.map((item) => {
            const active = isCurrentActive(item.route);
            return (
              <Pressable
                key={item.key}
                onPress={() => handleNavigate(item.route)}
                style={({ pressed }) => [
                  styles.navItem,
                  active && styles.navItemActive,
                  pressed && { opacity: 0.8 },
                ]}
              >
                <Ionicons
                  name={item.icon}
                  size={19}
                  color={active ? "#C5A059" : "#8B96A9"}
                  style={styles.navIcon}
                />
                <Text style={[styles.navText, active && styles.navTextActive]}>
                  {item.label}
                </Text>
                {active ? <View style={styles.activeBar} /> : null}
              </Pressable>
            );
          })}
        </View>

        <View style={styles.divider} />

        <Text style={styles.sectionLabel}>EXTERNAL SHORTCUTS</Text>
        <Pressable
          onPress={() => {
            onCloseMobileDrawer?.();
            router.push("/(tabs)/home" as any);
          }}
          style={({ pressed }) => [styles.navItem, pressed && { opacity: 0.8 }]}
        >
          <Ionicons name="open-outline" size={18} color="#8B96A9" style={styles.navIcon} />
          <Text style={styles.navText}>Lawyer Portal</Text>
        </Pressable>
      </ScrollView>

      {/* Admin User Footer */}
      <View style={styles.footer}>
        <View style={styles.adminAvatar}>
          <Text style={styles.adminAvatarText}>
            {(adminUser?.name || adminUser?.email || "A").charAt(0).toUpperCase()}
          </Text>
        </View>
        <View style={styles.adminMeta}>
          <Text style={styles.adminName} numberOfLines={1}>
            {adminUser?.name || "Super Admin"}
          </Text>
          <Text style={styles.adminEmail} numberOfLines={1}>
            {adminUser?.email || "admin@nyaysetu.gov.in"}
          </Text>
        </View>
        <Pressable
          onPress={handleSignOut}
          style={({ pressed }) => [styles.signOutBtn, pressed && { opacity: 0.7 }]}
          hitSlop={10}
        >
          <Ionicons name="log-out-outline" size={20} color="#E53E3E" />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: ADMIN_SIDEBAR_WIDTH,
    backgroundColor: "#0B1B3D",
    borderRightWidth: 1,
    borderRightColor: "#1B2A49",
    flexDirection: "column",
    justifyContent: "space-between",
    height: "100%",
    ...(Platform.OS === "web"
      ? {
          position: "fixed" as any,
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
        }
      : {}),
  },
  containerMobile: {
    position: "relative" as any,
    width: "100%",
    height: "100%",
    borderRightWidth: 0,
  },
  brandHeader: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 18,
    paddingVertical: 20,
    borderBottomWidth: 1,
    borderBottomColor: "#162544",
  },
  brandBadge: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: "rgba(197, 160, 89, 0.15)",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  brandTitle: {
    fontSize: 17,
    fontWeight: "800",
    color: "#FDFDFD",
    fontFamily: "serif",
    letterSpacing: -0.3,
  },
  roleBadge: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 3,
    alignSelf: "flex-start",
    backgroundColor: "rgba(197, 160, 89, 0.12)",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  roleDot: {
    width: 5,
    height: 5,
    borderRadius: 3,
    backgroundColor: "#C5A059",
    marginRight: 5,
  },
  roleText: {
    fontSize: 9,
    fontWeight: "800",
    color: "#C5A059",
    letterSpacing: 0.8,
  },
  closeDrawerBtn: {
    padding: 6,
  },
  navScrollView: {
    flex: 1,
    paddingHorizontal: 12,
    paddingVertical: 16,
  },
  sectionLabel: {
    fontSize: 10,
    fontWeight: "800",
    color: "#5B6882",
    letterSpacing: 1,
    marginBottom: 8,
    paddingHorizontal: 10,
  },
  navGroup: {
    gap: 3,
    marginBottom: 16,
  },
  navItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    position: "relative",
  },
  navItemActive: {
    backgroundColor: "rgba(197, 160, 89, 0.12)",
  },
  navIcon: {
    marginRight: 12,
  },
  navText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#8B96A9",
    flex: 1,
  },
  navTextActive: {
    color: "#FDFDFD",
    fontWeight: "700",
  },
  activeBar: {
    width: 4,
    height: 18,
    borderRadius: 2,
    backgroundColor: "#C5A059",
    position: "absolute",
    right: 8,
  },
  divider: {
    height: 1,
    backgroundColor: "#162544",
    marginVertical: 12,
    marginHorizontal: 8,
  },
  footer: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 16,
    borderTopWidth: 1,
    borderTopColor: "#162544",
    backgroundColor: "#08142D",
  },
  adminAvatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#C5A059",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 10,
  },
  adminAvatarText: {
    fontSize: 15,
    fontWeight: "800",
    color: "#061024",
  },
  adminMeta: {
    flex: 1,
    minWidth: 0,
    marginRight: 8,
  },
  adminName: {
    fontSize: 13,
    fontWeight: "700",
    color: "#FDFDFD",
  },
  adminEmail: {
    fontSize: 11,
    color: "#8B96A9",
    marginTop: 2,
  },
  signOutBtn: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: "rgba(229, 62, 62, 0.1)",
  },
});

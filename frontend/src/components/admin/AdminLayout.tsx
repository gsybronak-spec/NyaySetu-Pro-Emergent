import React, { useState } from "react";
import { StyleSheet, View, Text, Pressable, ScrollView, Modal, Platform } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { AdminGuard } from "./AdminGuard";
import { AdminSidebar, ADMIN_SIDEBAR_WIDTH } from "./AdminSidebar";
import { useResponsive } from "@/src/hooks/useResponsive";
import { useAdminAuth } from "@/src/context/AdminAuthContext";

interface AdminLayoutProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  scroll?: boolean;
}

export function AdminLayout({
  children,
  title,
  subtitle,
  actions,
  scroll = true,
}: AdminLayoutProps) {
  const { isDesktop } = useResponsive();
  const { adminUser } = useAdminAuth();
  const [mobileDrawerVisible, setMobileDrawerVisible] = useState(false);

  return (
    <AdminGuard>
      <View style={styles.root}>
        {/* Desktop Fixed Sidebar */}
        {isDesktop && <AdminSidebar />}

        {/* Mobile/Tablet Drawer Modal */}
        {!isDesktop && (
          <Modal
            visible={mobileDrawerVisible}
            animationType="slide"
            transparent={true}
            onRequestClose={() => setMobileDrawerVisible(false)}
          >
            <View style={styles.drawerOverlay}>
              <Pressable
                style={styles.drawerBackdrop}
                onPress={() => setMobileDrawerVisible(false)}
              />
              <View style={styles.drawerSheet}>
                <AdminSidebar
                  isMobileDrawer={true}
                  onCloseMobileDrawer={() => setMobileDrawerVisible(false)}
                />
              </View>
            </View>
          </Modal>
        )}

        {/* Main Content Area */}
        <View style={[styles.mainArea, isDesktop && { marginLeft: ADMIN_SIDEBAR_WIDTH }]}>
          {/* Top Admin Navigation / Mobile Header */}
          <View style={styles.topHeader}>
            <View style={styles.topHeaderLeft}>
              {!isDesktop && (
                <Pressable
                  onPress={() => setMobileDrawerVisible(true)}
                  style={styles.hamburgerBtn}
                >
                  <Ionicons name="menu" size={24} color="#FDFDFD" />
                </Pressable>
              )}
              <View>
                {title ? <Text style={styles.headerTitle}>{title}</Text> : null}
                {subtitle ? <Text style={styles.headerSubtitle}>{subtitle}</Text> : null}
              </View>
            </View>

            <View style={styles.topHeaderRight}>
              {actions ? <View style={styles.actionsBox}>{actions}</View> : null}
              <View style={styles.adminIndicator}>
                <View style={styles.adminIndicatorDot} />
                <Text style={styles.adminIndicatorText}>
                  {adminUser?.name?.split(" ")[0] || "Admin"}
                </Text>
              </View>
            </View>
          </View>

          {/* Page Body */}
          {scroll ? (
            <ScrollView
              style={styles.scrollBody}
              contentContainerStyle={styles.scrollBodyInner}
              showsVerticalScrollIndicator={true}
            >
              {children}
            </ScrollView>
          ) : (
            <View style={styles.fixedBody}>{children}</View>
          )}
        </View>
      </View>
    </AdminGuard>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#061024",
    minHeight: "100%",
  },
  mainArea: {
    flex: 1,
    backgroundColor: "#061024",
    minHeight: "100%",
  },
  topHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#0B1B3D",
    borderBottomWidth: 1,
    borderBottomColor: "#1B2A49",
    paddingHorizontal: 24,
    paddingVertical: 14,
    minHeight: 64,
  },
  topHeaderLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    flex: 1,
  },
  hamburgerBtn: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: "#12203B",
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#FDFDFD",
  },
  headerSubtitle: {
    fontSize: 12,
    color: "#8B96A9",
    marginTop: 2,
  },
  topHeaderRight: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
  },
  actionsBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  adminIndicator: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#12203B",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#253452",
  },
  adminIndicatorDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#48BB78",
    marginRight: 6,
  },
  adminIndicatorText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#D1D8E5",
  },
  scrollBody: {
    flex: 1,
  },
  scrollBodyInner: {
    padding: 24,
    maxWidth: 1400,
    width: "100%",
    alignSelf: "center",
  },
  fixedBody: {
    flex: 1,
    padding: 24,
    maxWidth: 1400,
    width: "100%",
    alignSelf: "center",
  },
  drawerOverlay: {
    flex: 1,
    flexDirection: "row",
    backgroundColor: "rgba(0, 0, 0, 0.6)",
  },
  drawerBackdrop: {
    flex: 1,
  },
  drawerSheet: {
    width: 280,
    height: "100%",
    backgroundColor: "#0B1B3D",
  },
});

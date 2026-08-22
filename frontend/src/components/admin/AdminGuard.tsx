import React, { useEffect } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { router, usePathname } from "expo-router";
import { useAdminAuth } from "@/src/context/AdminAuthContext";

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const { ready, isAuthenticated, isSuperAdmin, adminUser } = useAdminAuth();
  const pathname = usePathname();

  const isLoginPage =
    pathname === "/admin" ||
    pathname === "/admin/" ||
    pathname === "/admin/login" ||
    pathname === "/admin/login/";

  useEffect(() => {
    if (!ready) return;

    if (!isAuthenticated && !isLoginPage) {
      router.replace("/admin" as any);
    } else if (isAuthenticated && !isSuperAdmin && !isLoginPage) {
      // Non-super-admin is blocked
      router.replace("/admin" as any);
    } else if (isAuthenticated && isLoginPage) {
      router.replace("/admin/dashboard" as any);
    }
  }, [ready, isAuthenticated, isSuperAdmin, isLoginPage]);

  if (!ready) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#C5A059" />
        <Text style={styles.loadingText}>Verifying Super Admin Authorization...</Text>
      </View>
    );
  }

  if (!isAuthenticated && !isLoginPage) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="small" color="#C5A059" />
        <Text style={styles.loadingText}>Redirecting to Super Admin Login...</Text>
      </View>
    );
  }

  if (isAuthenticated && !isSuperAdmin && !isLoginPage) {
    return (
      <View style={styles.unauthContainer}>
        <Text style={styles.unauthTitle}>403 — Access Denied</Text>
        <Text style={styles.unauthSub}>
          Super Administrator privileges are required to access this control center. Your current role is:{" "}
          <Text style={{ fontWeight: "700" }}>{adminUser?.role || "Restricted"}</Text>.
        </Text>
      </View>
    );
  }

  return <>{children}</>;
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    minHeight: 400,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#061024",
  },
  loadingText: {
    marginTop: 16,
    fontSize: 14,
    color: "#A6B1C2",
    fontWeight: "500",
  },
  unauthContainer: {
    flex: 1,
    minHeight: 400,
    alignItems: "center",
    justifyContent: "center",
    padding: 32,
    backgroundColor: "#061024",
  },
  unauthTitle: {
    fontSize: 22,
    fontWeight: "700",
    color: "#E53E3E",
    marginBottom: 12,
  },
  unauthSub: {
    fontSize: 14,
    color: "#D1D8E5",
    textAlign: "center",
    maxWidth: 480,
    lineHeight: 22,
  },
});

import React, { useEffect } from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";
import { router } from "expo-router";
import { useAdminAuth } from "@/src/context/AdminAuthContext";
import { AdminLoginView } from "@/src/components/admin/AdminLoginView";

export default function AdminIndexScreen() {
  const { ready, isAuthenticated, isSuperAdmin } = useAdminAuth();

  useEffect(() => {
    if (!ready) return;
    if (isAuthenticated && isSuperAdmin) {
      router.replace("/admin/dashboard" as any);
    }
  }, [ready, isAuthenticated, isSuperAdmin]);

  if (!ready) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#C5A059" />
      </View>
    );
  }

  if (isAuthenticated && isSuperAdmin) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#C5A059" />
      </View>
    );
  }

  return <AdminLoginView />;
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    backgroundColor: "#061024",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 400,
  },
});

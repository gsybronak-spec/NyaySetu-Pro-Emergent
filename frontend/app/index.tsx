import { useEffect } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { Redirect, Stack } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";

import { useAuth } from "@/src/context/AuthContext";
import { useTheme } from "@/src/theme/ThemeContext";
import { Spacing } from "@/src/theme/tokens";

export default function Index() {
  const { ready, user } = useAuth();
  const { colors } = useTheme();

  if (!ready) {
    return (
      <LinearGradient colors={["#061024", "#0B1B3D", "#112240"]} style={styles.container}>
        <View style={styles.logo}>
          <Ionicons name="scale" size={64} color="#C5A059" />
        </View>
        <Text style={styles.title}>NyaySetu Pro</Text>
        <Text style={styles.tagline}>The New Era of Advocacy</Text>
        <ActivityIndicator color="#C5A059" style={{ marginTop: Spacing.xl }} />
      </LinearGradient>
    );
  }

  return <Redirect href={user ? "/(tabs)/home" : "/(auth)/login"} />;
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center" },
  logo: {
    width: 108,
    height: 108,
    borderRadius: 30,
    backgroundColor: "rgba(197,160,89,0.12)",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "rgba(197,160,89,0.35)",
  },
  title: {
    color: "#FDFDFD",
    fontSize: 32,
    fontWeight: "700",
    marginTop: Spacing.xl,
    letterSpacing: 0.5,
    fontFamily: "serif",
  },
  tagline: {
    color: "#C5A059",
    fontSize: 14,
    marginTop: Spacing.sm,
    letterSpacing: 1.5,
    textTransform: "uppercase",
    fontWeight: "600",
  },
});

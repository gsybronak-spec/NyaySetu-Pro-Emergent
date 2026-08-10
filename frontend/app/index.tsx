import { useEffect } from "react";
import { ActivityIndicator, Image, StyleSheet, Text, View } from "react-native";
import { Redirect, Stack } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";

import { useAuth } from "@/src/context/AuthContext";
import { useTheme } from "@/src/theme/ThemeContext";
import { Spacing } from "@/src/theme/tokens";

export default function Index() {
  const { ready, user } = useAuth();
  const { colors } = useTheme();

  if (!ready) {
    return (
      <LinearGradient colors={["#061024", "#0B1B3D", "#112240"]} style={styles.container}>
        <Image source={require("../assets/images/logo.png")} style={styles.logo} resizeMode="contain" />
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
    width: 120,
    height: 129,
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

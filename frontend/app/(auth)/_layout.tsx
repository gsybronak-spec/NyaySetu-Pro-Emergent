import { Redirect, Stack } from "expo-router";
import { ActivityIndicator, Image, Platform, StyleSheet, Text } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useAuth } from "@/src/context/AuthContext";
import { Spacing } from "@/src/theme/tokens";

export default function AuthLayout() {
  const { ready, user } = useAuth();

  // If auth is still resolving, render branded splash screen (Zero-Flicker)
  if (!ready) {
    return (
      <LinearGradient colors={["#061024", "#0B1B3D", "#112240"]} style={splashStyles.container}>
        <Image
          source={Platform.OS === "web" ? "/logo.webp" : require("../../assets/images/logo.png")}
          style={splashStyles.logo}
          resizeMode="contain"
        />
        <Text style={splashStyles.title}>NyaySetu Pro</Text>
        <Text style={splashStyles.tagline}>The New Era of Advocacy</Text>
        <ActivityIndicator color="#C5A059" style={{ marginTop: Spacing.xl }} />
      </LinearGradient>
    );
  }

  // If already authenticated, redirect away from login/auth screens immediately
  if (user) {
    const isComplete = user?.profile_completed ?? user?.is_profile_complete ?? true;
    return <Redirect href={isComplete ? "/(tabs)/home" : ("/profile-completion" as any)} />;
  }

  return <Stack screenOptions={{ headerShown: false, animation: "slide_from_right" }} />;
}

const splashStyles = StyleSheet.create({
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

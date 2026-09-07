import { Redirect, Tabs } from "expo-router";
import { BottomTabBar } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { ActivityIndicator, Image, StyleSheet, Text } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { useResponsive } from "@/src/hooks/useResponsive";
import { DesktopSidebar } from "@/src/components/DesktopSidebar";
import { Spacing } from "@/src/theme/tokens";

export default function TabsLayout() {
  const { colors } = useTheme();
  const { ready, user } = useAuth();
  const { isDesktop } = useResponsive();
  const insets = useSafeAreaInsets();

  // Route guard (C4): while auth initializes, render branded splash to avoid premature renders/401s
  if (!ready) {
    return (
      <LinearGradient colors={["#061024", "#0B1B3D", "#112240"]} style={splashStyles.container}>
        <Image source={require("../../assets/images/logo.png")} style={splashStyles.logo} resizeMode="contain" />
        <Text style={splashStyles.title}>NyaySetu Pro</Text>
        <Text style={splashStyles.tagline}>The New Era of Advocacy</Text>
        <ActivityIndicator color="#C5A059" style={{ marginTop: Spacing.xl }} />
      </LinearGradient>
    );
  }

  // Once ready: redirect to login if no session, or profile completion if incomplete
  if (!user) return <Redirect href="/(auth)/login" />;
  const isComplete = user?.profile_completed ?? user?.is_profile_complete ?? false;
  if (!isComplete) return <Redirect href={"/profile-completion" as any} />;

  const bottomInset = insets.bottom;
  const tabHeight = 64 + (bottomInset > 0 ? bottomInset : 8);

  return (
    <Tabs
      tabBar={(props) =>
        isDesktop ? <DesktopSidebar {...props} /> : <BottomTabBar {...props} />
      }
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.brandPrimary,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          height: tabHeight,
          paddingTop: 6,
          paddingBottom: bottomInset > 0 ? bottomInset : 8,
        },
        tabBarItemStyle: {
          paddingVertical: 2,
          justifyContent: "center",
          alignItems: "center",
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "600",
          marginTop: 2,
          marginBottom: 2,
        },
      }}
    >
      <Tabs.Screen
        name="home"
        options={{
          title: "Home",
          tabBarIcon: ({ color, size }) => <Ionicons name="home" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="cases"
        options={{
          title: "My Cases",
          tabBarIcon: ({ color, size }) => <Ionicons name="folder-open" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="templates"
        options={{
          title: "Templates",
          tabBarIcon: ({ color, size }) => <Ionicons name="document-text" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="subscription"
        options={{
          href: null,
          title: "Plans",
          tabBarIcon: ({ color, size }) => <Ionicons name="diamond" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          tabBarIcon: ({ color, size }) => <Ionicons name="person-circle" size={size} color={color} />,
        }}
      />
    </Tabs>
  );
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

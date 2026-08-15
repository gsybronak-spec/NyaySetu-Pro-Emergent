import { Redirect, Tabs } from "expo-router";
import { BottomTabBar } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { useResponsive } from "@/src/hooks/useResponsive";
import { DesktopSidebar } from "@/src/components/DesktopSidebar";

export default function TabsLayout() {
  const { colors, isDark } = useTheme();
  const { ready, user } = useAuth();
  const { isDesktop } = useResponsive();
  const insets = useSafeAreaInsets();

  // Route guard (C4): never render protected tabs for a missing/expired session.
  // The root index also redirects, but this covers sessions that expire mid-use.
  if (ready && !user) return <Redirect href="/(auth)/login" />;

  const bottomInset = insets.bottom;
  const tabHeight = 60 + (bottomInset > 0 ? bottomInset : 0);

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
          height: tabHeight,
          paddingBottom: bottomInset > 0 ? bottomInset : 8,
          paddingTop: 8,
        },
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
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

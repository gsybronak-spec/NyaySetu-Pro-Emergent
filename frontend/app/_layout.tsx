import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import { LogBox, Platform, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { useIconFonts } from "@/src/hooks/use-icon-fonts";
import { ThemeProvider } from "@/src/theme/ThemeContext";
import { AuthProvider } from "@/src/context/AuthContext";

LogBox.ignoreAllLogs(true);

SplashScreen.preventAutoHideAsync();

const GestureContainer = Platform.OS === "web"
  ? View
  : require("react-native-gesture-handler").GestureHandlerRootView;

export default function RootLayout() {
  const [loaded, error] = useIconFonts();

  useEffect(() => {
    if (loaded || error) {
      SplashScreen.hideAsync();
    }
  }, [loaded, error]);

  // On native, wait for fonts / splash hide; on web, allow immediate paint with font-display: swap
  if (Platform.OS !== "web" && !loaded && !error) return null;

  return (
    <GestureContainer style={{ flex: 1 }}>
      <SafeAreaProvider>
        <ThemeProvider>
          <AuthProvider>
            <Stack screenOptions={{ headerShown: false, animation: "fade" }} />
          </AuthProvider>
        </ThemeProvider>
      </SafeAreaProvider>
    </GestureContainer>
  );
}

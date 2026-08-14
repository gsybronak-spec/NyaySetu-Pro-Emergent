import { Platform, useWindowDimensions } from "react-native";

export type Breakpoint = "mobile" | "tablet" | "desktop";

/**
 * Breakpoint architecture:
 *   mobile  < 768px
 *   tablet  768px – 1023px
 *   desktop >= 1024px
 *
 * Desktop is web-only: native (Android/iOS) always keeps the app-like
 * mobile/tablet experience, never the desktop sidebar.
 */
export function useResponsive() {
  const { width, height } = useWindowDimensions();
  const isDesktop = Platform.OS === "web" && width >= 1024;
  const isTablet = Platform.OS === "web" && width >= 768 && width < 1024;
  const isMobile = !isDesktop && !isTablet;
  return { width, height, isDesktop, isTablet, isMobile };
}

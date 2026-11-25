import { router } from "expo-router";
import { Platform } from "react-native";

/**
 * Navigate back safely even when navigation stack is empty (e.g. web refresh,
 * deep link, or after router.replace) or when web history fails to change route.
 */
export function safeBack(fallback: string = "/(tabs)/home") {
  if (Platform.OS === "web" && typeof window !== "undefined") {
    const before = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (router.canGoBack()) {
      router.back();
      setTimeout(() => {
        const after = `${window.location.pathname}${window.location.search}${window.location.hash}`;
        if (after === before) {
          router.replace(fallback as any);
        }
      }, 150);
      return;
    }
    router.replace(fallback as any);
    return;
  }

  if (router.canGoBack()) {
    router.back();
  } else {
    router.replace(fallback as any);
  }
}

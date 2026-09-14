import { Platform } from "react-native";

let initialized = false;

export function initWebKeyboardManager() {
  if (initialized) return;
  if (Platform.OS !== "web" || typeof window === "undefined") return;

  const isMobile =
    window.matchMedia?.("(pointer: coarse)").matches ||
    window.innerWidth < 1024;

  if (!isMobile) return;

  initialized = true;

  const ensureActiveElementVisible = () => {
    const active = document.activeElement as HTMLElement | null;
    if (!active) return;
    const tagName = active.tagName?.toLowerCase();
    const isTextInput =
      tagName === "input" ||
      tagName === "textarea" ||
      active.isContentEditable;

    if (!isTextInput) return;

    // Give the browser time to finish virtual keyboard animation
    setTimeout(() => {
      if (!active || document.activeElement !== active) return;
      const vpHeight = window.visualViewport?.height || window.innerHeight;
      const rect = active.getBoundingClientRect();
      const targetSpacing = 24;

      if (rect.bottom > vpHeight - targetSpacing || rect.top < 0) {
        if (typeof active.scrollIntoView === "function") {
          active.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
            inline: "nearest",
          });
        }
      }
    }, 150);
  };

  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", () => {
      const diff = window.innerHeight - (window.visualViewport?.height || window.innerHeight);
      if (diff > 120) {
        // Keyboard opened
        ensureActiveElementVisible();
      }
    });
  }

  window.addEventListener("focusin", (e) => {
    const target = e.target as HTMLElement | null;
    if (!target) return;
    const tagName = target.tagName?.toLowerCase();
    if (tagName === "input" || tagName === "textarea" || target.isContentEditable) {
      ensureActiveElementVisible();
    }
  });
}

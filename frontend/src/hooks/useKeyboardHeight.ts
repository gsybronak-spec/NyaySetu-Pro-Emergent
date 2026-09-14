import { useEffect, useState } from "react";
import { Dimensions, Keyboard, KeyboardEvent, Platform } from "react-native";

export interface KeyboardState {
  keyboardHeight: number;
  isKeyboardVisible: boolean;
}

export function useKeyboardHeight(): KeyboardState {
  const [state, setState] = useState<KeyboardState>({
    keyboardHeight: 0,
    isKeyboardVisible: false,
  });

  useEffect(() => {
    if (Platform.OS === "web") {
      if (typeof window === "undefined" || !window.visualViewport) {
        return;
      }
      const isMobileTouch =
        window.matchMedia("(pointer: coarse)").matches ||
        window.innerWidth < 1024;

      if (!isMobileTouch) return;

      const handleViewportResize = () => {
        if (!window.visualViewport) return;
        const diff = window.innerHeight - window.visualViewport.height;
        if (diff > 120) {
          setState({ keyboardHeight: diff, isKeyboardVisible: true });
        } else {
          setState({ keyboardHeight: 0, isKeyboardVisible: false });
        }
      };

      window.visualViewport.addEventListener("resize", handleViewportResize);
      return () => {
        window.visualViewport?.removeEventListener("resize", handleViewportResize);
      };
    }

    const showEvent = Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow";
    const hideEvent = Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide";

    const onShow = (e: KeyboardEvent) => {
      const height = e.endCoordinates ? e.endCoordinates.height : 0;
      setState({ keyboardHeight: height, isKeyboardVisible: true });
    };

    const onHide = () => {
      setState({ keyboardHeight: 0, isKeyboardVisible: false });
    };

    const subShow = Keyboard.addListener(showEvent, onShow);
    const subHide = Keyboard.addListener(hideEvent, onHide);

    return () => {
      subShow.remove();
      subHide.remove();
    };
  }, []);

  return state;
}

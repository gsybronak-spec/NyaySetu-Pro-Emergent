import React, {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import {
  Dimensions,
  Keyboard,
  KeyboardEvent,
  NativeScrollEvent,
  NativeSyntheticEvent,
  Platform,
  ScrollView,
  ScrollViewProps,
  StyleSheet,
} from "react-native";
import {
  KeyboardScrollContext,
  KeyboardScrollContextValue,
} from "@/src/context/KeyboardScrollContext";

export interface KeyboardAwareScrollViewProps extends ScrollViewProps {
  extraScrollHeight?: number;
}

export const KeyboardAwareScrollView = forwardRef<
  ScrollView,
  KeyboardAwareScrollViewProps
>(function KeyboardAwareScrollView(
  {
    children,
    contentContainerStyle,
    onScroll,
    scrollEventThrottle = 16,
    keyboardShouldPersistTaps = "handled",
    extraScrollHeight = 24,
    ...rest
  },
  ref
) {
  const internalScrollRef = useRef<ScrollView>(null);
  useImperativeHandle(ref, () => internalScrollRef.current as ScrollView);

  const [keyboardHeight, setKeyboardHeight] = useState(0);
  const [isKeyboardVisible, setIsKeyboardVisible] = useState(false);

  const scrollYRef = useRef(0);
  const activeInputRef = useRef<React.RefObject<any> | null>(null);
  const keyboardHeightRef = useRef(0);

  const scrollToInput = useCallback(
    (inputRef: React.RefObject<any>, extraOffset = extraScrollHeight) => {
      activeInputRef.current = inputRef;

      if (!inputRef?.current || !internalScrollRef.current) return;

      if (Platform.OS === "web") {
        if (typeof inputRef.current.scrollIntoView === "function") {
          inputRef.current.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
            inline: "nearest",
          });
        }
        return;
      }

      // Native (Android & iOS)
      setTimeout(() => {
        if (!inputRef?.current || !internalScrollRef.current) return;

        inputRef.current.measureInWindow(
          (x: number, y: number, width: number, height: number) => {
            if (y === undefined || height === undefined) return;

            const windowHeight = Dimensions.get("window").height;
            const currentKbdHeight = keyboardHeightRef.current;
            // Target line is keyboard top minus spacing (or bottom of window if keyboard not yet reported)
            const keyboardTop =
              currentKbdHeight > 0
                ? windowHeight - currentKbdHeight
                : windowHeight - 320; // reasonable fallback estimate for Android soft keyboard
            const inputBottom = y + height;
            const requiredSpacing = extraOffset;

            if (inputBottom > keyboardTop - requiredSpacing) {
              const overlap = inputBottom - (keyboardTop - requiredSpacing);
              internalScrollRef.current?.scrollTo({
                y: Math.max(0, scrollYRef.current + overlap),
                animated: true,
              });
            }
          }
        );
      }, 80);
    },
    [extraScrollHeight]
  );

  useEffect(() => {
    if (Platform.OS === "web") {
      if (typeof window === "undefined" || !window.visualViewport) return;

      const handleViewport = () => {
        if (!window.visualViewport) return;
        const diff = window.innerHeight - window.visualViewport.height;
        if (diff > 120) {
          keyboardHeightRef.current = diff;
          setKeyboardHeight(diff);
          setIsKeyboardVisible(true);
          if (activeInputRef.current) {
            scrollToInput(activeInputRef.current);
          }
        } else {
          keyboardHeightRef.current = 0;
          setKeyboardHeight(0);
          setIsKeyboardVisible(false);
        }
      };

      window.visualViewport.addEventListener("resize", handleViewport);
      return () => {
        window.visualViewport?.removeEventListener("resize", handleViewport);
      };
    }

    const showEvent = Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow";
    const hideEvent = Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide";

    const onShow = (e: KeyboardEvent) => {
      const height = e.endCoordinates ? e.endCoordinates.height : 0;
      keyboardHeightRef.current = height;
      setKeyboardHeight(height);
      setIsKeyboardVisible(true);

      if (activeInputRef.current) {
        scrollToInput(activeInputRef.current);
      }
    };

    const onHide = () => {
      keyboardHeightRef.current = 0;
      setKeyboardHeight(0);
      setIsKeyboardVisible(false);
      activeInputRef.current = null;
    };

    const subShow = Keyboard.addListener(showEvent, onShow);
    const subHide = Keyboard.addListener(hideEvent, onHide);

    return () => {
      subShow.remove();
      subHide.remove();
    };
  }, [scrollToInput]);

  const handleScroll = useCallback(
    (e: NativeSyntheticEvent<NativeScrollEvent>) => {
      scrollYRef.current = e.nativeEvent.contentOffset.y;
      onScroll?.(e);
    },
    [onScroll]
  );

  const contextValue: KeyboardScrollContextValue = {
    scrollToInput,
    keyboardHeight,
    isKeyboardVisible,
  };

  const flattenedStyle = StyleSheet.flatten(contentContainerStyle) || {};
  const basePaddingBottom =
    typeof flattenedStyle.paddingBottom === "number"
      ? flattenedStyle.paddingBottom
      : 0;

  const adjustedContainerStyle = [
    contentContainerStyle,
    keyboardHeight > 0 && {
      paddingBottom: basePaddingBottom + keyboardHeight,
    },
  ];

  return (
    <KeyboardScrollContext.Provider value={contextValue}>
      <ScrollView
        ref={internalScrollRef}
        keyboardShouldPersistTaps={keyboardShouldPersistTaps}
        scrollEventThrottle={scrollEventThrottle}
        onScroll={handleScroll}
        contentContainerStyle={adjustedContainerStyle}
        {...rest}
      >
        {children}
      </ScrollView>
    </KeyboardScrollContext.Provider>
  );
});

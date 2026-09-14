import React, { forwardRef, useImperativeHandle, useRef } from "react";
import {
  NativeSyntheticEvent,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TextInputFocusEventData,
  TextInputProps,
  View,
} from "react-native";
import { useTheme } from "@/src/theme/ThemeContext";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useKeyboardScroll } from "@/src/context/KeyboardScrollContext";

export interface FieldProps extends TextInputProps {
  label?: string;
  error?: string;
  multiline?: boolean;
  labelColor?: string;
}

export const Field = forwardRef<TextInput, FieldProps>(function Field(
  { label, error, style, multiline, labelColor, onFocus, ...rest },
  forwardedRef
) {
  const { colors } = useTheme();
  const { scrollToInput } = useKeyboardScroll();
  const containerRef = useRef<View>(null);
  const inputRef = useRef<TextInput>(null);

  useImperativeHandle(forwardedRef, () => inputRef.current as TextInput);

  const handleFocus = (e: any) => {
    onFocus?.(e);

    // Coordinate with KeyboardAwareScrollView
    scrollToInput(containerRef, 24);

    // Fallback for mobile web / PWA
    if (Platform.OS === "web" && typeof window !== "undefined") {
      const isMobile =
        window.matchMedia?.("(pointer: coarse)").matches ||
        window.innerWidth < 1024;
      if (isMobile) {
        setTimeout(() => {
          const el = (containerRef.current as any) || (inputRef.current as any);
          if (el && typeof el.scrollIntoView === "function") {
            el.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }
        }, 150);
      }
    }
  };

  return (
    <View ref={containerRef} style={{ marginBottom: Spacing.md }}>
      {label ? (
        <Text style={[styles.label, { color: labelColor || colors.onSurfaceSecondary }]}>
          {label}
        </Text>
      ) : null}
      <TextInput
        ref={inputRef}
        placeholderTextColor={colors.muted}
        onFocus={handleFocus}
        {...rest}
        multiline={multiline}
        style={[
          styles.input,
          {
            color: colors.onSurface,
            backgroundColor: colors.surfaceSecondary,
            borderColor: error ? colors.error : colors.border,
            minHeight: multiline ? 96 : 50,
            textAlignVertical: multiline ? "top" : "center",
            paddingTop: multiline ? Spacing.md : undefined,
          },
          style as any,
        ]}
      />
      {error ? (
        <Text style={{ color: colors.error, fontSize: 12, marginTop: 4 }}>{error}</Text>
      ) : null}
    </View>
  );
});

const styles = StyleSheet.create({
  label: { fontSize: 13, fontWeight: "600", marginBottom: Spacing.xs },
  input: {
    borderRadius: Radius.md,
    borderWidth: 1,
    paddingHorizontal: Spacing.md,
    fontSize: 15,
  },
});

import React from "react";
import { StyleSheet, Text, TextInput, TextInputProps, View } from "react-native";
import { useTheme } from "@/src/theme/ThemeContext";
import { Radius, Spacing } from "@/src/theme/tokens";

interface Props extends TextInputProps {
  label?: string;
  error?: string;
  multiline?: boolean;
}

export function Field({ label, error, style, multiline, ...rest }: Props) {
  const { colors } = useTheme();
  return (
    <View style={{ marginBottom: Spacing.md }}>
      {label ? <Text style={[styles.label, { color: colors.onSurfaceSecondary }]}>{label}</Text> : null}
      <TextInput
        placeholderTextColor={colors.muted}
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
      {error ? <Text style={{ color: colors.error, fontSize: 12, marginTop: 4 }}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  label: { fontSize: 13, fontWeight: "600", marginBottom: Spacing.xs },
  input: {
    borderRadius: Radius.md,
    borderWidth: 1,
    paddingHorizontal: Spacing.md,
    fontSize: 15,
  },
});

import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";
import { Radius, Spacing } from "@/src/theme/tokens";
import { parseDateValue, toISODate } from "@/src/utils/date";

interface Props {
  label?: string;
  /** Canonical value: YYYY-MM-DD (or empty). Legacy DD-MM-YYYY is tolerated. */
  value: string | null | undefined;
  /** Called with the new canonical YYYY-MM-DD value. */
  onChange: (value: string) => void;
  testID?: string;
  placeholder?: string;
}

/**
 * Web date field: a real <input type="date"> so the browser's native calendar
 * opens on click (no dead input, no manual typing required). Styled to match
 * the app's existing field look. Value/onChange stay canonical YYYY-MM-DD.
 */
export function DateField({ label, value, onChange, testID, placeholder }: Props) {
  const { colors } = useTheme();

  // The browser date input only accepts YYYY-MM-DD values.
  const parsed = parseDateValue(value);
  const inputValue = parsed ? toISODate(parsed) : "";

  const inputStyle: React.CSSProperties = {
    flex: 1,
    minHeight: 50,
    borderWidth: 0,
    outline: "none",
    background: "transparent",
    fontSize: 15,
    color: colors.onSurface,
    fontFamily: "inherit",
    padding: 0,
    WebkitAppearance: "none",
    appearance: "none",
    minWidth: 0,
  };

  return (
    <View style={{ marginBottom: Spacing.md }}>
      {label ? (
        <Text style={{ color: colors.onSurfaceSecondary, fontSize: 13, fontWeight: "600", marginBottom: Spacing.xs }}>{label}</Text>
      ) : null}
      <View style={[styles.field, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
        {React.createElement("input", {
          type: "date",
          testID,
          "data-testid": testID,
          value: inputValue,
          onChange: (e: React.ChangeEvent<HTMLInputElement>) => onChange(e.target.value || ""),
          placeholder,
          style: inputStyle,
        } as any)}
        <Ionicons name="calendar-outline" size={18} color={colors.muted} style={{ marginLeft: Spacing.sm }} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  field: {
    minHeight: 50,
    borderRadius: Radius.md,
    borderWidth: 1,
    paddingHorizontal: Spacing.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
});

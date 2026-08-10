import { useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";
import DateTimePicker from "@react-native-community/datetimepicker";
import { Ionicons } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";
import { Radius, Spacing } from "@/src/theme/tokens";
import { formatDateDisplay, parseDateValue, toISODate } from "@/src/utils/date";

interface Props {
  label?: string;
  /** Canonical value: YYYY-MM-DD (or empty). Legacy DD-MM-YYYY is tolerated for display. */
  value: string | null | undefined;
  /** Called with the new canonical YYYY-MM-DD value. */
  onChange: (value: string) => void;
  testID?: string;
  placeholder?: string;
}

/**
 * Native date field: styled Pressable that opens the platform date picker.
 * - Android: native dialog; dismiss leaves the value untouched.
 * - iOS: spinner with explicit Done / Cancel.
 * Stored value is always YYYY-MM-DD; the field displays DD-MM-YYYY.
 */
export function DateField({ label, value, onChange, testID, placeholder }: Props) {
  const { colors } = useTheme();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Date | null>(null);

  const display = formatDateDisplay(value);
  const initial = parseDateValue(value) || new Date();

  const commitDraft = () => {
    if (draft) onChange(toISODate(draft));
  };

  return (
    <View style={{ marginBottom: Spacing.md }}>
      {label ? (
        <Text style={{ color: colors.onSurfaceSecondary, fontSize: 13, fontWeight: "600", marginBottom: Spacing.xs }}>{label}</Text>
      ) : null}
      <Pressable
        testID={testID}
        onPress={() => {
          setDraft(null);
          setOpen(true);
        }}
        style={[styles.field, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
      >
        <Text style={{ color: display ? colors.onSurface : colors.muted, fontSize: 15 }}>{display || placeholder || "Select date"}</Text>
        <Ionicons name="calendar-outline" size={18} color={colors.muted} />
      </Pressable>

      {open && Platform.OS === "ios" ? (
        <View style={[styles.pickerCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <DateTimePicker
            value={draft ?? initial}
            mode="date"
            display="spinner"
            onChange={(_, d) => {
              if (d) setDraft(d);
            }}
          />
          <View style={{ flexDirection: "row", justifyContent: "flex-end", gap: Spacing.md, padding: Spacing.md }}>
            <Pressable testID={testID ? `${testID}-cancel` : undefined} onPress={() => setOpen(false)} hitSlop={8}>
              <Text style={{ color: colors.muted, fontWeight: "700" }}>Cancel</Text>
            </Pressable>
            <Pressable testID={testID ? `${testID}-done` : undefined} onPress={() => { commitDraft(); setOpen(false); }} hitSlop={8}>
              <Text style={{ color: colors.brandPrimary, fontWeight: "800" }}>Done</Text>
            </Pressable>
          </View>
        </View>
      ) : null}

      {open && Platform.OS !== "ios" ? (
        <DateTimePicker
          value={draft ?? initial}
          mode="date"
          display={Platform.OS === "android" ? "default" : "spinner"}
          onChange={(e, d) => {
            setOpen(false);
            if (e.type !== "dismissed" && d) onChange(toISODate(d));
          }}
        />
      ) : null}
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
  pickerCard: {
    marginTop: Spacing.sm,
    borderRadius: Radius.md,
    borderWidth: 1,
    overflow: "hidden",
  },
});

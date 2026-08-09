import React, { useState } from "react";
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTheme } from "@/src/theme/ThemeContext";
import { Radius, Spacing } from "@/src/theme/tokens";

interface Option {
  id: string;
  label: string;
  sublabel?: string;
}

interface Props {
  label?: string;
  placeholder?: string;
  value?: string | null;
  options: Option[];
  onChange: (id: string) => void;
  testID?: string;
  disabled?: boolean;
}

export function Dropdown({ label, placeholder = "Select...", value, options, onChange, testID, disabled }: Props) {
  const { colors } = useTheme();
  const [open, setOpen] = useState(false);
  const selected = options.find((o) => o.id === value);

  return (
    <View style={{ marginBottom: Spacing.md }}>
      {label ? (
        <Text style={[styles.label, { color: colors.onSurfaceSecondary }]}>{label}</Text>
      ) : null}
      <Pressable
        testID={testID}
        onPress={() => !disabled && setOpen(true)}
        style={[
          styles.field,
          {
            backgroundColor: colors.surfaceSecondary,
            borderColor: colors.border,
          },
          disabled && { opacity: 0.5 },
        ]}
      >
        <Text style={{ color: selected ? colors.onSurface : colors.muted, flex: 1 }} numberOfLines={1}>
          {selected ? selected.label : placeholder}
        </Text>
        <Ionicons name="chevron-down" size={18} color={colors.muted} />
      </Pressable>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <Pressable
            style={[styles.sheet, { backgroundColor: colors.surface, borderColor: colors.border }]}
            onPress={(e) => e.stopPropagation()}
          >
            <View style={styles.sheetHead}>
              <Text style={[styles.sheetTitle, { color: colors.onSurface }]}>{label || "Select"}</Text>
              <Pressable onPress={() => setOpen(false)} hitSlop={12}>
                <Ionicons name="close" size={22} color={colors.onSurface} />
              </Pressable>
            </View>
            <ScrollView style={{ maxHeight: 420 }}>
              {options.map((o) => (
                <Pressable
                  key={o.id}
                  testID={`${testID}-opt-${o.id}`}
                  onPress={() => {
                    onChange(o.id);
                    setOpen(false);
                  }}
                  style={({ pressed }) => [
                    styles.opt,
                    { borderBottomColor: colors.divider, backgroundColor: pressed ? colors.surfaceSecondary : "transparent" },
                  ]}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={{ color: colors.onSurface, fontSize: 15 }}>{o.label}</Text>
                    {o.sublabel ? (
                      <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }}>{o.sublabel}</Text>
                    ) : null}
                  </View>
                  {value === o.id ? <Ionicons name="checkmark" size={20} color={colors.brandPrimary} /> : null}
                </Pressable>
              ))}
            </ScrollView>
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  label: { fontSize: 13, fontWeight: "600", marginBottom: Spacing.xs },
  field: {
    minHeight: 50,
    borderRadius: Radius.md,
    borderWidth: 1,
    paddingHorizontal: Spacing.md,
    flexDirection: "row",
    alignItems: "center",
  },
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "flex-end",
  },
  sheet: {
    borderTopLeftRadius: Radius.lg,
    borderTopRightRadius: Radius.lg,
    borderWidth: 1,
    paddingBottom: 24,
  },
  sheetHead: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.lg,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  sheetTitle: { flex: 1, fontSize: 17, fontWeight: "700" },
  opt: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
});

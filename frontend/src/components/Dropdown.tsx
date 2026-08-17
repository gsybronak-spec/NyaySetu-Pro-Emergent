import React, { useMemo, useState } from "react";
import { ActivityIndicator, Modal, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTheme } from "@/src/theme/ThemeContext";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";

export interface Option {
  id: string;
  label: string;
  sublabel?: string;
  pinnable?: boolean;
}

interface Props {
  label?: string;
  placeholder?: string;
  value?: string | null;
  options: Option[];
  onChange: (id: string) => void;
  testID?: string;
  disabled?: boolean;
  searchable?: boolean;
  favouriteIds?: string[];
  onToggleFavourite?: (id: string) => void;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

export function Dropdown({
  label,
  placeholder = "Select...",
  value,
  options = [],
  onChange,
  testID,
  disabled,
  searchable,
  favouriteIds,
  onToggleFavourite,
  loading = false,
  error = null,
  onRetry,
}: Props) {
  const { colors } = useTheme();
  const { isDesktop } = useResponsive();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const selected = options.find((o) => o.id === value);

  const filtered = useMemo(() => {
    let list = Array.isArray(options) ? options : [];
    if (searchable && query.trim()) {
      const q = query.toLowerCase().trim();
      list = list.filter(
        (o) =>
          (o.label || "").toLowerCase().includes(q) ||
          (o.sublabel || "").toLowerCase().includes(q) ||
          (o.id || "").toLowerCase().includes(q)
      );
    }
    if (favouriteIds && favouriteIds.length) {
      const favSetLocal = new Set(favouriteIds);
      const favs = list.filter((o) => favSetLocal.has(o.id));
      const rest = list.filter((o) => !favSetLocal.has(o.id));
      list = [...favs, ...rest];
    }
    return list;
  }, [options, query, searchable, favouriteIds]);

  const favSet = new Set(favouriteIds || []);

  const close = () => {
    setOpen(false);
    setQuery("");
  };

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
        {loading ? (
          <ActivityIndicator size="small" color={colors.brandPrimary} />
        ) : (
          <Ionicons name="chevron-down" size={18} color={colors.muted} />
        )}
      </Pressable>

      <Modal visible={open} transparent animationType="fade" onRequestClose={close}>
        <Pressable
          style={[
            styles.backdrop,
            isDesktop && { justifyContent: "center", alignItems: "center", padding: Spacing.xl },
          ]}
          onPress={close}
        >
          <Pressable
            style={[
              styles.sheet,
              { backgroundColor: colors.surface, borderColor: colors.border },
              isDesktop && {
                width: "100%",
                maxWidth: 540,
                borderRadius: Radius.lg,
                maxHeight: "85%",
              },
            ]}
            onPress={(e) => e.stopPropagation()}
          >
            <View style={styles.sheetHead}>
              <Text style={[styles.sheetTitle, { color: colors.onSurface }]}>{label || "Select"}</Text>
              <Pressable onPress={close} hitSlop={12} testID={`${testID}-close-btn`}>
                <Ionicons name="close" size={22} color={colors.onSurface} />
              </Pressable>
            </View>

            {searchable ? (
              <View
                style={[
                  styles.searchRow,
                  { backgroundColor: colors.surfaceSecondary, borderColor: colors.border },
                ]}
              >
                <Ionicons name="search" size={16} color={colors.muted} />
                <TextInput
                  testID={`${testID}-search`}
                  placeholder="Search in English or ગુજરાતી..."
                  placeholderTextColor={colors.muted}
                  value={query}
                  onChangeText={setQuery}
                  autoFocus={Platform.OS !== "web"}
                  style={{ flex: 1, color: colors.onSurface, marginLeft: Spacing.sm, height: "100%" }}
                />
                {query.length > 0 ? (
                  <Pressable onPress={() => setQuery("")} hitSlop={8}>
                    <Ionicons name="close-circle" size={16} color={colors.muted} />
                  </Pressable>
                ) : null}
              </View>
            ) : null}

            <ScrollView style={{ maxHeight: 420 }} keyboardShouldPersistTaps="handled">
              {loading ? (
                <View style={styles.centerBox}>
                  <ActivityIndicator size="small" color={colors.brandPrimary} />
                  <Text style={{ color: colors.muted, marginTop: Spacing.sm, fontSize: 13 }}>
                    માહિતી લોડ થઈ રહી છે... / Loading options...
                  </Text>
                </View>
              ) : error ? (
                <View style={styles.centerBox}>
                  <Ionicons name="alert-circle-outline" size={28} color={colors.error} />
                  <Text style={{ color: colors.error, fontSize: 13, marginTop: Spacing.xs, textAlign: "center" }}>
                    {error}
                  </Text>
                  {onRetry ? (
                    <Pressable
                      onPress={onRetry}
                      style={[styles.retryBtn, { backgroundColor: colors.brandPrimary }]}
                      testID={`${testID}-retry-btn`}
                    >
                      <Text style={{ color: colors.onBrandPrimary, fontWeight: "700", fontSize: 13 }}>
                        Retry / ફરી પ્રયાસ કરો
                      </Text>
                    </Pressable>
                  ) : null}
                </View>
              ) : filtered.length === 0 ? (
                <View style={styles.centerBox}>
                  <Text style={{ color: colors.muted, textAlign: "center", fontSize: 14 }}>
                    {query.trim() ? "No matches found / કોઈ પરિણામ મળ્યું નથી" : "No options available"}
                  </Text>
                </View>
              ) : (
                filtered.map((o) => {
                  const isFav = favSet.has(o.id);
                  const showStar = onToggleFavourite && o.pinnable !== false && o.id !== "other";
                  return (
                    <Pressable
                      key={o.id}
                      testID={`${testID}-opt-${o.id}`}
                      onPress={() => {
                        onChange(o.id);
                        close();
                      }}
                      style={({ pressed }) => [
                        styles.opt,
                        {
                          borderBottomColor: colors.divider,
                          backgroundColor: pressed ? colors.surfaceSecondary : "transparent",
                        },
                      ]}
                    >
                      {showStar ? (
                        <Pressable
                          testID={`${testID}-fav-${o.id}`}
                          hitSlop={10}
                          onPress={(e) => {
                            e.stopPropagation();
                            onToggleFavourite!(o.id);
                          }}
                          style={{ marginRight: Spacing.sm }}
                        >
                          <Ionicons
                            name={isFav ? "star" : "star-outline"}
                            size={18}
                            color={isFav ? colors.brandPrimary : colors.muted}
                          />
                        </Pressable>
                      ) : null}
                      <View style={{ flex: 1 }}>
                        <Text style={{ color: colors.onSurface, fontSize: 15, fontWeight: value === o.id ? "700" : "400" }}>
                          {o.label}
                        </Text>
                        {o.sublabel ? (
                          <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }}>{o.sublabel}</Text>
                        ) : null}
                      </View>
                      {value === o.id ? <Ionicons name="checkmark-circle" size={20} color={colors.brandPrimary} /> : null}
                    </Pressable>
                  );
                })
              )}
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
  searchRow: {
    flexDirection: "row",
    alignItems: "center",
    marginHorizontal: Spacing.lg,
    marginTop: Spacing.md,
    marginBottom: Spacing.xs,
    paddingHorizontal: Spacing.md,
    height: 44,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  opt: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  centerBox: {
    padding: Spacing.xxl,
    alignItems: "center",
    justifyContent: "center",
  },
  retryBtn: {
    marginTop: Spacing.md,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.md,
  },
});

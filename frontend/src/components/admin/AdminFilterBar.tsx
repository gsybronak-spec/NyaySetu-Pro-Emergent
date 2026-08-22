import React, { useState } from "react";
import { StyleSheet, Text, TextInput, View, Pressable, Platform } from "react-native";
import { Ionicons } from "@expo/vector-icons";

export interface FilterOption {
  label: string;
  value: string;
}

export interface FilterField {
  key: string;
  label: string;
  value: string;
  options: FilterOption[];
  onChange: (value: string) => void;
}

interface AdminFilterBarProps {
  search?: string;
  onSearchChange?: (val: string) => void;
  searchPlaceholder?: string;
  filters?: FilterField[];
  onReset?: () => void;
  totalCount?: number;
}

export function AdminFilterBar({
  search = "",
  onSearchChange,
  searchPlaceholder = "Search records...",
  filters = [],
  onReset,
  totalCount,
}: AdminFilterBarProps) {
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);

  const hasActiveFilters =
    search.trim().length > 0 || filters.some((f) => f.value && f.value !== "all" && f.value !== "");

  return (
    <View style={styles.container}>
      {/* Search Input */}
      {onSearchChange ? (
        <View style={styles.searchBox}>
          <Ionicons name="search" size={16} color="#8B96A9" style={styles.searchIcon} />
          <TextInput
            style={styles.searchInput}
            placeholder={searchPlaceholder}
            placeholderTextColor="#6B7280"
            value={search}
            onChangeText={onSearchChange}
          />
          {search ? (
            <Pressable onPress={() => onSearchChange("")} style={styles.clearBtn}>
              <Ionicons name="close-circle" size={16} color="#8B96A9" />
            </Pressable>
          ) : null}
        </View>
      ) : null}

      {/* Filter Dropdowns */}
      <View style={styles.filterRow}>
        {filters.map((f) => {
          const selectedOption = f.options.find((o) => o.value === f.value);
          const isSelected = f.value && f.value !== "all" && f.value !== "";

          if (Platform.OS === "web") {
            return (
              <View key={f.key} style={styles.webSelectWrapper}>
                <select
                  value={f.value}
                  onChange={(e) => f.onChange(e.target.value)}
                  style={{
                    backgroundColor: isSelected ? "#1E293B" : "#12203B",
                    color: isSelected ? "#C5A059" : "#D1D8E5",
                    border: `1px solid ${isSelected ? "#C5A059" : "#253452"}`,
                    borderRadius: "8px",
                    padding: "8px 12px",
                    fontSize: "13px",
                    fontWeight: 500,
                    outline: "none",
                    cursor: "pointer",
                  }}
                >
                  <option value="all">{`All ${f.label}`}</option>
                  {f.options.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </View>
            );
          }

          return (
            <Pressable
              key={f.key}
              onPress={() => setActiveDropdown(activeDropdown === f.key ? null : f.key)}
              style={[styles.filterChip, isSelected && styles.filterChipActive]}
            >
              <Text style={[styles.filterChipText, isSelected && styles.filterChipTextActive]}>
                {selectedOption?.label || f.label}
              </Text>
              <Ionicons
                name="chevron-down"
                size={14}
                color={isSelected ? "#C5A059" : "#8B96A9"}
                style={{ marginLeft: 4 }}
              />
            </Pressable>
          );
        })}

        {/* Reset Button */}
        {hasActiveFilters && onReset ? (
          <Pressable onPress={onReset} style={styles.resetBtn}>
            <Ionicons name="refresh" size={14} color="#C5A059" style={{ marginRight: 4 }} />
            <Text style={styles.resetText}>Reset</Text>
          </Pressable>
        ) : null}

        {totalCount !== undefined ? (
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{totalCount} records</Text>
          </View>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: 12,
    marginBottom: 16,
  },
  searchBox: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#12203B",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#253452",
    paddingHorizontal: 12,
    minWidth: 260,
    flex: 1,
    maxWidth: 400,
    height: 38,
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    color: "#FDFDFD",
    fontSize: 13,
    paddingVertical: 0,
  },
  clearBtn: {
    padding: 4,
  },
  filterRow: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 8,
  },
  webSelectWrapper: {
    minWidth: 130,
  },
  filterChip: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#12203B",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#253452",
  },
  filterChipActive: {
    backgroundColor: "rgba(197, 160, 89, 0.15)",
    borderColor: "#C5A059",
  },
  filterChipText: {
    fontSize: 13,
    color: "#D1D8E5",
    fontWeight: "500",
  },
  filterChipTextActive: {
    color: "#C5A059",
    fontWeight: "600",
  },
  resetBtn: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: "#1B2A49",
    borderWidth: 1,
    borderColor: "#253452",
  },
  resetText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#C5A059",
  },
  countBadge: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: "#1B2A49",
  },
  countText: {
    fontSize: 12,
    color: "#8B96A9",
    fontWeight: "500",
  },
});

import React from "react";
import { StyleSheet, Text, View, ScrollView, Pressable, Platform } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { AdminLoadingState, AdminEmptyState, AdminErrorState } from "./AdminStates";

export interface ColumnDef<T> {
  key: string;
  header: string;
  width?: number | string;
  flex?: number;
  align?: "left" | "center" | "right";
  render?: (item: T, index: number) => React.ReactNode;
}

interface AdminDataTableProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  keyExtractor: (item: T) => string;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyIcon?: keyof typeof Ionicons.glyphMap;
  selectable?: boolean;
  selectedKeys?: string[];
  onSelectionChange?: (keys: string[]) => void;
  onRowPress?: (item: T) => void;
  bulkActions?: React.ReactNode;
}

export function AdminDataTable<T>({
  columns,
  data,
  keyExtractor,
  loading = false,
  error = null,
  onRetry,
  emptyTitle,
  emptyDescription,
  emptyIcon,
  selectable = false,
  selectedKeys = [],
  onSelectionChange,
  onRowPress,
  bulkActions,
}: AdminDataTableProps<T>) {
  if (loading && (!data || data.length === 0)) {
    return (
      <View style={styles.tableWrapper}>
        <AdminLoadingState />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.tableWrapper}>
        <AdminErrorState message={error} onRetry={onRetry} />
      </View>
    );
  }

  const allSelected = data.length > 0 && data.every((item) => selectedKeys.includes(keyExtractor(item)));

  const toggleSelectAll = () => {
    if (!onSelectionChange) return;
    if (allSelected) {
      onSelectionChange([]);
    } else {
      onSelectionChange(data.map(keyExtractor));
    }
  };

  const toggleSelectRow = (key: string) => {
    if (!onSelectionChange) return;
    if (selectedKeys.includes(key)) {
      onSelectionChange(selectedKeys.filter((k) => k !== key));
    } else {
      onSelectionChange([...selectedKeys, key]);
    }
  };

  return (
    <View style={styles.tableWrapper}>
      {/* Bulk actions banner */}
      {selectable && selectedKeys.length > 0 && bulkActions ? (
        <View style={styles.bulkToolbar}>
          <Text style={styles.bulkCount}>{selectedKeys.length} selected</Text>
          <View style={styles.bulkActionsContainer}>{bulkActions}</View>
        </View>
      ) : null}

      <ScrollView horizontal showsHorizontalScrollIndicator={true} contentContainerStyle={{ minWidth: "100%" }}>
        <View style={styles.tableInner}>
          {/* Header Row */}
          <View style={styles.headerRow}>
            {selectable ? (
              <Pressable onPress={toggleSelectAll} style={styles.checkboxCell}>
                <Ionicons
                  name={allSelected ? "checkbox" : "square-outline"}
                  size={18}
                  color={allSelected ? "#C5A059" : "#6B7280"}
                />
              </Pressable>
            ) : null}

            {columns.map((col) => {
              const alignStyle =
                col.align === "right"
                  ? { alignItems: "flex-end" as const }
                  : col.align === "center"
                  ? { alignItems: "center" as const }
                  : { alignItems: "flex-start" as const };

              return (
                <View
                  key={col.key}
                  style={[
                    styles.headerCell,
                    col.width ? { width: col.width as any } : { flex: col.flex || 1, minWidth: 120 },
                    alignStyle,
                  ]}
                >
                  <Text style={styles.headerText}>{col.header}</Text>
                </View>
              );
            })}
          </View>

          {/* Body Rows */}
          {data.length === 0 ? (
            <AdminEmptyState title={emptyTitle} description={emptyDescription} icon={emptyIcon} />
          ) : (
            data.map((item, index) => {
              const rowKey = keyExtractor(item);
              const isSelected = selectedKeys.includes(rowKey);
              const isEven = index % 2 === 0;

              return (
                <Pressable
                  key={rowKey}
                  onPress={() => onRowPress?.(item)}
                  style={({ pressed }) => [
                    styles.bodyRow,
                    isEven ? styles.rowEven : styles.rowOdd,
                    isSelected && styles.rowSelected,
                    pressed && onRowPress ? styles.rowPressed : null,
                  ]}
                >
                  {selectable ? (
                    <Pressable
                      onPress={(e) => {
                        e.stopPropagation();
                        toggleSelectRow(rowKey);
                      }}
                      style={styles.checkboxCell}
                    >
                      <Ionicons
                        name={isSelected ? "checkbox" : "square-outline"}
                        size={18}
                        color={isSelected ? "#C5A059" : "#6B7280"}
                      />
                    </Pressable>
                  ) : null}

                  {columns.map((col) => {
                    const alignStyle =
                      col.align === "right"
                        ? { alignItems: "flex-end" as const }
                        : col.align === "center"
                        ? { alignItems: "center" as const }
                        : { alignItems: "flex-start" as const };

                    return (
                      <View
                        key={col.key}
                        style={[
                          styles.bodyCell,
                          col.width ? { width: col.width as any } : { flex: col.flex || 1, minWidth: 120 },
                          alignStyle,
                        ]}
                      >
                        {col.render ? (
                          col.render(item, index)
                        ) : (
                          <Text style={styles.cellText} numberOfLines={1}>
                            {String((item as any)[col.key] ?? "—")}
                          </Text>
                        )}
                      </View>
                    );
                  })}
                </Pressable>
              );
            })
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  tableWrapper: {
    backgroundColor: "#12203B",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#253452",
    overflow: "hidden",
  },
  tableInner: {
    width: "100%",
  },
  bulkToolbar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "rgba(197, 160, 89, 0.15)",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#C5A059",
  },
  bulkCount: {
    fontSize: 13,
    fontWeight: "700",
    color: "#C5A059",
  },
  bulkActionsContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#0D182E",
    borderBottomWidth: 1,
    borderBottomColor: "#253452",
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  headerCell: {
    paddingHorizontal: 8,
    justifyContent: "center",
  },
  headerText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#8B96A9",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  bodyRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#1B2A49",
  },
  rowEven: {
    backgroundColor: "#12203B",
  },
  rowOdd: {
    backgroundColor: "#0F1C34",
  },
  rowSelected: {
    backgroundColor: "rgba(197, 160, 89, 0.12)",
  },
  rowPressed: {
    backgroundColor: "#1B2A49",
  },
  bodyCell: {
    paddingHorizontal: 8,
    justifyContent: "center",
  },
  cellText: {
    fontSize: 13,
    color: "#D1D8E5",
  },
  checkboxCell: {
    width: 36,
    alignItems: "center",
    justifyContent: "center",
  },
});

import React from "react";
import { StyleSheet, Text, View, Pressable, Platform } from "react-native";
import { Ionicons } from "@expo/vector-icons";

interface AdminPaginationProps {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
}

export function AdminPagination({
  page,
  pageSize,
  total,
  totalPages,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 25, 50, 100],
}: AdminPaginationProps) {
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  const canPrev = page > 1;
  const canNext = page < totalPages;

  return (
    <View style={styles.container}>
      {/* Range text */}
      <View style={styles.infoRow}>
        <Text style={styles.infoText}>
          Showing <Text style={styles.boldText}>{from}</Text> to{" "}
          <Text style={styles.boldText}>{to}</Text> of <Text style={styles.boldText}>{total}</Text> results
        </Text>

        {onPageSizeChange && Platform.OS === "web" ? (
          <View style={styles.pageSizeWrapper}>
            <Text style={styles.pageSizeLabel}>Rows per page:</Text>
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              style={{
                backgroundColor: "#12203B",
                color: "#D1D8E5",
                border: "1px solid #253452",
                borderRadius: "6px",
                padding: "4px 8px",
                fontSize: "12px",
                fontWeight: 500,
                outline: "none",
                cursor: "pointer",
              }}
            >
              {pageSizeOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </View>
        ) : null}
      </View>

      {/* Pagination Controls */}
      <View style={styles.controls}>
        <Pressable
          disabled={!canPrev}
          onPress={() => onPageChange(1)}
          style={[styles.navBtn, !canPrev && styles.navBtnDisabled]}
        >
          <Ionicons name="play-back" size={14} color={canPrev ? "#D1D8E5" : "#6B7280"} />
        </Pressable>

        <Pressable
          disabled={!canPrev}
          onPress={() => onPageChange(page - 1)}
          style={[styles.navBtn, !canPrev && styles.navBtnDisabled]}
        >
          <Ionicons name="chevron-back" size={16} color={canPrev ? "#D1D8E5" : "#6B7280"} />
        </Pressable>

        <View style={styles.pageNumberBadge}>
          <Text style={styles.pageNumberText}>
            Page {page} of {Math.max(totalPages, 1)}
          </Text>
        </View>

        <Pressable
          disabled={!canNext}
          onPress={() => onPageChange(page + 1)}
          style={[styles.navBtn, !canNext && styles.navBtnDisabled]}
        >
          <Ionicons name="chevron-forward" size={16} color={canNext ? "#D1D8E5" : "#6B7280"} />
        </Pressable>

        <Pressable
          disabled={!canNext}
          onPress={() => onPageChange(totalPages)}
          style={[styles.navBtn, !canNext && styles.navBtnDisabled]}
        >
          <Ionicons name="play-forward" size={14} color={canNext ? "#D1D8E5" : "#6B7280"} />
        </Pressable>
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
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderTopWidth: 1,
    borderTopColor: "#253452",
    backgroundColor: "#0D182E",
    borderBottomLeftRadius: 12,
    borderBottomRightRadius: 12,
  },
  infoRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 16,
  },
  infoText: {
    fontSize: 13,
    color: "#8B96A9",
  },
  boldText: {
    fontWeight: "700",
    color: "#FDFDFD",
  },
  pageSizeWrapper: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  pageSizeLabel: {
    fontSize: 12,
    color: "#8B96A9",
  },
  controls: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  navBtn: {
    width: 32,
    height: 32,
    borderRadius: 6,
    backgroundColor: "#1B2A49",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "#253452",
  },
  navBtnDisabled: {
    opacity: 0.4,
    backgroundColor: "#0F1A2E",
  },
  pageNumberBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: "#12203B",
    borderWidth: 1,
    borderColor: "#253452",
  },
  pageNumberText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#D1D8E5",
  },
});

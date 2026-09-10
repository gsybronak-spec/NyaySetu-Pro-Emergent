import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { useTheme } from "@/src/theme/ThemeContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";

function fmtDate(iso?: string) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso.slice(0, 10);
  return (
    d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" }) +
    " · " +
    d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })
  );
}

export function NotificationCenter() {
  const { colors } = useTheme();
  const [visible, setVisible] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const loadNotifications = useCallback(async () => {
    try {
      const res = await api.notifications();
      if (res && Array.isArray(res.notifications)) {
        setNotifications(res.notifications);
        setUnreadCount(res.unread_count || 0);
      }
    } catch {
      // Offline fallback
    }
  }, []);

  useEffect(() => {
    loadNotifications();
    const interval = setInterval(loadNotifications, 60000); // 1-minute poll
    return () => clearInterval(interval);
  }, [loadNotifications]);

  const openModal = () => {
    setVisible(true);
    loadNotifications();
  };

  const handleMarkRead = async (notif: any) => {
    try {
      await api.markNotificationRead(notif.id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notif.id ? { ...n, read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // Ignore
    }
  };

  const handleMarkAllRead = async () => {
    setLoading(true);
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch {
      // Ignore
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Pressable
        testID="notification-bell-btn"
        onPress={openModal}
        style={({ pressed }) => [
          styles.bellBtn,
          { backgroundColor: colors.surfaceSecondary, borderColor: colors.border },
          pressed && { opacity: 0.8 },
        ]}
        hitSlop={8}
      >
        <Ionicons name="notifications-outline" size={20} color={colors.onSurface} />
        {unreadCount > 0 && (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>
              {unreadCount > 9 ? "9+" : unreadCount}
            </Text>
          </View>
        )}
      </Pressable>

      <Modal
        visible={visible}
        transparent
        animationType="fade"
        onRequestClose={() => setVisible(false)}
      >
        <Pressable style={styles.overlay} onPress={() => setVisible(false)}>
          <Pressable
            style={[
              styles.modalCard,
              { backgroundColor: colors.surface, borderColor: colors.border },
            ]}
            onPress={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <View style={[styles.header, { borderBottomColor: colors.border }]}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                <Ionicons name="notifications" size={18} color={colors.brandPrimary} />
                <Text style={[styles.headerTitle, { color: colors.onSurface }]}>Notifications</Text>
                {unreadCount > 0 && (
                  <View style={[styles.pill, { backgroundColor: colors.brandPrimary + "20" }]}>
                    <Text style={[styles.pillText, { color: colors.brandPrimary }]}>
                      {unreadCount} new
                    </Text>
                  </View>
                )}
              </View>

              <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                {unreadCount > 0 && (
                  <Pressable
                    testID="notif-mark-all-read"
                    onPress={handleMarkAllRead}
                    disabled={loading}
                    hitSlop={8}
                  >
                    <Text style={[styles.markAllText, { color: colors.brandPrimary }]}>
                      Mark all read
                    </Text>
                  </Pressable>
                )}
                <Pressable onPress={() => setVisible(false)} hitSlop={8}>
                  <Ionicons name="close" size={20} color={colors.muted} />
                </Pressable>
              </View>
            </View>

            {/* List */}
            <ScrollView
              style={{ maxHeight: 420 }}
              contentContainerStyle={{ padding: Spacing.sm }}
            >
              {notifications.length === 0 ? (
                <View style={styles.empty}>
                  <Ionicons name="notifications-off-outline" size={40} color={colors.muted} />
                  <Text style={[styles.emptyText, { color: colors.muted }]}>
                    No notifications right now
                  </Text>
                </View>
              ) : (
                notifications.map((n) => {
                  const isAnnouncement = n.type === "announcement";
                  const isUnread = !n.read;
                  return (
                    <Pressable
                      key={n.id}
                      testID={`notif-item-${n.id}`}
                      onPress={() => isUnread && handleMarkRead(n)}
                      style={[
                        styles.item,
                        {
                          backgroundColor: isUnread
                            ? colors.brandPrimary + "0C"
                            : colors.surfaceSecondary,
                          borderColor: isUnread ? colors.brandPrimary + "40" : colors.border,
                        },
                      ]}
                    >
                      <View
                        style={[
                          styles.itemIcon,
                          {
                            backgroundColor: isAnnouncement
                              ? "#3B82F620"
                              : colors.brandPrimary + "20",
                          },
                        ]}
                      >
                        <Ionicons
                          name={isAnnouncement ? "megaphone-outline" : "information-circle-outline"}
                          size={18}
                          color={isAnnouncement ? "#2563EB" : colors.brandPrimary}
                        />
                      </View>

                      <View style={{ flex: 1, minWidth: 0, marginLeft: Spacing.sm }}>
                        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
                          <Text
                            style={[
                              styles.itemTitle,
                              {
                                color: colors.onSurface,
                                fontWeight: isUnread ? "700" : "600",
                              },
                            ]}
                            numberOfLines={1}
                          >
                            {n.title || "Notice"}
                          </Text>
                          {isUnread && <View style={styles.unreadDot} />}
                        </View>

                        <Text style={[styles.itemMsg, { color: colors.onSurfaceSecondary }]}>
                          {n.message}
                        </Text>

                        <Text style={[styles.itemDate, { color: colors.muted }]}>
                          {fmtDate(n.created_at)}
                        </Text>
                      </View>
                    </Pressable>
                  );
                })
              )}
            </ScrollView>
          </Pressable>
        </Pressable>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  bellBtn: {
    width: 38,
    height: 38,
    borderRadius: Radius.md,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
  },
  badge: {
    position: "absolute",
    top: -3,
    right: -3,
    backgroundColor: "#EF4444",
    minWidth: 16,
    height: 16,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 3,
  },
  badgeText: {
    color: "#FFFFFF",
    fontSize: 9,
    fontWeight: "800",
  },
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.45)",
    alignItems: "center",
    justifyContent: "center",
    padding: Spacing.md,
  },
  modalCard: {
    width: "100%",
    maxWidth: 440,
    borderRadius: Radius.lg,
    borderWidth: 1,
    overflow: "hidden",
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 16,
    elevation: 8,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: Spacing.md,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  headerTitle: {
    fontSize: 15,
    fontWeight: "700",
  },
  pill: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: Radius.full,
  },
  pillText: {
    fontSize: 11,
    fontWeight: "700",
  },
  markAllText: {
    fontSize: 12,
    fontWeight: "600",
  },
  item: {
    flexDirection: "row",
    alignItems: "flex-start",
    padding: Spacing.sm,
    borderRadius: Radius.md,
    borderWidth: 1,
    marginBottom: Spacing.xs,
  },
  itemIcon: {
    width: 32,
    height: 32,
    borderRadius: Radius.sm,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 2,
  },
  itemTitle: {
    fontSize: 13,
  },
  itemMsg: {
    fontSize: 12,
    marginTop: 2,
    lineHeight: 16,
  },
  itemDate: {
    fontSize: 10,
    marginTop: 4,
  },
  unreadDot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
    backgroundColor: "#EF4444",
    marginLeft: 6,
  },
  empty: {
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 13,
    marginTop: Spacing.sm,
  },
});

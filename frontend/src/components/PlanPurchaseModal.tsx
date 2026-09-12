import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
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
import { Radius, Spacing } from "@/src/theme/tokens";
import { api } from "@/src/api/client";
import { getCachedPlans, setCachedPlans } from "@/src/constants/plans";
import {
  loadRazorpayScript,
  preloadRazorpayScript,
  prepareRazorpayModal,
  RAZORPAY_THEME_COLOR,
  RAZORPAY_BACKDROP_COLOR,
  RAZORPAY_LOGO_URL,
} from "@/src/utils/razorpay";

const RAZORPAY_ENABLED = process.env.EXPO_PUBLIC_RAZORPAY_ENABLED === "1";

interface PlanPurchaseModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: (newBalance: number) => void;
  currentBalance?: number;
}

export function PlanPurchaseModal({
  visible,
  onClose,
  onSuccess,
  currentBalance = 0,
}: PlanPurchaseModalProps) {
  const { colors } = useTheme();
  // Instant initial plans from in-memory cache — zero blank loading delay
  const [plans, setPlans] = useState<any[]>(() => getCachedPlans());
  const [loading, setLoading] = useState(false);
  const [buyingId, setBuyingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (visible) {
      preloadRazorpayScript();
      setError(null);
      api
        .plans()
        .then((p: any) => {
          const list = Array.isArray(p) ? p : [];
          const active = list.filter((x: any) => x.active !== false);
          if (active.length > 0) {
            setPlans(active);
            setCachedPlans(active);
          }
        })
        .catch((e: any) => {
          // Gracefully retain cached plans
        })
        .finally(() => setLoading(false));
    }
  }, [visible]);

  const handlePurchase = async (plan: any) => {
    setBuyingId(plan.id);
    setError(null);
    try {
      let balance = currentBalance;
      if (RAZORPAY_ENABLED) {
        // Parallelize order creation with script loading check
        const [order] = await Promise.all([
          api.razorpayCreateOrder(plan.id),
          Platform.OS === "web" ? loadRazorpayScript() : Promise.resolve(),
        ]);

        prepareRazorpayModal();
        let paymentId = "";
        let signature = "";

        if (Platform.OS === "web") {
          const payment = await new Promise<any>((resolve, reject) => {
            const Razorpay = (window as any).Razorpay;
            if (!Razorpay) {
              reject(new Error("Payment gateway unavailable"));
              return;
            }
            const rz = new Razorpay({
              key: order.key_id || process.env.EXPO_PUBLIC_RAZORPAY_KEY_ID,
              amount: order.amount_paise,
              currency: order.currency || "INR",
              order_id: order.order_id,
              name: "NyaySetu Pro",
              description: order.plan?.name || plan.name || "",
              image: RAZORPAY_LOGO_URL,
              theme: {
                color: RAZORPAY_THEME_COLOR,
                backdrop_color: RAZORPAY_BACKDROP_COLOR,
              },
              modal: {
                backdropclose: false,
                escape: true,
                handleback: true,
                confirm_close: true,
                animation: true,
                ondismiss: () => reject(new Error("Payment cancelled")),
              },
              handler: (response: any) => resolve(response),
            });
            rz.on("payment.failed", (response: any) => {
              const reason = response?.error?.description || response?.error?.reason || "Payment failed";
              reject(new Error(reason));
            });
            rz.open();
          });
          paymentId = payment.razorpay_payment_id;
          signature = payment.razorpay_signature;
        } else {
          const RazorpayCheckout = require("react-native-razorpay").default;
          const payment = await RazorpayCheckout.open({
            key: order.key_id || process.env.EXPO_PUBLIC_RAZORPAY_KEY_ID,
            amount: order.amount_paise,
            currency: order.currency || "INR",
            name: "NyaySetu Pro",
            description: order.plan?.name || plan.name || "",
            image: RAZORPAY_LOGO_URL,
            order_id: order.order_id,
            theme: { color: RAZORPAY_THEME_COLOR },
          });
          paymentId = payment.razorpay_payment_id;
          signature = payment.razorpay_signature;
        }

        const verified = await api.razorpayVerify({
          plan_id: plan.id,
          order_id: order.order_id,
          payment_id: paymentId,
          signature: signature,
        });
        balance = verified.balance;
      } else {
        const res = await api.purchase(plan.id);
        balance = res.balance;
      }

      const msg = `Payment Successful! ${plan.credits || ""} credits added. New balance: ${balance} credits.`;
      if (Platform.OS === "web" && typeof window !== "undefined") {
        window.alert(msg);
      } else {
        Alert.alert("Success", msg);
      }

      if (onSuccess) onSuccess(balance);
      onClose();
    } catch (e: any) {
      const msg = e?.message || "Purchase could not be completed.";
      setError(msg);
    } finally {
      setBuyingId(null);
    }
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <Pressable style={styles.overlay} onPress={onClose}>
        <Pressable
          style={[
            styles.modalContainer,
            { backgroundColor: colors.surface, borderColor: colors.border },
          ]}
          onPress={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <View style={styles.header}>
            <View style={{ flex: 1 }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                <Ionicons name="diamond" size={20} color="#C5A059" />
                <Text style={[styles.headerTitle, { color: colors.onSurface }]}>
                  Purchase Template Credits
                </Text>
              </View>
              <Text style={[styles.headerSub, { color: colors.muted }]}>
                તમારી પાસે ક્રેડિટ સમાપ્ત થઈ ગઈ છે • યોજના પસંદ કરો
              </Text>
            </View>
            <Pressable
              testID="close-plan-modal"
              onPress={onClose}
              hitSlop={10}
              style={[styles.closeBtn, { backgroundColor: colors.surfaceSecondary }]}
            >
              <Ionicons name="close" size={20} color={colors.muted} />
            </Pressable>
          </View>

          {/* Balance Pill */}
          <View
            style={[
              styles.balancePill,
              { backgroundColor: colors.surfaceSecondary, borderColor: colors.border },
            ]}
          >
            <Ionicons name="wallet-outline" size={16} color={colors.muted} />
            <Text style={{ fontSize: 13, color: colors.muted }}>
              Current Balance:{" "}
              <Text style={{ fontWeight: "700", color: currentBalance > 0 ? "#10B981" : "#EF4444" }}>
                {currentBalance} Credits
              </Text>
            </Text>
          </View>

          {error && (
            <View style={styles.errorBox}>
              <Ionicons name="alert-circle" size={16} color="#EF4444" />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          {/* Plans List */}
          {loading ? (
            <View style={{ padding: Spacing.xl, alignItems: "center" }}>
              <ActivityIndicator size="large" color={colors.brandPrimary} />
              <Text style={{ marginTop: Spacing.md, color: colors.muted, fontSize: 13 }}>
                Loading plans...
              </Text>
            </View>
          ) : (
            <ScrollView style={{ maxHeight: 380 }} contentContainerStyle={{ gap: Spacing.md }}>
              {plans.length === 0 ? (
                <Text style={{ textAlign: "center", color: colors.muted, padding: Spacing.lg }}>
                  No active plans available right now. Please contact support.
                </Text>
              ) : (
                plans.map((p) => {
                  const isBuying = buyingId === p.id;
                  const priceInRupees = typeof p.price === "number" ? (p.price > 1000 ? p.price / 100 : p.price) : p.price;
                  const pricePerCredit = p.credits ? Math.round(priceInRupees / p.credits) : 0;

                  return (
                    <View
                      key={p.id}
                      style={[
                        styles.planCard,
                        {
                          borderColor: p.popular ? colors.brandPrimary : colors.border,
                          backgroundColor: colors.surfaceSecondary,
                        },
                      ]}
                    >
                      {p.popular && (
                        <View style={[styles.popularBadge, { backgroundColor: colors.brandPrimary }]}>
                          <Text style={[styles.popularText, { color: colors.onBrandPrimary }]}>
                            MOST POPULAR
                          </Text>
                        </View>
                      )}
                      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                        <View style={{ flex: 1 }}>
                          <Text style={[styles.planName, { color: colors.onSurface }]}>
                            {p.name}
                          </Text>
                          <Text style={[styles.planCredits, { color: colors.brandPrimary }]}>
                            {p.credits} Template Credits
                          </Text>
                          {pricePerCredit > 0 && (
                            <Text style={{ fontSize: 11, color: colors.muted, marginTop: 2 }}>
                              ₹{pricePerCredit} per document • Never expires
                            </Text>
                          )}
                        </View>
                        <View style={{ alignItems: "flex-end" }}>
                          <Text style={[styles.planPrice, { color: colors.onSurface }]}>
                            ₹{priceInRupees}
                          </Text>
                          <Pressable
                            testID={`buy-plan-${p.id}`}
                            disabled={buyingId !== null}
                            onPress={() => handlePurchase(p)}
                            style={({ pressed }) => [
                              styles.buyBtn,
                              { backgroundColor: colors.brandPrimary },
                              (pressed || isBuying) && { opacity: 0.8 },
                            ]}
                          >
                            {isBuying ? (
                              <ActivityIndicator size="small" color={colors.onBrandPrimary} />
                            ) : (
                              <Text style={[styles.buyBtnText, { color: colors.onBrandPrimary }]}>
                                Buy Now
                              </Text>
                            )}
                          </Pressable>
                        </View>
                      </View>
                    </View>
                  );
                })
              )}
            </ScrollView>
          )}

          {/* Footer */}
          <View style={styles.footer}>
            <Pressable
              testID="cancel-plan-modal"
              onPress={onClose}
              style={({ pressed }) => [
                styles.cancelBtn,
                { borderColor: colors.border },
                pressed && { opacity: 0.7 },
              ]}
            >
              <Text style={[styles.cancelBtnText, { color: colors.muted }]}>Close / બંધ કરો</Text>
            </Pressable>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.6)",
    justifyContent: "center",
    alignItems: "center",
    padding: Spacing.lg,
  },
  modalContainer: {
    width: "100%",
    maxWidth: 500,
    borderRadius: Radius.lg,
    borderWidth: 1,
    padding: Spacing.xl,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.3,
    shadowRadius: 28,
    elevation: 12,
  },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    marginBottom: Spacing.md,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: "700",
  },
  headerSub: {
    fontSize: 12,
    marginTop: 2,
  },
  closeBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: "center",
    alignItems: "center",
  },
  balancePill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: Spacing.md,
    paddingVertical: 8,
    borderRadius: Radius.md,
    borderWidth: 1,
    marginBottom: Spacing.md,
  },
  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "rgba(239, 68, 68, 0.12)",
    borderWidth: 1,
    borderColor: "rgba(239, 68, 68, 0.3)",
    padding: Spacing.sm,
    borderRadius: Radius.md,
    marginBottom: Spacing.md,
  },
  errorText: {
    color: "#EF4444",
    fontSize: 12,
    flex: 1,
  },
  planCard: {
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1.5,
    position: "relative",
  },
  popularBadge: {
    position: "absolute",
    top: -10,
    right: 12,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  popularText: {
    fontSize: 9,
    fontWeight: "800",
    letterSpacing: 0.5,
  },
  planName: {
    fontSize: 15,
    fontWeight: "700",
  },
  planCredits: {
    fontSize: 13,
    fontWeight: "600",
    marginTop: 2,
  },
  planPrice: {
    fontSize: 18,
    fontWeight: "800",
    marginBottom: 6,
  },
  buyBtn: {
    paddingHorizontal: Spacing.md,
    paddingVertical: 6,
    borderRadius: Radius.sm,
    minWidth: 84,
    alignItems: "center",
    justifyContent: "center",
  },
  buyBtnText: {
    fontSize: 12,
    fontWeight: "700",
  },
  footer: {
    marginTop: Spacing.lg,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: "rgba(255,255,255,0.1)",
    paddingTop: Spacing.sm,
  },
  cancelBtn: {
    paddingVertical: Spacing.sm,
    borderRadius: Radius.md,
    alignItems: "center",
    justifyContent: "center",
  },
  cancelBtnText: {
    fontSize: 13,
    fontWeight: "600",
  },
});

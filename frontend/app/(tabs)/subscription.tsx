import { useCallback, useState } from "react";
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";

// Production payment path — enable only when Razorpay keys are configured on
// the backend (RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET) and this flag is set in
// the Vercel/Expo environment. Until then the dev mock purchase is used.
const RAZORPAY_ENABLED = process.env.EXPO_PUBLIC_RAZORPAY_ENABLED === "1";

function loadRazorpayScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof document === "undefined") {
      reject(new Error("Razorpay checkout requires a browser"));
      return;
    }
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }
    const s = document.createElement("script");
    s.src = src;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Could not load payment gateway"));
    document.head.appendChild(s);
  });
}

async function buyWithRazorpay(planId: string): Promise<{ balance: number; total_used: number }> {
  // 1. Server creates the Razorpay order (server resolves plan + price).
  const order = await api.razorpayCreateOrder(planId);
  // 2. Open Razorpay checkout with the order id; server never trusts client price.
  await loadRazorpayScript("https://checkout.razorpay.com/v1/checkout.js");
  const payment = await new Promise<any>((resolve, reject) => {
    const Razorpay = (window as any).Razorpay;
    if (!Razorpay) {
      reject(new Error("Payment gateway unavailable"));
      return;
    }
    const rz = new Razorpay({
      key: order.key_id,
      amount: order.amount_paise,
      currency: order.currency,
      order_id: order.order_id,
      name: "NyaySetu Pro",
      description: order.plan?.name || "",
      handler: (response: any) => resolve(response),
      modal: { ondismiss: () => reject(new Error("Payment cancelled")) },
    });
    rz.open();
  });
  // 3. Server-side verification + idempotent credit grant.
  const verified = await api.razorpayVerify({
    plan_id: planId,
    order_id: order.order_id,
    payment_id: payment.razorpay_payment_id,
    signature: payment.razorpay_signature,
  });
  return { balance: verified.balance, total_used: 0 };
}

export default function Subscription() {
  const { colors, isDark } = useTheme();
  const [plans, setPlans] = useState<any[]>([]);
  const [wallet, setWallet] = useState({ balance: 0, total_used: 0 });
  const [buying, setBuying] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [p, w] = await Promise.all([
        api.plans().catch(() => []),
        api.wallet().catch(() => ({ balance: 0, total_used: 0 })),
      ]);
      setPlans(Array.isArray(p) ? p : []);
      if (w && typeof w === "object") setWallet(w);
    } catch {
      setPlans([]);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const buy = async (id: string) => {
    setBuying(id);
    try {
      const res = RAZORPAY_ENABLED ? await buyWithRazorpay(id) : await api.purchase(id);
      setWallet({ balance: res.balance, total_used: wallet.total_used });
      Alert.alert("Payment Successful", `Credits added to your wallet. New balance: ${res.balance} templates.`);
    } catch (e: any) {
      Alert.alert("Payment Failed", e?.message || "Payment could not be completed");
    } finally {
      setBuying(null);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <ScrollView contentContainerStyle={{ paddingBottom: Spacing.xxxl }}>
        <LinearGradient
          colors={isDark ? ["#0B1B3D", "#061024"] : ["#0B1B3D", "#112240"]}
          style={styles.hero}
        >
          <Text style={styles.heroLabel}>YOUR WALLET</Text>
          <Text style={styles.heroBalance}>{wallet.balance}</Text>
          <Text style={styles.heroSub}>Templates Remaining</Text>
          <View style={styles.heroStats}>
            <View style={styles.heroStat}>
              <Text style={styles.heroStatVal}>{wallet.total_used}</Text>
              <Text style={styles.heroStatLbl}>Used</Text>
            </View>
            <View style={styles.heroDivider} />
            <View style={styles.heroStat}>
              <Text style={styles.heroStatVal}>₹9</Text>
              <Text style={styles.heroStatLbl}>Per Template</Text>
            </View>
          </View>
        </LinearGradient>

        <Text style={[styles.sectionTitle, { color: colors.onSurface }]}>Choose your plan</Text>
        <Text style={[styles.sectionSub, { color: colors.muted }]}>
          Credit packs — valid until consumed
        </Text>

        <View style={{ paddingHorizontal: Spacing.lg, gap: Spacing.md }}>
          {plans.map((p) => {
            const isSingle = p.id === "single";
            const isPopular = p.popular;
            return (
              <View
                key={p.id}
                style={[
                  styles.planCard,
                  {
                    backgroundColor: colors.surfaceSecondary,
                    borderColor: isPopular ? colors.brandPrimary : colors.border,
                    borderWidth: isPopular ? 2 : 1,
                  },
                ]}
              >
                {isPopular ? (
                  <View style={[styles.popularBadge, { backgroundColor: colors.brandPrimary }]}>
                    <Text style={{ color: colors.onBrandPrimary, fontWeight: "800", fontSize: 10, letterSpacing: 1 }}>
                      MOST POPULAR
                    </Text>
                  </View>
                ) : null}
                <View style={styles.planTop}>
                  <View style={{ flex: 1 }}>
                    <Text style={{ color: colors.onSurface, fontSize: 16, fontWeight: "700" }}>{p.name}</Text>
                    <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }}>
                      {isSingle ? "One-time payment" : `${p.credits} template credits`}
                    </Text>
                  </View>
                  <View style={{ alignItems: "flex-end" }}>
                    <Text style={{ color: colors.brandPrimary, fontSize: 26, fontWeight: "800", fontFamily: "serif" }}>
                      ₹{p.price}
                    </Text>
                    {!isSingle && (
                      <Text style={{ color: colors.muted, fontSize: 11 }}>≈ ₹{p.per_template}/template</Text>
                    )}
                  </View>
                </View>
                {!isSingle && (
                  <View style={[styles.savingRow, { backgroundColor: colors.brandTertiary }]}>
                    <Ionicons name="trending-down" size={14} color={colors.onBrandTertiary} />
                    <Text style={{ color: colors.onBrandTertiary, fontSize: 12, fontWeight: "700", marginLeft: 4 }}>
                      Save {Math.round((1 - p.per_template / 9) * 100)}% vs ₹9/template
                    </Text>
                  </View>
                )}
                <Pressable
                  testID={`buy-${p.id}`}
                  onPress={() => buy(p.id)}
                  disabled={buying === p.id}
                  style={[styles.buyBtn, { backgroundColor: colors.brand, opacity: buying === p.id ? 0.6 : 1 }]}
                >
                  <Text style={{ color: "#FFF", fontWeight: "700", fontSize: 14 }}>
                    {buying === p.id ? "Processing..." : isSingle ? "Buy 1 Template" : "Purchase"}
                  </Text>
                </Pressable>
              </View>
            );
          })}
        </View>

        <View style={[styles.info, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
          <Ionicons name="shield-checkmark" size={20} color={colors.brandPrimary} />
          <View style={{ flex: 1, marginLeft: Spacing.sm }}>
            <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 13 }}>Secure Payment</Text>
            <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }}>
              Payments powered by Razorpay. Credits added after successful verification.
            </Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  hero: {
    margin: Spacing.lg,
    borderRadius: Radius.lg,
    padding: Spacing.xl,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(197,160,89,0.2)",
  },
  heroLabel: { color: "#C5A059", fontSize: 11, letterSpacing: 2, fontWeight: "700" },
  heroBalance: { color: "#FFF", fontSize: 56, fontWeight: "800", fontFamily: "serif" },
  heroSub: { color: "#A6B1C2", fontSize: 13 },
  heroStats: { flexDirection: "row", marginTop: Spacing.lg, alignItems: "center" },
  heroStat: { paddingHorizontal: Spacing.lg, alignItems: "center" },
  heroStatVal: { color: "#FFF", fontSize: 18, fontWeight: "700" },
  heroStatLbl: { color: "#A6B1C2", fontSize: 11 },
  heroDivider: { width: 1, height: 30, backgroundColor: "rgba(255,255,255,0.15)" },
  sectionTitle: { fontSize: 18, fontWeight: "700", marginTop: Spacing.md, paddingHorizontal: Spacing.lg, fontFamily: "serif" },
  sectionSub: { fontSize: 12, paddingHorizontal: Spacing.lg, marginBottom: Spacing.md },
  planCard: { padding: Spacing.lg, borderRadius: Radius.lg, position: "relative" },
  popularBadge: { position: "absolute", top: -10, right: Spacing.lg, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  planTop: { flexDirection: "row", alignItems: "flex-start" },
  savingRow: { flexDirection: "row", alignItems: "center", paddingHorizontal: Spacing.md, paddingVertical: 6, borderRadius: 8, marginTop: Spacing.md, alignSelf: "flex-start" },
  buyBtn: { marginTop: Spacing.md, paddingVertical: Spacing.md, borderRadius: Radius.md, alignItems: "center" },
  info: { flexDirection: "row", alignItems: "center", margin: Spacing.lg, padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1 },
});

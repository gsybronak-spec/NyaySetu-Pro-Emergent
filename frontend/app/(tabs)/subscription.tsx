import { useCallback, useEffect, useState } from "react";
import { Alert, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router, useFocusEffect } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAppLanguage } from "@/src/context/AppLanguageContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";
import { DesktopPage } from "@/src/components/DesktopPage";
import { safeBack } from "@/src/utils/navigation";
import { useAuth } from "@/src/context/AuthContext";
import { getCachedPlans, setCachedPlans, getCachedWallet, setCachedWallet } from "@/src/constants/plans";
import {
  loadRazorpayScript,
  preloadRazorpayScript,
  prepareRazorpayModal,
  RAZORPAY_THEME_COLOR,
  RAZORPAY_BACKDROP_COLOR,
  RAZORPAY_LOGO_URL,
} from "@/src/utils/razorpay";

// Production payment path — enable only when Razorpay keys are configured on
// the backend (RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET) and this flag is set in
// the Vercel/Expo environment. Until then the dev mock purchase is used.
const RAZORPAY_ENABLED = process.env.EXPO_PUBLIC_RAZORPAY_ENABLED === "1";

async function buyWithRazorpay(planId: string, user?: any): Promise<{ balance: number; total_used: number }> {
  // Parallelize server order creation and client script readiness check
  const [order] = await Promise.all([
    api.razorpayCreateOrder(planId),
    Platform.OS === 'web' ? loadRazorpayScript() : Promise.resolve(),
  ]);

  // Ensure viewport is stabilized and virtual keyboard is dismissed
  prepareRazorpayModal();

  let paymentId = "";
  let signature = "";

  if (Platform.OS === 'web') {
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
        description: order.plan?.name || "Legal Draft Credits",
        image: RAZORPAY_LOGO_URL,
        prefill: {
          name: user?.name_en || user?.name_gu || "",
          email: user?.email || "",
          contact: user?.mobile || "",
        },
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
    const RazorpayCheckout = require('react-native-razorpay').default;
    const payment = await RazorpayCheckout.open({
      key: order.key_id || process.env.EXPO_PUBLIC_RAZORPAY_KEY_ID,
      amount: order.amount_paise,
      currency: order.currency || "INR",
      name: "NyaySetu Pro",
      description: order.plan?.name || "Legal Draft Credits",
      image: RAZORPAY_LOGO_URL,
      order_id: order.order_id,
      prefill: {
        name: user?.name_en || user?.name_gu || "",
        email: user?.email || "",
        contact: user?.mobile || "",
      },
      theme: { color: RAZORPAY_THEME_COLOR },
    });
    paymentId = payment.razorpay_payment_id;
    signature = payment.razorpay_signature;
  }

  const verified = await api.razorpayVerify({
    plan_id: planId,
    order_id: order.order_id,
    payment_id: paymentId,
    signature: signature,
  });
  return { balance: verified.balance, total_used: 0 };
}

export default function Subscription() {
  const { colors, isDark } = useTheme();
  const { t, ui } = useAppLanguage();
  const { isDesktop } = useResponsive();
  const insets = useSafeAreaInsets();
  const { user } = useAuth();

  // Instant render from cache — 0ms blank delay
  const [plans, setPlans] = useState<any[]>(() => getCachedPlans());
  const [wallet, setWallet] = useState(() => getCachedWallet() || {
    balance: user?.wallet_balance ?? 0,
    total_used: user?.total_credits_used ?? 0,
  });
  const [buying, setBuying] = useState<string | null>(null);

  // Proactively prefetch Razorpay Checkout script in background
  useEffect(() => {
    preloadRazorpayScript();
  }, []);

  const isUnlimited = Boolean(user?.unlimited_access || user?.is_owner || user?.is_partner || (wallet as any)?.unlimited || (wallet as any)?.unlimited_access);

  useFocusEffect(useCallback(() => {
    let active = true;
    (async () => {
      try {
        const [p, w] = await Promise.all([
          api.plans().catch(() => getCachedPlans()),
          api.wallet().catch(() => getCachedWallet() || { balance: user?.wallet_balance ?? 0, total_used: user?.total_credits_used ?? 0 }),
        ]);
        if (active && Array.isArray(p) && p.length > 0) {
          setPlans(p);
          setCachedPlans(p);
        }
        if (active && w && typeof w === "object") {
          setWallet(w);
          setCachedWallet(w);
        }
      } catch {
        // Retain current plans and wallet gracefully
      }
    })();
    return () => {
      active = false;
    };
  }, [user?.wallet_balance]));

  const buy = async (id: string) => {
    setBuying(id);
    try {
      const res = RAZORPAY_ENABLED ? await buyWithRazorpay(id, user) : await api.purchase(id);
      setWallet({ balance: res.balance, total_used: wallet.total_used });
      const okMsg = ui(
        `Credits added to your wallet. New balance: ${res.balance} templates.`,
        `તમારા વૉલેટમાં ક્રેડિટ્સ ઉમેરાઈ ગઈ છે. નવું બેલેન્સ: ${res.balance} અરજીઓ.`
      );
      if (Platform.OS === "web" && typeof window !== "undefined") {
        window.alert(`${ui("Payment Successful", "ચુકવણી સફળ")} — ${okMsg}`);
      } else {
        Alert.alert(ui("Payment Successful", "ચુકવણી સફળ"), okMsg);
      }
    } catch (e: any) {
      const failMsg = e?.message || ui("Payment could not be completed", "ચુકવણી પૂર્ણ થઈ શકી નથી");
      if (Platform.OS === "web" && typeof window !== "undefined") {
        window.alert(failMsg);
      } else {
        Alert.alert(ui("Payment Failed", "ચુકવણી નિષ્ફળ"), failMsg);
      }
    } finally {
      setBuying(null);
    }
  };

  const renderPlanCard = (p: any, wide: boolean) => {
    const isSingle = p.id === "single";
    const isPopular = p.popular;
    return (
      <View
        key={p.id}
        style={[
          wide ? styles.dPlanCard : styles.planCard,
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
              {ui("MOST POPULAR", "સૌથી લોકપ્રિય")}
            </Text>
          </View>
        ) : null}
        <View style={styles.planTop}>
          <View style={{ flex: 1 }}>
            <Text style={{ color: colors.onSurface, fontSize: 16, fontWeight: "700" }}>{p.name}</Text>
            <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }}>
              {isSingle ? ui("One-time payment", "એક વખતની ચુકવણી") : ui(`${p.credits} template credits`, `${p.credits} અરજી ક્રેડિટ્સ`)}
            </Text>
          </View>
          <View style={{ alignItems: "flex-end" }}>
            <Text style={{ color: colors.brandPrimary, fontSize: 26, fontWeight: "800", fontFamily: "serif" }}>
              ₹{p.price}
            </Text>
            {!isSingle && (
              <Text style={{ color: colors.muted, fontSize: 11 }}>{ui(`≈ ₹${p.per_template}/template`, `≈ ₹${p.per_template}/અરજી`)}</Text>
            )}
          </View>
        </View>
        {!isSingle && (
          <View style={[styles.savingRow, { backgroundColor: colors.brandTertiary }]}>
            <Ionicons name="trending-down" size={14} color={colors.onBrandTertiary} />
            <Text style={{ color: colors.onBrandTertiary, fontSize: 12, fontWeight: "700", marginLeft: 4 }}>
              {ui(`Save ${Math.round((1 - p.per_template / 9) * 100)}% vs ₹9/template`, `₹9/અરજીની સામે ${Math.round((1 - p.per_template / 9) * 100)}% બચત`)}
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
            {buying === p.id ? ui("Processing...", "પ્રક્રિયા ચાલુ છે...") : isSingle ? ui("Buy 1 Template", "૧ અરજી ખરીદો") : ui("Purchase", "ખરીદો")}
          </Text>
        </Pressable>
      </View>
    );
  };

  // ------------------------- DESKTOP -------------------------
  if (isDesktop) {
    return (
      <DesktopPage
        title={t("tabPlansWallet")}
        subtitle={ui("Credit packs — valid until consumed", "ક્રેડિટ પેક — વપરાય ત્યાં સુધી માન્ય")}
        onBack={() => safeBack("/(tabs)/home")}
      >
        <LinearGradient
          colors={isDark ? ["#0B1B3D", "#061024"] : ["#0B1B3D", "#112240"]}
          style={styles.dHero}
        >
          <View style={{ flex: 1 }}>
            <Text style={styles.heroLabel}>
              {isUnlimited
                ? (user?.is_owner ? ui("OWNER UNLIMITED ACCESS", "માલિક અમર્યાદિત ઍક્સેસ") : ui("PARTNER UNLIMITED ACCESS", "પાર્ટનર અમર્યાદિત ઍક્સેસ"))
                : ui("YOUR WALLET", "તમારું વૉલેટ")}
            </Text>
            <View style={{ flexDirection: "row", alignItems: "baseline", marginTop: 8 }}>
              <Text style={styles.heroBalance}>{isUnlimited ? t("unlimited") : wallet.balance}</Text>
              <Text style={styles.heroSub}>
                {isUnlimited ? ui(" Templates Access Active", " અરજીઓનો ઍક્સેસ સક્રિય") : ui(" Templates Remaining", " અરજીઓ બાકી")}
              </Text>
            </View>
            <Text style={{ color: "#A6B1C2", fontSize: 13, marginTop: 8 }}>
              {isUnlimited
                ? ui("You have permanent unlimited access to all templates. No credits are ever deducted.", "તમારી પાસે બધી અરજીઓનો કાયમી અમર્યાદિત ઍક્સેસ છે. કોઈ ક્રેડિટ કપાશે નહીં.")
                : ui("Each generated document consumes 1 template credit. Credits never expire.", "દરેક તૈયાર થતા દસ્તાવેજ માટે ૧ ક્રેડિટ વપરાય છે. ક્રેડિટ્સ ક્યારેય એક્સપાયર થતી નથી.")}
            </Text>
          </View>
          <View style={styles.dHeroStats}>
            <View style={styles.heroStat}>
              <Text style={styles.heroStatVal}>{wallet.total_used}</Text>
              <Text style={styles.heroStatLbl}>{ui("Used", "વપરાયેલ")}</Text>
            </View>
            <View style={styles.heroDivider} />
            <View style={styles.heroStat}>
              <Text style={styles.heroStatVal}>₹9</Text>
              <Text style={styles.heroStatLbl}>{ui("Per Template", "પ્રતિ અરજી")}</Text>
            </View>
            <View style={styles.heroDivider} />
            <View style={styles.heroStat}>
              <Text style={styles.heroStatVal}>₹0</Text>
              <Text style={styles.heroStatLbl}>{ui("Expiry", "અવધિ સમાપ્તિ")}</Text>
            </View>
          </View>
        </LinearGradient>

        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: Spacing.lg }}>
          {plans.map((p) => renderPlanCard(p, true))}
        </View>

        <View style={[styles.info, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
          <Ionicons name="shield-checkmark" size={20} color={colors.brandPrimary} />
          <View style={{ flex: 1, marginLeft: Spacing.sm }}>
            <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 13 }}>{ui("Secure Payment", "સુરક્ષિત ચુકવણી")}</Text>
            <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }}>
              {ui("Payments powered by Razorpay. Credits added after successful verification.", "Razorpay દ્વારા સુરક્ષિત ચુકવણી. ચકાસણી બાદ તરત જ ક્રેડિટ ઉમેરાય છે.")}
            </Text>
          </View>
          <Pressable testID="txn-link" onPress={() => router.push("/transactions" as any)}>
            <Text style={{ color: colors.brandPrimary, fontWeight: "700", fontSize: 13 }}>{ui("Transaction History →", "વ્યવહાર ઇતિહાસ →")}</Text>
          </Pressable>
        </View>
      </DesktopPage>
    );
  }

  // ------------------------- MOBILE (unchanged) -------------------------
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
          paddingHorizontal: Spacing.md,
          paddingVertical: 12,
          borderBottomWidth: 1,
          borderBottomColor: colors.border,
        }}
      >
        <Pressable testID="sub-back" onPress={() => safeBack("/(tabs)/home")} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
        </Pressable>
        <Text style={{ fontSize: 17, fontWeight: "700", color: colors.onSurface }}>{t("tabPlansWallet")}</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ paddingBottom: Math.max(90, 60 + insets.bottom + Spacing.xl) }}
      >
        <LinearGradient
          colors={isDark ? ["#0B1B3D", "#061024"] : ["#0B1B3D", "#112240"]}
          style={styles.hero}
        >
          <Text style={styles.heroLabel}>
            {isUnlimited
              ? (user?.is_owner ? ui("OWNER UNLIMITED ACCESS", "માલિક અમર્યાદિત ઍક્સેસ") : ui("PARTNER UNLIMITED ACCESS", "પાર્ટનર અમર્યાદિત ઍક્સેસ"))
              : ui("YOUR WALLET", "તમારું વૉલેટ")}
          </Text>
          <Text style={styles.heroBalance}>{isUnlimited ? t("unlimited") : wallet.balance}</Text>
          <Text style={styles.heroSub}>{isUnlimited ? ui("Templates Access Active", "અરજીઓનો ઍક્સેસ સક્રિય") : ui("Templates Remaining", "અરજીઓ બાકી")}</Text>
          <View style={styles.heroStats}>
            <View style={styles.heroStat}>
              <Text style={styles.heroStatVal}>{wallet.total_used}</Text>
              <Text style={styles.heroStatLbl}>{ui("Used", "વપરાયેલ")}</Text>
            </View>
            <View style={styles.heroDivider} />
            <View style={styles.heroStat}>
              <Text style={styles.heroStatVal}>₹9</Text>
              <Text style={styles.heroStatLbl}>{ui("Per Template", "પ્રતિ અરજી")}</Text>
            </View>
          </View>
        </LinearGradient>

        <Text style={[styles.sectionTitle, { color: colors.onSurface }]}>{ui("Choose your plan", "તમારો પ્લાન પસંદ કરો")}</Text>
        <Text style={[styles.sectionSub, { color: colors.muted }]}>
          {ui("Credit packs — valid until consumed", "ક્રેડિટ પેક — વપરાય ત્યાં સુધી માન્ય")}
        </Text>

        <View style={{ paddingHorizontal: Spacing.lg, gap: Spacing.md }}>
          {plans.map((p) => renderPlanCard(p, false))}
        </View>

        <View style={[styles.info, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
          <Ionicons name="shield-checkmark" size={20} color={colors.brandPrimary} />
          <View style={{ flex: 1, marginLeft: Spacing.sm }}>
            <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 13 }}>{ui("Secure Payment", "સુરક્ષિત ચુકવણી")}</Text>
            <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }}>
              {ui("Payments powered by Razorpay. Credits added after successful verification.", "Razorpay દ્વારા સુરક્ષિત ચુકવણી. ચકાસણી બાદ તરત જ ક્રેડિટ ઉમેરાય છે.")}
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
  // Desktop
  dHero: {
    flexDirection: "row", alignItems: "center",
    padding: Spacing.xl, borderRadius: 16, borderWidth: 1,
    borderColor: "rgba(197,160,89,0.2)",
  },
  dHeroStats: { flexDirection: "row", alignItems: "center", flexShrink: 0 },
  dPlanCard: {
    width: "31%", minWidth: 280, flexGrow: 1,
    padding: Spacing.xl, borderRadius: 16, position: "relative",
  },
});

import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Platform, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router, useFocusEffect } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { useAppLanguage } from "@/src/context/AppLanguageContext";
import { api } from "@/src/api/client";
import { Radius, Spacing } from "@/src/theme/tokens";
import { formatAdvocateName, formatDisplayName } from "@/src/utils/advocate";
import { useResponsive } from "@/src/hooks/useResponsive";
import { DesktopPage, StatCard } from "@/src/components/DesktopPage";
import { TemplateLogicalPair, getActiveTemplatePairs, PERMANENTLY_DELETED_BASE_KEYS } from "@/src/data/templateCatalogPairs";
import { catalogCache } from "@/src/services/catalogCache";
import { LanguageSelectModal } from "@/src/components/LanguageSelectModal";
import { NotificationCenter } from "@/src/components/NotificationCenter";
import { UserGuideModal } from "@/src/components/UserGuideModal";
import { storage } from "@/src/utils/storage";

export default function Home() {
  const { colors, isDark } = useTheme();
  const { user } = useAuth();
  const { appLang, setAppLang, t, ui } = useAppLanguage();
  const { isDesktop } = useResponsive();
  const insets = useSafeAreaInsets();
  const [quote, setQuote] = useState("Justice begins with preparation.");
  const [wallet, setWallet] = useState(() => ({ balance: user?.wallet_balance ?? 0, total_used: user?.total_credits_used ?? 0 }));
  const [allTemplatePairs, setAllTemplatePairs] = useState<TemplateLogicalPair[]>(() =>
    catalogCache.peekActiveTemplatePairs()
  );
  const [visibleHomeCount, setVisibleHomeCount] = useState<number>(10);
  const [totalTemplateCount, setTotalTemplateCount] = useState<number>(() =>
    catalogCache.peekActiveTemplatePairs().length
  );
  const [selectedPair, setSelectedPair] = useState<TemplateLogicalPair | null>(null);
  const [showUserGuideModal, setShowUserGuideModal] = useState<boolean>(false);
  const [drafts, setDrafts] = useState<any[]>([]);
  const [cases, setCases] = useState<any[]>([]);
  const [applications, setApplications] = useState<any[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState(false);

  const isUnlimited = Boolean(user?.unlimited_access || user?.is_owner || user?.is_partner || (wallet as any)?.unlimited || (wallet as any)?.unlimited_access);

  const load = useCallback(async () => {
    let failed = false;
    const [q, w, drs, activePairs] = await Promise.all([
      api.quote().catch(() => { failed = true; return null; }),
      api.wallet().catch(() => { failed = true; return null; }),
      api.drafts().catch(() => { failed = true; return []; }),
      catalogCache.getActiveTemplatePairs(false).catch(() => catalogCache.peekActiveTemplatePairs()),
    ]);
    if (q?.quote) setQuote(q.quote);
    if (w && typeof w === "object") setWallet(w);
    setDrafts(Array.isArray(drs) ? drs : []);
    const active = Array.isArray(activePairs) && activePairs.length > 0 ? activePairs : catalogCache.peekActiveTemplatePairs();
    setAllTemplatePairs(active);
    setTotalTemplateCount(active.length);
    setLoadError(failed);
    // Desktop dashboard only — avoid extra API calls on the mobile home screen.
    if (isDesktop) {
      const [cs, hs] = await Promise.all([
        api.listCases({ status: "active" }).catch(() => []),
        api.history().catch(() => []),
      ]);
      setCases(Array.isArray(cs) ? cs : []);
      setApplications(Array.isArray(hs) ? hs : []);
    }
  }, [isDesktop]);

  useEffect(() => {
    let active = true;
    const unsub = catalogCache.subscribe("active_template_pairs", (pairs) => {
      if (active && Array.isArray(pairs) && pairs.length > 0) {
        setAllTemplatePairs(pairs);
        setTotalTemplateCount(pairs.length);
      }
    });
    return () => {
      active = false;
      unsub();
    };
  }, []);



  const templatePairs = useMemo(() => {
    return allTemplatePairs.slice(0, visibleHomeCount);
  }, [allTemplatePairs, visibleHomeCount]);

  const hasMoreHome = visibleHomeCount < allTemplatePairs.length;
  const remainingHomeCount = Math.max(0, allTemplatePairs.length - visibleHomeCount);
  const nextHomeBatchSize = Math.min(10, remainingHomeCount);

  const handleHomeSeeMore = () => {
    setVisibleHomeCount((prev) => prev + 10);
  };

  // First-time login onboarding popup check
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const seen = await storage.getItem("@nyaysetu_userguide_seen_v1", false);
        if (!seen && active) {
          setShowUserGuideModal(true);
        }
      } catch {
        // Safe ignore
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const onRefresh = async () => {
    setRefreshing(true);
    await Promise.all([
      load(),
      catalogCache.getActiveTemplatePairs(true).catch(() => {}),
    ]);
    setRefreshing(false);
  };

  const hour = new Date().getHours();
  const greeting = hour < 12 ? t("goodMorning") : hour < 18 ? t("goodAfternoon") : t("goodEvening");
  const advocateName = formatDisplayName(user, t("advocate"), appLang);
  const displayQuote = appLang === "gu" && !/[\u0A80-\u0AFF]/.test(quote) ? t("defaultQuote") : quote;

  const renderLanguageToggle = (onDarkHero = false) => (
    <View
      testID="home-language-toggle"
      style={[
        styles.langTogglePill,
        onDarkHero
          ? { backgroundColor: "rgba(255,255,255,0.08)", borderColor: "rgba(197,160,89,0.4)" }
          : { backgroundColor: colors.surfaceSecondary, borderColor: colors.border },
      ]}
    >
      {(["en", "gu"] as const).map((code) => {
        const active = appLang === code;
        return (
          <Pressable
            key={code}
            testID={`home-lang-${code}`}
            onPress={() => setAppLang(code)}
            hitSlop={6}
            style={[
              styles.langToggleOption,
              active && { backgroundColor: colors.brandPrimary },
            ]}
          >
            <Text
              style={[
                styles.langToggleTxt,
                {
                  color: active
                    ? colors.onBrandPrimary
                    : onDarkHero
                      ? "#E2E8F0"
                      : colors.onSurface,
                },
              ]}
            >
              {code === "en" ? "English" : "ગુજરાતી"}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );

  // ------------------------- DESKTOP -------------------------
  if (isDesktop) {
    const quickActions = [
      { key: "create-case", label: t("createCaseBtn"), icon: "add-circle", href: "/case/new" as const, tone: "#C5A059" },
      { key: "browse-templates", label: t("browseTemplates"), icon: "document-text", href: "/(tabs)/templates" as const, tone: "#0B1B3D" },
      { key: "view-cases", label: t("viewCases"), icon: "folder-open", href: "/(tabs)/cases" as const, tone: "#112240" },
      { key: "plans-wallet", label: t("tabPlansWallet"), icon: "diamond", href: "/(tabs)/subscription" as const, tone: "#7A1C1C" },
    ];

    return (
      <DesktopPage
        title={`${greeting}, ${advocateName || t("advocate")}`}
        subtitle={ui("Your legal workspace — pick up where you left off.", "તમારું કાનૂની કાર્યક્ષેત્ર — જ્યાંથી અટક્યા હતા ત્યાંથી આગળ વધો.")}
        actions={
          <View style={{ flexDirection: "row", gap: 10, alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
            {renderLanguageToggle(false)}
            <Pressable
              testID="desktop-guide-btn"
              onPress={() => router.push("/user-guide" as any)}
              style={[styles.desktopGuideBtn, { borderColor: colors.brandPrimary + "40", backgroundColor: colors.surfaceSecondary }]}
            >
              <Ionicons name="book-outline" size={16} color={colors.brandPrimary} />
              <Text style={{ color: colors.onSurface, fontSize: 13, fontWeight: "600", marginLeft: 6 }}>{t("userGuide")}</Text>
            </Pressable>
            <Pressable
              testID="home-search-btn"
              onPress={() => router.push("/search" as any)}
              style={[styles.desktopSearch, { borderColor: colors.border, backgroundColor: colors.surfaceSecondary }]}
            >
              <Ionicons name="search" size={16} color={colors.muted} />
              <Text style={{ color: colors.muted, fontSize: 13, marginLeft: 6 }} numberOfLines={1}>{t("searchCasesTemplatesPlaceholder")}</Text>
            </Pressable>
          </View>
        }
      >
        {loadError ? (
          <View style={[styles.desktopError, { backgroundColor: colors.surfaceSecondary, borderColor: colors.error + "50" }]}>
            <Ionicons name="cloud-offline-outline" size={16} color={colors.error} />
            <Text style={{ color: colors.error, fontSize: 13, flex: 1, marginLeft: 8 }}>
              {t("refreshError")}
            </Text>
            <Pressable testID="home-error-retry" onPress={load}>
              <Text style={{ color: colors.brandPrimary, fontWeight: "700", fontSize: 13 }}>{t("retry")}</Text>
            </Pressable>
          </View>
        ) : null}

        {/* Top welcome + banner */}
        <LinearGradient
          colors={isDark ? ["#0B1B3D", "#061024"] : ["#0B1B3D", "#112240"]}
          style={styles.desktopWelcome}
        >
          <View style={{ flex: 1, paddingRight: Spacing.xl }}>
            <Text style={styles.desktopQuote}>"{displayQuote}"</Text>
            <Text style={styles.desktopWelcomeSub}>
              {t("heroSub")}
            </Text>
          </View>
          <View style={styles.desktopWalletChip}>
            <Ionicons name="wallet" size={16} color="#C5A059" />
            <Text style={styles.desktopWalletTxt}>
              {isUnlimited ? t("unlimitedTemplates") : t("templatesRemainingCount", { n: wallet.balance })}
            </Text>
          </View>
        </LinearGradient>

        {/* Real metrics */}
        <View style={styles.statGrid}>
          <StatCard
            label={t("activeCases")}
            value={cases.length}
            icon="folder-open"
            tone="navy"
            onPress={() => router.push("/(tabs)/cases")}
            testID="stat-card-active-cases"
          />
          <StatCard
            label={t("drafts")}
            value={drafts.length}
            icon="create"
            tone="gold"
            onPress={() => router.push({ pathname: "/vault", params: { tab: "drafts" } })}
            testID="stat-card-drafts"
          />
          <StatCard
            label={t("applicationsGenerated")}
            value={applications.length}
            icon="document-text"
            tone="green"
            onPress={() => router.push({ pathname: "/vault", params: { tab: "documents" } })}
            testID="stat-card-applications-generated"
          />
          <StatCard
            label={t("creditsRemaining")}
            value={isUnlimited ? t("unlimited") : wallet.balance}
            icon="wallet"
            tone="red"
            onPress={() => router.push("/(tabs)/subscription")}
            testID="stat-card-credits-remaining"
          />
        </View>

        {/* Quick actions */}
        <View style={styles.desktopSection}>
          <Text style={[styles.desktopSectionTitle, { color: colors.onSurface }]}>{t("quickActions")}</Text>
          <View style={styles.quickGrid}>
            {quickActions.map((a) => (
              <Pressable
                key={a.key}
                testID={`desktop-quick-${a.key}`}
                onPress={() => router.push(a.href)}
                style={({ pressed }) => [
                  styles.quickCard,
                  { borderColor: colors.border, backgroundColor: colors.surfaceSecondary },
                  pressed && { opacity: 0.85 },
                ]}
              >
                <View style={[styles.quickIcon, { backgroundColor: a.tone + "1A" }]}>
                  <Ionicons name={a.icon as any} size={22} color={a.tone} />
                </View>
                <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 14, marginTop: Spacing.sm }}>
                  {a.label}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>

        {/* Recent cases */}
        {cases.length > 0 && (
          <View style={styles.desktopSection}>
            <View style={styles.desktopRowBetween}>
              <Text style={[styles.desktopSectionTitle, { color: colors.onSurface }]}>{t("recentCases")}</Text>
              <Pressable testID="see-all-cases" onPress={() => router.push("/(tabs)/cases")}>
                <Text style={{ color: colors.brandPrimary, fontWeight: "700" }}>{t("seeAll")}</Text>
              </Pressable>
            </View>
            <View style={styles.recentGrid}>
              {cases.slice(0, 6).map((c) => (
                <Pressable
                  key={c.id}
                  testID={`recent-case-${c.id}`}
                  onPress={() => router.push({ pathname: "/case/[id]", params: { id: c.id } })}
                  style={[styles.recentCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
                >
                  <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
                    <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 14, flex: 1 }} numberOfLines={1}>
                      {c.nickname || c.party_name || c.case_number || ui("Case", "કેસ")}
                    </Text>
                    <View style={[styles.recentPill, { backgroundColor: c.category === "Criminal" ? "#7A1C1C20" : colors.brandTertiary }]}>
                      <Text style={{ color: c.category === "Criminal" ? "#7A1C1C" : colors.onBrandTertiary, fontSize: 10, fontWeight: "700" }}>
                        {c.category || ui("Other", "અન્ય")}
                      </Text>
                    </View>
                  </View>
                  <Text style={{ color: colors.muted, fontSize: 12, marginTop: 6 }} numberOfLines={1}>
                    {c.case_number ? `${c.case_number} • ` : ""}{c.case_type_label || ui("Case", "કેસ")}
                  </Text>
                  {c.party_name ? (
                    <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }} numberOfLines={1}>
                      {c.party_name}
                    </Text>
                  ) : null}
                </Pressable>
              ))}
            </View>
          </View>
        )}

        {/* Most used templates / Top 10 Ordered Templates */}
        <View style={styles.desktopSection}>
          <View style={styles.desktopRowBetween}>
            <Text style={[styles.desktopSectionTitle, { color: colors.onSurface }]}>{t("legalTemplates")}</Text>
            {totalTemplateCount > 0 ? (
              <Pressable testID="see-all-templates" onPress={() => router.push("/(tabs)/templates")}>
                <Text style={{ color: colors.brandPrimary, fontWeight: "700" }}>{t("seeAllCount", { n: totalTemplateCount })}</Text>
              </Pressable>
            ) : null}
          </View>
          {totalTemplateCount === 0 ? (
            <View style={{ padding: Spacing.xl, alignItems: "center", justifyContent: "center", backgroundColor: colors.surfaceSecondary, borderRadius: Radius.md, borderWidth: 1, borderColor: colors.border }}>
              <Ionicons name="document-text-outline" size={36} color={colors.muted} />
              <Text style={{ color: colors.onSurface, fontWeight: "600", marginTop: Spacing.sm }}>{t("noTemplatesAvailable")}</Text>
            </View>
          ) : (
            <>
              <View style={styles.homeTplGridDesktop}>
                {templatePairs.map((pair) => (
                  <Pressable
                    key={pair.baseKey}
                    testID={`tpl-card-${pair.baseKey}`}
                    onPress={() => setSelectedPair(pair)}
                    style={({ pressed }) => [
                      styles.homeTplCardDesktop,
                      { backgroundColor: colors.surfaceSecondary, borderColor: colors.border },
                      pressed && { opacity: 0.88 },
                    ]}
                  >
                    <View style={{ flex: 1 }}>
                      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                        <View style={[styles.catPill, { backgroundColor: colors.surface, borderColor: colors.border }]}>
                          <Text style={{ color: colors.brandPrimary, fontSize: 11, fontWeight: "700" }}>{pair.category}</Text>
                        </View>
                        <Ionicons name="document-text" size={18} color={colors.brandPrimary} />
                      </View>
                      <Text style={{ color: colors.onSurface, fontWeight: "700", marginTop: Spacing.sm, fontSize: 15, lineHeight: 22 }} numberOfLines={2}>
                        {pair.name_gu}
                      </Text>
                      <Text style={{ color: colors.muted, fontSize: 12, marginTop: 3, fontWeight: "500" }} numberOfLines={2}>
                        {pair.name_en}
                      </Text>
                    </View>
                    <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: Spacing.md, paddingTop: Spacing.xs, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border }}>
                      <Text style={{ color: colors.brandPrimary, fontSize: 12, fontWeight: "600" }}>{t("draftActionCue")}</Text>
                      <Ionicons name="chevron-forward" size={16} color={colors.brandPrimary} />
                    </View>
                  </Pressable>
                ))}
              </View>
              {hasMoreHome ? (
                <Pressable
                  testID="desktop-see-more-templates"
                  onPress={handleHomeSeeMore}
                  style={[styles.seeMoreBtn, { backgroundColor: colors.brandPrimary }]}
                >
                  <Text style={styles.seeMoreBtnText}>
                    {t("seeMoreBatch", { batch: nextHomeBatchSize, remaining: remainingHomeCount })}
                  </Text>
                  <Ionicons name="chevron-down" size={18} color="#FFF" />
                </Pressable>
              ) : (
                <Pressable
                  testID="desktop-see-more-templates"
                  onPress={() => router.push("/(tabs)/templates")}
                  style={[styles.seeMoreBtn, { backgroundColor: colors.surfaceSecondary, borderWidth: 1, borderColor: colors.border }]}
                >
                  <Text style={[styles.seeMoreBtnText, { color: colors.onSurface }]}>
                    {t("allLoadedViewCatalog", { n: totalTemplateCount })}
                  </Text>
                  <Ionicons name="arrow-forward" size={18} color={colors.brandPrimary} />
                </Pressable>
              )}
            </>
          )}
        </View>
        <LanguageSelectModal
          visible={selectedPair !== null}
          onClose={() => setSelectedPair(null)}
          templateNameGu={selectedPair?.name_gu}
          templateNameEn={selectedPair?.name_en}
          category={selectedPair?.category}
          onSelect={(lang) => {
            if (selectedPair) {
              const id = lang === "gu" ? selectedPair.guId : selectedPair.enId;
              router.push({ pathname: "/template/[id]", params: { id, lang } });
              setSelectedPair(null);
            }
          }}
        />
        <UserGuideModal
          visible={showUserGuideModal}
          onClose={() => setShowUserGuideModal(false)}
          onComplete={() => setShowUserGuideModal(false)}
        />
      </DesktopPage>
    );
  }

  // ------------------------- MOBILE (unchanged) -------------------------
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <View style={styles.brandRow}>
          <Image
            source={Platform.OS === "web" ? "/logo.webp" : require("../../assets/images/logo.png")}
            style={styles.brandLogo}
            contentFit="contain"
           accessibilityLabel="NyaySetu Pro Logo" />
          <Text style={[styles.brandName, { color: colors.onSurface }]}>NyaySetu <Text style={{ color: colors.brandPrimary }}>Pro</Text></Text>
        </View>
        <View style={{ flexDirection: "row", gap: Spacing.md, alignItems: "center" }}>
          <Pressable testID="home-guide-btn" onPress={() => router.push("/user-guide" as any)} hitSlop={8}>
            <Ionicons name="book-outline" size={22} color={colors.brandPrimary} />
          </Pressable>
          <NotificationCenter />
          <Pressable testID="home-search-btn" onPress={() => router.push("/search" as any)}>
            <Ionicons name="search" size={22} color={colors.onSurface} />
          </Pressable>
        </View>
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ paddingBottom: Math.max(90, 60 + insets.bottom + Spacing.xl) }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {loadError && (
          <View style={[styles.errorBanner, { backgroundColor: colors.surfaceSecondary, borderColor: colors.error + "50" }]}>
            <Ionicons name="cloud-offline-outline" size={16} color={colors.error} />
            <Text style={{ color: colors.error, fontSize: 12, flex: 1, marginLeft: 6 }}>
              {t("refreshError")}
            </Text>
            <Pressable testID="home-error-retry" onPress={load} hitSlop={8}>
              <Text style={{ color: colors.brandPrimary, fontWeight: "700", fontSize: 12 }}>{t("retry")}</Text>
            </Pressable>
          </View>
        )}
        {/* Welcome Card */}
        <LinearGradient
          colors={isDark ? ["#0B1B3D", "#112240"] : ["#0B1B3D", "#1D2D50"]}
          style={styles.welcome}
        >
          <View style={styles.welcomeTopRow}>
            <Text style={styles.welcomeGreet}>{greeting},</Text>
            {renderLanguageToggle(true)}
          </View>
          <Text style={styles.welcomeName}>{advocateName}</Text>
          <View style={styles.quoteRow}>
            <View style={styles.quoteBar} />
            <Text style={styles.quote}>"{displayQuote}"</Text>
          </View>
          <View style={styles.walletChip}>
            <Ionicons name="wallet" size={14} color="#C5A059" />
            <Text style={styles.walletTxt}>
              {isUnlimited ? t("unlimitedTemplates") : t("templatesRemainingCount", { n: wallet.balance })}
            </Text>
          </View>
        </LinearGradient>

        {/* Action Cards */}
        <View style={styles.actionRow}>
          <Pressable
            testID="home-add-case-card"
            onPress={() => router.push("/case/new")}
            style={[styles.actionCard, { backgroundColor: colors.brandPrimary }]}
          >
            <Ionicons name="add-circle" size={26} color={colors.onBrandPrimary} />
            <Text style={[styles.actionTitle, { color: colors.onBrandPrimary }]}>{t("addNewCase")}</Text>
            <Text style={[styles.actionSub, { color: colors.onBrandPrimary, opacity: 0.85 }]}>{t("createCaseSub")}</Text>
          </Pressable>
          <Pressable
            testID="home-my-cases-card"
            onPress={() => router.push("/(tabs)/cases")}
            style={[styles.actionCard, { backgroundColor: colors.brand }]}
          >
            <Ionicons name="folder-open" size={26} color="#FFF" />
            <Text style={[styles.actionTitle, { color: "#FFF" }]}>{t("tabMyCases")}</Text>
            <Text style={[styles.actionSub, { color: "#FFF", opacity: 0.75 }]}>{t("manageAllCases")}</Text>
          </Pressable>
        </View>



        {/* Quick Access: Documents Vault & Drafts */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.onSurface }]}>{t("quickAccess")}</Text>
          <View style={{ flexDirection: "row", gap: Spacing.md }}>
            {[
              { key: "documents-vault", label: "Documents Vault", displayLabel: t("documentsVault"), icon: "file-tray-full", color: "#C5A059", tab: "documents" },
              { key: "drafts", label: "Drafts", displayLabel: t("drafts"), icon: "create", color: "#C5A059", tab: "drafts" },
            ].map((c) => (
              <Pressable
                key={c.key}
                testID={`cat-${c.key}`}
                onPress={() => router.push({ pathname: "/vault", params: { tab: c.tab } })}
                style={[styles.catCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
              >
                <View style={[styles.catIcon, { backgroundColor: c.color + "20" }]}>
                  <Ionicons name={c.icon as any} size={22} color={c.color} />
                </View>
                <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 15 }}>{c.displayLabel}</Text>
              </Pressable>
            ))}
          </View>
        </View>

        {/* Legal Templates - First 10 Templates (5 rows x 2 cards) */}
        <View style={styles.section}>
          <View style={styles.rowBetween}>
            <Text style={[styles.sectionTitle, { color: colors.onSurface, marginBottom: 0 }]}>{t("legalTemplates")}</Text>
            {totalTemplateCount > 0 ? (
              <Pressable testID="see-all-templates" onPress={() => router.push("/(tabs)/templates")}>
                <Text style={{ color: colors.brandPrimary, fontWeight: "700" }}>{t("seeAllCount", { n: totalTemplateCount })}</Text>
              </Pressable>
            ) : null}
          </View>
          {totalTemplateCount === 0 ? (
            <View style={{ padding: Spacing.lg, alignItems: "center", justifyContent: "center", backgroundColor: colors.surfaceSecondary, borderRadius: Radius.md, borderWidth: 1, borderColor: colors.border, marginTop: Spacing.sm }}>
              <Ionicons name="document-text-outline" size={32} color={colors.muted} />
              <Text style={{ color: colors.onSurface, fontWeight: "600", marginTop: Spacing.xs, fontSize: 13 }}>{t("noTemplatesAvailable")}</Text>
            </View>
          ) : (
            <>
              <View style={styles.homeTplGrid}>
                {templatePairs.map((pair) => (
                  <Pressable
                    key={pair.baseKey}
                    testID={`tpl-card-${pair.baseKey}`}
                    onPress={() => setSelectedPair(pair)}
                    style={({ pressed }) => [
                      styles.homeTplCard,
                      { backgroundColor: colors.surfaceSecondary, borderColor: colors.border },
                      pressed && { opacity: 0.88 },
                    ]}
                  >
                    <View style={{ flex: 1 }}>
                      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                        <View style={[styles.catPill, { backgroundColor: colors.surface, borderColor: colors.border }]}>
                          <Text style={{ color: colors.brandPrimary, fontSize: 10, fontWeight: "700" }}>{pair.category}</Text>
                        </View>
                        <Ionicons name="document-text" size={16} color={colors.brandPrimary} />
                      </View>
                      <Text style={{ color: colors.onSurface, fontWeight: "700", marginTop: Spacing.xs, fontSize: 15, lineHeight: 21 }} numberOfLines={2}>
                        {pair.name_gu}
                      </Text>
                      <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2, fontWeight: "500" }} numberOfLines={2}>
                        {pair.name_en}
                      </Text>
                    </View>
                    <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: Spacing.sm, paddingTop: Spacing.xs, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border }}>
                      <Text style={{ color: colors.brandPrimary, fontSize: 11, fontWeight: "600" }}>{t("draftActionCue")}</Text>
                      <Ionicons name="chevron-forward" size={14} color={colors.brandPrimary} />
                    </View>
                  </Pressable>
                ))}
              </View>
              {hasMoreHome ? (
                <Pressable
                  testID="home-see-more-templates"
                  onPress={handleHomeSeeMore}
                  style={[styles.seeMoreBtn, { backgroundColor: colors.brandPrimary }]}
                >
                  <Text style={styles.seeMoreBtnText}>
                    {t("seeMoreBatch", { batch: nextHomeBatchSize, remaining: remainingHomeCount })}
                  </Text>
                  <Ionicons name="chevron-down" size={18} color="#FFF" />
                </Pressable>
              ) : (
                <Pressable
                  testID="home-see-more-templates"
                  onPress={() => router.push("/(tabs)/templates")}
                  style={[styles.seeMoreBtn, { backgroundColor: colors.surfaceSecondary, borderWidth: 1, borderColor: colors.border }]}
                >
                  <Text style={[styles.seeMoreBtnText, { color: colors.onSurface }]}>
                    {t("allLoadedViewCatalog", { n: totalTemplateCount })}
                  </Text>
                  <Ionicons name="arrow-forward" size={18} color={colors.brandPrimary} />
                </Pressable>
              )}
            </>
          )}
        </View>
      </ScrollView>
      <LanguageSelectModal
        visible={selectedPair !== null}
        onClose={() => setSelectedPair(null)}
        templateNameGu={selectedPair?.name_gu}
        templateNameEn={selectedPair?.name_en}
        category={selectedPair?.category}
        onSelect={(lang) => {
          const pair = selectedPair;
          setSelectedPair(null);
          if (pair) {
            const id = lang === "gu" ? pair.guId : pair.enId;
            router.push({ pathname: "/template/[id]", params: { id, lang } });
          }
        }}
      />
      <UserGuideModal
        visible={showUserGuideModal}
        onClose={() => setShowUserGuideModal(false)}
        onComplete={() => setShowUserGuideModal(false)}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  brandRow: { flexDirection: "row", alignItems: "center", gap: Spacing.sm },
  brandLogo: { width: 28, height: 30 },
  brandName: { fontSize: 18, fontWeight: "800", fontFamily: "serif" },
  welcome: {
    margin: Spacing.lg,
    padding: Spacing.xl,
    borderRadius: Radius.lg,
    borderWidth: 1,
    borderColor: "rgba(197,160,89,0.2)",
  },
  welcomeTopRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: Spacing.sm,
    marginBottom: 4,
  },
  langTogglePill: {
    flexDirection: "row",
    alignItems: "center",
    padding: 3,
    borderRadius: 999,
    borderWidth: 1,
    gap: 2,
    flexShrink: 0,
  },
  langToggleOption: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
  },
  langToggleTxt: {
    fontSize: 11,
    fontWeight: "700",
  },
  welcomeGreet: { color: "#C5A059", fontSize: 12, letterSpacing: 1.2, textTransform: "uppercase", fontWeight: "700", flexShrink: 1 },
  welcomeName: { color: "#FDFDFD", fontSize: 24, fontFamily: "serif", fontWeight: "700", marginTop: 4 },
  quoteRow: { flexDirection: "row", alignItems: "center", marginTop: Spacing.md },
  quoteBar: { width: 3, height: 20, backgroundColor: "#C5A059", marginRight: Spacing.sm },
  quote: { color: "#D1D8E5", fontStyle: "italic", flex: 1, fontSize: 13 },
  walletChip: {
    flexDirection: "row", alignItems: "center", alignSelf: "flex-start",
    gap: 6, backgroundColor: "rgba(197,160,89,0.1)",
    paddingHorizontal: Spacing.md, paddingVertical: 6,
    borderRadius: Radius.pill, marginTop: Spacing.md,
    borderWidth: 1, borderColor: "rgba(197,160,89,0.35)",
  },
  walletTxt: { color: "#C5A059", fontSize: 12, fontWeight: "700" },
  errorBanner: {
    flexDirection: "row", alignItems: "center", marginHorizontal: Spacing.lg, marginTop: Spacing.md,
    padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1,
  },
  actionRow: { flexDirection: "row", paddingHorizontal: Spacing.lg, gap: Spacing.md },
  actionCard: { flex: 1, padding: Spacing.lg, borderRadius: Radius.lg, gap: 6 },
  actionTitle: { fontSize: 16, fontWeight: "800", marginTop: Spacing.sm },
  actionSub: { fontSize: 11 },
  section: { paddingHorizontal: Spacing.lg, marginTop: Spacing.xl },
  sectionTitle: { fontSize: 17, fontWeight: "700", marginBottom: Spacing.md, fontFamily: "serif" },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  catCard: {
    flex: 1, padding: Spacing.lg, borderRadius: Radius.md, borderWidth: 1,
    alignItems: "flex-start", gap: Spacing.sm,
  },
  catIcon: { width: 40, height: 40, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  tplCard: {
    width: "48%", padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1, minHeight: 110,
  },
  catPill: {
    alignSelf: "flex-start",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    borderWidth: 1,
  },
  homeTplGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    marginTop: Spacing.md,
    gap: Spacing.sm,
  },
  homeTplCard: {
    width: "48.5%",
    padding: Spacing.sm,
    borderRadius: Radius.md,
    borderWidth: 1,
    justifyContent: "space-between",
    minHeight: 145,
    marginBottom: Spacing.xs,
  },
  homeTplGridDesktop: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    gap: Spacing.md,
  },
  homeTplCardDesktop: {
    width: "48.5%",
    padding: Spacing.md,
    borderRadius: 14,
    borderWidth: 1,
    justifyContent: "space-between",
    minHeight: 155,
    marginBottom: Spacing.sm,
  },
  homeTplBtnRow: {
    flexDirection: "row",
    gap: 6,
    marginTop: Spacing.sm,
  },
  homeLangBtn: {
    flex: 1,
    paddingVertical: 6,
    borderRadius: Radius.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  homeLangBtnText: {
    fontSize: 11,
    fontWeight: "700",
  },
  seeMoreBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    marginTop: Spacing.lg,
    paddingVertical: 12,
    paddingHorizontal: Spacing.xl,
    borderRadius: Radius.md,
  },
  seeMoreBtnText: {
    color: "#FFF",
    fontWeight: "700",
    fontSize: 14,
  },
  // Desktop
  desktopGuideBtn: {
    flexDirection: "row", alignItems: "center",
    paddingHorizontal: Spacing.md, paddingVertical: 8, borderRadius: 999, borderWidth: 1,
  },
  desktopSearch: {
    flexDirection: "row", alignItems: "center",
    paddingHorizontal: Spacing.md, paddingVertical: 9, borderRadius: 999, borderWidth: 1,
    minWidth: 190,
  },
  desktopError: {
    flexDirection: "row", alignItems: "center",
    padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1,
  },
  desktopWelcome: {
    flexDirection: "row", alignItems: "center",
    padding: Spacing.xl, borderRadius: 16, borderWidth: 1,
    borderColor: "rgba(197,160,89,0.2)",
  },
  desktopQuote: { color: "#FDFDFD", fontSize: 20, fontFamily: "serif", fontWeight: "700" },
  desktopWelcomeSub: { color: "#A6B1C2", fontSize: 13, marginTop: Spacing.sm, lineHeight: 19 },
  desktopWalletChip: {
    flexDirection: "row", alignItems: "center", gap: 8,
    backgroundColor: "rgba(197,160,89,0.12)", paddingHorizontal: Spacing.lg, paddingVertical: 10,
    borderRadius: 999, borderWidth: 1, borderColor: "rgba(197,160,89,0.35)", flexShrink: 0,
  },
  desktopWalletTxt: { color: "#C5A059", fontSize: 13, fontWeight: "700" },
  statGrid: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.lg },
  desktopSection: { gap: Spacing.md },
  desktopSectionTitle: { fontSize: 18, fontWeight: "700", fontFamily: "serif" },
  desktopRowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  quickGrid: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.md },
  quickCard: {
    width: 220, padding: Spacing.lg, borderRadius: 14, borderWidth: 1,
  },
  quickIcon: { width: 44, height: 44, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  recentGrid: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.md },
  recentCard: { width: "31%", minWidth: 260, padding: Spacing.lg, borderRadius: 14, borderWidth: 1 },
  recentPill: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999 },
  tplGrid: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.md },
  desktopTplCard: {
    width: "23.5%", minWidth: 210, padding: Spacing.md, borderRadius: 14, borderWidth: 1, minHeight: 150,
  },
  desktopTplIcon: { width: 38, height: 38, borderRadius: 10, alignItems: "center", justifyContent: "center" },
});

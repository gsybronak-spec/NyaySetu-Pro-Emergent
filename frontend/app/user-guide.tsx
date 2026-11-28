import React, { useState, useMemo } from "react";
import {
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  useWindowDimensions,
} from "react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAppLanguage } from "@/src/context/AppLanguageContext";
import { Radius, Spacing } from "@/src/theme/tokens";
import { storage } from "@/src/utils/storage";
import { UserGuideModal } from "@/src/components/UserGuideModal";
import { safeBack } from "@/src/utils/navigation";

type GuideTab = "quickstart" | "cases" | "templates" | "pdf" | "wallet" | "faq";

export default function UserGuideScreen() {
  const { colors, isDark } = useTheme();
  const { isGujarati, t, ui } = useAppLanguage();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const isDesktop = width >= 768;

  const [activeTab, setActiveTab] = useState<GuideTab>("quickstart");
  const [searchQuery, setSearchQuery] = useState("");
  const [showInteractiveModal, setShowInteractiveModal] = useState(false);

  const tabs: { key: GuideTab; labelGu: string; labelEn: string; icon: keyof typeof Ionicons.glyphMap }[] = [
    { key: "quickstart", labelGu: "ઝડપી શરૂઆત", labelEn: "Quick Tour", icon: "rocket-outline" },
    { key: "cases", labelGu: "કેસ મેનેજમેન્ટ", labelEn: "Case System", icon: "briefcase-outline" },
    { key: "templates", labelGu: "૨૬ કાનૂની નમૂનાઓ", labelEn: "Templates", icon: "document-text-outline" },
    { key: "pdf", labelGu: "કોર્ટ PDF પ્રિન્ટ", labelEn: "PDF Guidelines", icon: "print-outline" },
    { key: "wallet", labelGu: "વોલેટ અને પ્લાન્સ", labelEn: "Wallet & Plans", icon: "wallet-outline" },
    { key: "faq", labelGu: "વારંવાર પૂછાતા પ્રશ્નો", labelEn: "FAQs", icon: "help-circle-outline" },
  ];

  const handleResetTour = async () => {
    try {
      await storage.removeItem("@nyaysetu_userguide_seen_v1");
    } catch {
      // Safe fallback
    }
    setShowInteractiveModal(true);
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.surface }]} edges={["top"]}>
      {/* Top Navigation Bar */}
      <View style={[styles.topBar, { borderBottomColor: colors.border, backgroundColor: colors.surface }]}>
        <View style={styles.topBarLeft}>
          <Pressable
            testID="guide-back-button"
            onPress={() => safeBack("/(tabs)/profile")}
            style={[styles.backBtn, { backgroundColor: colors.surfaceSecondary }]}
            hitSlop={10}
          >
            <Ionicons name="arrow-back" size={20} color={colors.onSurface} />
          </Pressable>
          <View style={{ marginLeft: Spacing.sm }}>
            <Text style={[styles.pageTitle, { color: colors.onSurface }]}>{t("userGuideFull")}</Text>
            <Text style={[styles.pageSubtitle, { color: colors.muted }]}>
              {ui("NyaySetu Pro Documentation", "ન્યાયસેતુ પ્રો માર્ગદર્શિકા અને માહિતી")}
            </Text>
          </View>
        </View>

        <Pressable
          onPress={() => setShowInteractiveModal(true)}
          style={[styles.interactiveTourBtn, { backgroundColor: colors.brandPrimary }]}
        >
          <Ionicons name="play-circle-outline" size={16} color="#061024" />
          <Text style={styles.interactiveTourText}>{ui("Slide Tour", "ઇન્ટરેક્ટિવ ટુર")}</Text>
        </Pressable>
      </View>

      <View style={[styles.contentLayout, isDesktop && styles.contentLayoutDesktop]}>
        {/* Sidebar / Top Horizontal Tabs */}
        <View style={[styles.tabBarContainer, isDesktop ? [styles.desktopSidebar, { borderRightColor: colors.border }] : null]}>
          <ScrollView
            horizontal={!isDesktop}
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={isDesktop ? styles.desktopTabList : styles.mobileTabList}
          >
            {tabs.map((tab) => {
              const active = activeTab === tab.key;
              return (
                <Pressable
                  key={tab.key}
                  onPress={() => setActiveTab(tab.key)}
                  style={[
                    styles.tabItem,
                    active
                      ? [styles.tabItemActive, { backgroundColor: colors.brand, borderColor: colors.brandPrimary }]
                      : [styles.tabItemInactive, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }],
                  ]}
                >
                  <Ionicons
                    name={tab.icon}
                    size={16}
                    color={active ? colors.brandPrimary : colors.muted}
                  />
                  <View style={{ marginLeft: 8 }}>
                    <Text
                      style={[
                        styles.tabTextGu,
                        { color: active ? "#FFF" : colors.onSurface, fontWeight: active ? "800" : "600" },
                      ]}
                    >
                      {isGujarati ? tab.labelGu : tab.labelEn}
                    </Text>
                  </View>
                </Pressable>
              );
            })}
          </ScrollView>
        </View>

        {/* Tab Detail Body */}
        <ScrollView style={styles.tabBodyScroll} contentContainerStyle={styles.tabBodyContent} showsVerticalScrollIndicator={false}>
          {activeTab === "quickstart" && (
            <View>
              {/* Hero Banner */}
              <LinearGradient
                colors={isDark ? ["#0B1B3D", "#1A365D"] : ["#0B1B3D", "#1A365D"]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.heroBanner}
              >
                <View style={styles.heroBadge}>
                  <Ionicons name="sparkles" size={13} color="#C5A059" />
                  <Text style={{ color: "#C5A059", fontSize: 11, fontWeight: "800", marginLeft: 4 }}>
                    {ui("Court-Ready Legal Applications in 1 Minute", "૧ મિનિટમાં કોર્ટ-માન્ય કાનૂની અરજી")}
                  </Text>
                </View>
                <Text style={styles.heroTitle}>{ui("Welcome to NyaySetu Pro", "ન્યાયસેતુ પ્રો માં આપનું સ્વાગત છે")}</Text>
                <Text style={styles.heroDesc}>
                  {ui(
                    "Fast, paperless legal drafting software built for advocates. This guide helps you use every feature effortlessly.",
                    "ગુજરાતની અદાલતોના વકીલો માટે ખાસ તૈયાર થયેલું ઝડપી, પેપરલેસ લીગલ ડ્રાફ્ટિંગ સોફ્ટવેર. આ માર્ગદર્શિકા તમને દરેક ફીચર સરળતાથી વાપરવામાં મદદ કરશે."
                  )}
                </Text>
              </LinearGradient>

              {/* 3 Step Quick Overview */}
              <Text style={[styles.sectionHeading, { color: colors.onSurface }]}>
                {ui("Create Applications in 3 Simple Steps:", "સરળ ૩ પગલાંમાં અરજી બનાવો:")}
              </Text>

              <View style={[styles.stepCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <View style={[styles.stepNumberBadge, { backgroundColor: colors.brandPrimary }]}>
                  <Text style={styles.stepNumberText}>{ui("1", "૧")}</Text>
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={[styles.stepTitle, { color: colors.onSurface }]}>{ui("Add Case", "કેસ ઉમેરો")}</Text>
                  <Text style={[styles.stepDesc, { color: colors.muted }]}>
                    {ui(
                      "Save district, court name, case number, and party details once.",
                      "જિલ્લો, કોર્ટનું નામ, કેસ નંબર અને વાદી-પ્રતિવાદીનું નામ સેવ કરો."
                    )}
                  </Text>
                </View>
              </View>

              <View style={[styles.stepCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <View style={[styles.stepNumberBadge, { backgroundColor: colors.brandPrimary }]}>
                  <Text style={styles.stepNumberText}>{ui("2", "૨")}</Text>
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={[styles.stepTitle, { color: colors.onSurface }]}>{ui("Select Legal Template", "કાનૂની નમૂનો પસંદ કરો")}</Text>
                  <Text style={[styles.stepDesc, { color: colors.muted }]}>
                    {ui(
                      "Pick exemption, warrant cancellation, adjournment, or vakalatnama. All saved case details auto-fill automatically.",
                      "હાજરી મુક્તિ, વોરંટ રદ, મુદ્દત કે વકાલતનામું પસંદ કરો. કેસની તમામ વિગતો આપોઆપ ભરાઈ જશે."
                    )}
                  </Text>
                </View>
              </View>

              <View style={[styles.stepCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <View style={[styles.stepNumberBadge, { backgroundColor: colors.brandPrimary }]}>
                  <Text style={styles.stepNumberText}>{ui("3", "૩")}</Text>
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={[styles.stepTitle, { color: colors.onSurface }]}>{ui("Download & Share PDF", "પ્રિન્ટ / વોટ્સએપ કરો")}</Text>
                  <Text style={[styles.stepDesc, { color: colors.muted }]}>
                    {ui(
                      "Download court-compliant PDFs with 40mm filing margins straight to your phone or print immediately.",
                      "૪૦mm ડાબા માર્જિન સાથે કોર્ટ-માન્ય PDF તરત ડાઉનલોડ કરો અથવા સીધી પ્રિન્ટ કાઢો."
                    )}
                  </Text>
                </View>
              </View>
            </View>
          )}

          {activeTab === "cases" && (
            <View>
              <Text style={[styles.sectionHeading, { color: colors.onSurface }]}>{ui("Case Management System", "કેસ મેનેજમેન્ટ સિસ્ટમ")}</Text>
              <Text style={[styles.sectionSub, { color: colors.muted }]}>
                {ui(
                  "Saving case details once prevents retyping court and party names for every application.",
                  "કેસ સેવ કરવાથી દરેક અરજીમાં કોર્ટ અને પક્ષકારોની વિગત વારંવાર લખવાની જરૂર રહેતી નથી."
                )}
              </Text>

              {/* Visual Mockup Card */}
              <View style={[styles.visualCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <View style={[styles.visualHeader, { backgroundColor: colors.brand }]}>
                  <Ionicons name="folder-open" size={16} color="#C5A059" />
                  <Text style={{ color: "#FFF", fontWeight: "700", fontSize: 13, marginLeft: 6 }}>
                    {ui("New Case Screen", "નવો કેસ ઉમેરવાની સ્ક્રીન")}
                  </Text>
                </View>
                <View style={styles.visualContent}>
                  <Text style={[styles.mockFieldLabel, { color: colors.muted }]}>{ui("1. District & Taluka:", "૧. જિલ્લો અને તાલુકો:")}</Text>
                  <Text style={[styles.mockFieldValue, { color: colors.onSurface }]}>{ui("Ahmedabad → Ahmedabad City", "અમદાવાદ ➔ અમદાવાદ શહેર")}</Text>

                  <Text style={[styles.mockFieldLabel, { color: colors.muted, marginTop: 6 }]}>{ui("2. Court Name:", "૨. કોર્ટનું નામ:")}</Text>
                  <Text style={[styles.mockFieldValue, { color: colors.onSurface }]}>{ui("Court of Chief Judicial Magistrate", "ચીફ જ્યુડિશિયલ મેજીસ્ટ્રેટશ્રીની કોર્ટ")}</Text>

                  <Text style={[styles.mockFieldLabel, { color: colors.muted, marginTop: 6 }]}>{ui("3. Parties:", "૩. પક્ષકારો:")}</Text>
                  <Text style={[styles.mockFieldValue, { color: colors.onSurface }]}>{ui("Complainant: Rajeshkumar Patel | Accused: Maheshbhai Thakor", "ફરિયાદી: રાજેશકુમાર પટેલ | આરોપી: મહેશભાઈ ઠાકોર")}</Text>
                </View>
              </View>

              <View style={[styles.tipBox, { backgroundColor: "rgba(197,160,89,0.12)", borderColor: colors.brandPrimary }]}>
                <Ionicons name="bulb-outline" size={18} color="#8C6A29" />
                <Text style={{ color: colors.onSurface, fontSize: 12, marginLeft: 8, flex: 1, lineHeight: 18 }}>
                  <Text style={{ fontWeight: "800" }}>{ui("Pro Tip: ", "પ્રો ટિપ: ")}</Text>
                  {ui(
                    'If your court is not listed, select "Other" and type your local court name manually.',
                    'જો કોર્ટનું નામ ડ્રોપડાઉનમાં ન મળે તો "અન્ય કોર્ટ" પસંદ કરી તમારી સ્થાનિક કોર્ટનું નામ જાતે ટાઇપ કરી શકો છો.'
                  )}
                </Text>
              </View>
            </View>
          )}

          {activeTab === "templates" && (
            <View>
              <Text style={[styles.sectionHeading, { color: colors.onSurface }]}>{ui("Authoritative Legal Templates", "અધિકૃત કાનૂની નમૂનાઓ")}</Text>
              <Text style={[styles.sectionSub, { color: colors.muted }]}>
                {ui(
                  "Legally vetted court formats in both Gujarati and English tailored for Gujarat Civil & Criminal courts.",
                  "ગુજરાતની સિવિલ અને ક્રિમિનલ કોર્ટોના રૂલ્સ મુજબ વકીલો દ્વારા ચકાસાયેલ પ્રમાણિત લખાણ."
                )}
              </Text>

              <View style={[styles.tableCard, { borderColor: colors.border, backgroundColor: colors.surfaceSecondary }]}>
                <View style={[styles.tableRow, styles.tableHeaderRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableHeaderCell, { color: colors.onSurface, flex: 2 }]}>{ui("Template Name", "નમૂનાનું નામ")}</Text>
                  <Text style={[styles.tableHeaderCell, { color: colors.onSurface, flex: 1 }]}>{ui("Category", "કેટેગરી")}</Text>
                </View>

                <View style={[styles.tableRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableCell, { color: colors.onSurface, flex: 2 }]}>વોરંટ રદ કરવાની અરજી</Text>
                  <Text style={[styles.tableBadge, { color: "#C05621", flex: 1 }]}>{ui("Criminal", "ક્રિમિનલ")}</Text>
                </View>
                <View style={[styles.tableRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableCell, { color: colors.onSurface, flex: 2 }]}>હાજરી મુક્તિ અરજી (Sec 317)</Text>
                  <Text style={[styles.tableBadge, { color: "#C05621", flex: 1 }]}>{ui("Criminal", "ક્રિમિનલ")}</Text>
                </View>
                <View style={[styles.tableRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableCell, { color: colors.onSurface, flex: 2 }]}>એફ.એસ.નો હક બંધ કરવાની અરજી</Text>
                  <Text style={[styles.tableBadge, { color: "#C05621", flex: 1 }]}>{ui("Criminal", "ક્રિમિનલ")}</Text>
                </View>
                <View style={[styles.tableRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableCell, { color: colors.onSurface, flex: 2 }]}>વકાલતનામું (દિવાની / ફોજદારી)</Text>
                  <Text style={[styles.tableBadge, { color: "#2B6CB0", flex: 1 }]}>{ui("Civil / Criminal", "દિવાની / ફોજદારી")}</Text>
                </View>
                <View style={[styles.tableRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableCell, { color: colors.onSurface, flex: 2 }]}>મુદ્દત અરજી (Adjournment)</Text>
                  <Text style={[styles.tableBadge, { color: "#2F855A", flex: 1 }]}>{ui("General", "સામાન્ય")}</Text>
                </View>
                <View style={[styles.tableRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableCell, { color: colors.onSurface, flex: 2 }]}>દસ્તાવેજ પરત લેવાની અરજી</Text>
                  <Text style={[styles.tableBadge, { color: "#2F855A", flex: 1 }]}>{ui("General", "સામાન્ય")}</Text>
                </View>
                <View style={[styles.tableRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableCell, { color: colors.onSurface, flex: 2 }]}>સર્ટિફાઇડ નકલ અરજી</Text>
                  <Text style={[styles.tableBadge, { color: "#2F855A", flex: 1 }]}>{ui("General", "સામાન્ય")}</Text>
                </View>
              </View>

              {/* Special instructions for Warrant cancellation */}
              <View style={[styles.alertCard, { backgroundColor: "rgba(43,108,176,0.08)", borderColor: "#2B6CB0" }]}>
                <Ionicons name="information-circle" size={18} color="#2B6CB0" />
                <View style={{ marginLeft: 8, flex: 1 }}>
                  <Text style={{ color: "#2B6CB0", fontWeight: "800", fontSize: 13 }}>
                    {ui("Update for Warrant Cancellation Applications:", "વોરંટ રદ અરજી માટે નવું અપડેટ:")}
                  </Text>
                  <Text style={{ color: colors.onSurface, fontSize: 12, marginTop: 2, lineHeight: 18 }}>
                    {ui(
                      "6 exact party roles (Accused, Opponent, Defendant, Complainant, Applicant, Plaintiff) are supported with grammatically fitted absence reasons.",
                      'હવે "કોના તરફે એડવોકેટ" માં ૬ ચોક્કસ હોદ્દા (આરોપી, સામાવાળા, પ્રતિવાદી, ફરિયાદી, અરજદાર, વાદી) ઉપલબ્ધ છે. તેમજ ગેરહાજરીનું કારણ સીધું વ્યાકરણબદ્ધ રીતે ફકરામાં ફિટ બેસે છે.'
                    )}
                  </Text>
                </View>
              </View>
            </View>
          )}

          {activeTab === "pdf" && (
            <View>
              <Text style={[styles.sectionHeading, { color: colors.onSurface }]}>{ui("Court-Compliant PDF Guidelines", "કોર્ટ-માન્ય PDF પ્રિન્ટિંગ નિયમો")}</Text>
              <Text style={[styles.sectionSub, { color: colors.muted }]}>
                {ui(
                  "PDFs are generated with filing margins and legal typography conforming to Gujarat court standards.",
                  "ગુજરાતની અદાલતોના ફાઇલિંગ નિયમ અનુસાર ચોક્કસ માર્જિન અને લેઆઉટ સાથે પીડીએફ જનરેટ થાય છે."
                )}
              </Text>

              <View style={[styles.pdfSpecContainer, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <View style={styles.specItem}>
                  <Ionicons name="resize" size={16} color={colors.brandPrimary} />
                  <Text style={[styles.specTitle, { color: colors.onSurface }]}>{ui("Left Margin: 40 mm (1.57 inch)", "ડાબો માર્જિન: ૪૦ mm (1.57 inch)")}</Text>
                  <Text style={[styles.specDesc, { color: colors.muted }]}>
                    {ui("Leaves accurate court punching and binding space.", "કોર્ટ ફાઇલિંગ પંચિંગ અને દોરી બાંધવા માટે પરફેક્ટ જગ્યા છૂટે છે.")}
                  </Text>
                </View>
                <View style={styles.specItem}>
                  <Ionicons name="text" size={16} color={colors.brandPrimary} />
                  <Text style={[styles.specTitle, { color: colors.onSurface }]}>{ui("Fonts: Lohit Gujarati / Times New Roman", "અધિકૃત ફોન્ટ્સ: Lohit Gujarati અને Times New Roman")}</Text>
                  <Text style={[styles.specDesc, { color: colors.muted }]}>
                    {ui("Crisp character shaping so printed text stays readable.", "સ્પષ્ટ અક્ષરો જેથી પ્રિન્ટમાં કોઈ અક્ષર તૂટતો નથી.")}
                  </Text>
                </View>
                <View style={styles.specItem}>
                  <Ionicons name="checkmark-done" size={16} color={colors.brandPrimary} />
                  <Text style={[styles.specTitle, { color: colors.onSurface }]}>{ui("Direct Device Save & Share", "સીધું ફોનમાં સેવ અને શેરિંગ")}</Text>
                  <Text style={[styles.specDesc, { color: colors.muted }]}>
                    {ui("Save documents directly to Downloads/NyaySetu Pro or share on WhatsApp.", "મોબાઇલમાંથી સીધી ફાઇલ સેવ કરો અથવા અસીલને વ્હોટ્સએપ પર મોકલો.")}
                  </Text>
                </View>
              </View>
            </View>
          )}

          {activeTab === "wallet" && (
            <View>
              <Text style={[styles.sectionHeading, { color: colors.onSurface }]}>{ui("Wallet & Billing", "વોલેટ અને રિચાર્જ")}</Text>
              <Text style={[styles.sectionSub, { color: colors.muted }]}>
                {ui(
                  "Transparent credit system: previewing is free, credits are deducted only on final download.",
                  "પારદર્શક પેમેન્ટ સિસ્ટમ. પ્રીવ્યૂ જોવા માટે કોઈ ચાર્જ નથી, માત્ર આખરી PDF ડાઉનલોડ વખતે જ ક્રેડિટ કપાશે."
                )}
              </Text>

              <View style={[styles.stepCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <Ionicons name="wallet-outline" size={24} color={colors.brandPrimary} />
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={[styles.stepTitle, { color: colors.onSurface }]}>{ui("Pay Per Document", "દસ્તાવેજ દીઠ ચુકવણી")}</Text>
                  <Text style={[styles.stepDesc, { color: colors.muted }]}>
                    {ui("Top up credit packs and use them anytime with no expiry.", "જરૂર મુજબ વોલેટ રિચાર્જ કરો અને કોઈપણ એક્સપાયરી વગર ક્રેડિટ વાપરો.")}
                  </Text>
                </View>
              </View>

              <View style={[styles.stepCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border, marginTop: 8 }]}>
                <Ionicons name="infinite" size={24} color="#10B981" />
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={[styles.stepTitle, { color: colors.onSurface }]}>{ui("Unlimited Access Plans", "અનલિમિટેડ પ્લાન્સ")}</Text>
                  <Text style={[styles.stepDesc, { color: colors.muted }]}>
                    {ui("Built for busy chambers needing frequent daily drafting.", "રોજિંદા વધુ કામ ધરાવતી ઓફિસો માટે સુવિધાજનક પ્લાન્સ.")}
                  </Text>
                </View>
              </View>
            </View>
          )}

          {activeTab === "faq" && (
            <View>
              <Text style={[styles.sectionHeading, { color: colors.onSurface }]}>{ui("Frequently Asked Questions", "વારંવાર પૂછાતા પ્રશ્નો")}</Text>

              <View style={[styles.faqCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <Text style={[styles.faqQ, { color: colors.onSurface }]}>{ui("1. Are generated PDFs court-compliant?", "૧. શું આ PDF કોર્ટમાં કાયદેસર રીતે રજૂ કરી શકાય?")}</Text>
                <Text style={[styles.faqA, { color: colors.muted }]}>
                  {ui(
                    "Yes. Templates follow Gujarat court filing standards (40mm left margin, legal page size, and authentic legal drafting).",
                    "હા, ૧૦૦% માન્ય છે. ન્યાયસેતુ પ્રોની તમામ અરજીઓ ગુજરાત હાઇકોર્ટ અને ડિસ્ટ્રિક્ટ કોર્ટ્સના લીગલ ફાઇલિંગ રૂલ્સ (૪૦mm ડાબો માર્જિન, લીગલ સાઈઝ પેપર, કોર્ટ માન્ય ગુજરાતી કાનૂની પરિભાષા) અનુસાર બનેલી છે."
                  )}
                </Text>
              </View>

              <View style={[styles.faqCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <Text style={[styles.faqQ, { color: colors.onSurface }]}>{ui("2. What if the app closes while editing?", "૨. જો અરજી ભરતી વખતે એપ બંધ થઈ જાય તો?")}</Text>
                <Text style={[styles.faqA, { color: colors.muted }]}>
                  {ui(
                    "Real-time autosave stores your unfinished progress as a draft so you can resume anytime from Vault or the case.",
                    "ચિંતા કરશો નહીં. એપમાં રિયલ-ટાઇમ ઓટો-સેવ ટેકનોલોજી છે. તમે જે પણ વિગતો ભરી હશે તે ડ્રાફ્ટ તરીકે સાચવેલી જ રહેશે."
                  )}
                </Text>
              </View>

              <View style={[styles.faqCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <Text style={[styles.faqQ, { color: colors.onSurface }]}>{ui("3. How do I draft applications in English or Gujarati?", "૩. અંગ્રેજી કે ગુજરાતીમાં અરજી બનાવવી હોય તો?")}</Text>
                <Text style={[styles.faqA, { color: colors.muted }]}>
                  {ui(
                    "When opening any template, choose Gujarati or English from the document language prompt. Legal templates always support both languages.",
                    "કોઈપણ અરજી ખોલતી વખતે દસ્તાવેજની ભાષા ગુજરાતી અથવા અંગ્રેજી પસંદ કરી શકો છો. અરજીઓ બંને ભાષામાં ઉપલબ્ધ રહે છે."
                  )}
                </Text>
              </View>

              {/* Reset Tour Button */}
              <View style={{ marginTop: Spacing.xl, alignItems: "center" }}>
                <Pressable
                  onPress={handleResetTour}
                  style={[styles.resetTourBtn, { borderColor: colors.border, backgroundColor: colors.surfaceSecondary }]}
                >
                  <Ionicons name="refresh-outline" size={16} color={colors.muted} />
                  <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "700", marginLeft: 6 }}>
                    {ui("Replay Welcome Tour", "ઓનબોર્ડિંગ પોપઅપ ફરીથી જુઓ")}
                  </Text>
                </Pressable>
              </View>
            </View>
          )}
        </ScrollView>
      </View>

      {/* Interactive Modal Tour */}
      <UserGuideModal
        visible={showInteractiveModal}
        onClose={() => setShowInteractiveModal(false)}
        onComplete={() => setShowInteractiveModal(false)}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
  },
  topBarLeft: {
    flexDirection: "row",
    alignItems: "center",
  },
  backBtn: {
    width: 36,
    height: 36,
    borderRadius: Radius.md,
    justifyContent: "center",
    alignItems: "center",
  },
  pageTitle: {
    fontSize: 16,
    fontWeight: "800",
  },
  pageSubtitle: {
    fontSize: 11,
    fontWeight: "500",
  },
  interactiveTourBtn: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: Radius.sm,
  },
  interactiveTourText: {
    fontSize: 12,
    fontWeight: "800",
    color: "#061024",
    marginLeft: 4,
  },
  contentLayout: {
    flex: 1,
    flexDirection: "column",
  },
  contentLayoutDesktop: {
    flexDirection: "row",
  },
  tabBarContainer: {
    paddingVertical: Spacing.xs,
  },
  desktopSidebar: {
    width: 250,
    borderRightWidth: 1,
    paddingVertical: Spacing.md,
  },
  desktopTabList: {
    paddingHorizontal: Spacing.md,
  },
  mobileTabList: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
  },
  tabItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: Radius.md,
    borderWidth: 1,
    marginRight: Spacing.xs,
    marginBottom: Spacing.xs,
  },
  tabItemActive: {},
  tabItemInactive: {},
  tabTextGu: {
    fontSize: 12,
  },
  tabTextEn: {
    fontSize: 10,
  },
  tabBodyScroll: {
    flex: 1,
  },
  tabBodyContent: {
    padding: Spacing.lg,
    paddingBottom: Spacing.xxxl,
  },
  heroBanner: {
    padding: Spacing.lg,
    borderRadius: Radius.lg,
    marginBottom: Spacing.lg,
  },
  heroBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(197,160,89,0.15)",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: Radius.sm,
    alignSelf: "flex-start",
    marginBottom: Spacing.sm,
  },
  heroTitle: {
    color: "#FFF",
    fontSize: 19,
    fontWeight: "800",
    marginBottom: Spacing.xs,
  },
  heroDesc: {
    color: "#E2E8F0",
    fontSize: 12,
    lineHeight: 18,
  },
  sectionHeading: {
    fontSize: 17,
    fontWeight: "800",
    marginBottom: 4,
  },
  sectionSub: {
    fontSize: 12,
    marginBottom: Spacing.md,
    lineHeight: 17,
  },
  stepCard: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
    marginBottom: Spacing.sm,
  },
  stepNumberBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: "center",
    alignItems: "center",
  },
  stepNumberText: {
    fontSize: 14,
    fontWeight: "800",
    color: "#061024",
  },
  stepTitle: {
    fontSize: 13,
    fontWeight: "700",
  },
  stepDesc: {
    fontSize: 11,
    marginTop: 2,
    lineHeight: 16,
  },
  visualCard: {
    borderRadius: Radius.md,
    borderWidth: 1,
    overflow: "hidden",
    marginBottom: Spacing.md,
  },
  visualHeader: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  visualContent: {
    padding: 12,
  },
  mockFieldLabel: {
    fontSize: 10,
    fontWeight: "600",
  },
  mockFieldValue: {
    fontSize: 12,
    fontWeight: "700",
    marginTop: 2,
  },
  tipBox: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  tableCard: {
    borderRadius: Radius.md,
    borderWidth: 1,
    overflow: "hidden",
    marginBottom: Spacing.md,
  },
  tableRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  tableHeaderRow: {
    backgroundColor: "rgba(0,0,0,0.03)",
  },
  tableHeaderCell: {
    fontSize: 12,
    fontWeight: "800",
  },
  tableCell: {
    fontSize: 12,
    fontWeight: "600",
  },
  tableBadge: {
    fontSize: 11,
    fontWeight: "700",
  },
  alertCard: {
    flexDirection: "row",
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  pdfSpecContainer: {
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  specItem: {
    marginBottom: Spacing.md,
  },
  specTitle: {
    fontSize: 13,
    fontWeight: "700",
    marginTop: 4,
  },
  specDesc: {
    fontSize: 11,
    marginTop: 2,
    lineHeight: 16,
  },
  faqCard: {
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
    marginBottom: Spacing.sm,
  },
  faqQ: {
    fontSize: 13,
    fontWeight: "700",
  },
  faqA: {
    fontSize: 12,
    marginTop: 4,
    lineHeight: 18,
  },
  resetTourBtn: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: Radius.sm,
    borderWidth: 1,
  },
});

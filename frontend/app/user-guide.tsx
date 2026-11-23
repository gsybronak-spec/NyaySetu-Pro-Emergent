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
import { Radius, Spacing } from "@/src/theme/tokens";
import { storage } from "@/src/utils/storage";
import { UserGuideModal } from "@/src/components/UserGuideModal";

type GuideTab = "quickstart" | "cases" | "templates" | "pdf" | "wallet" | "faq";

export default function UserGuideScreen() {
  const { colors, isDark } = useTheme();
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
            onPress={() => router.back()}
            style={[styles.backBtn, { backgroundColor: colors.surfaceSecondary }]}
            hitSlop={10}
          >
            <Ionicons name="arrow-back" size={20} color={colors.onSurface} />
          </Pressable>
          <View style={{ marginLeft: Spacing.sm }}>
            <Text style={[styles.pageTitle, { color: colors.onSurface }]}>વપરાશકર્તા માર્ગદર્શિકા</Text>
            <Text style={[styles.pageSubtitle, { color: colors.muted }]}>NyaaySetu Pro User Guide & Documentation</Text>
          </View>
        </View>

        <Pressable
          onPress={() => setShowInteractiveModal(true)}
          style={[styles.interactiveTourBtn, { backgroundColor: colors.brandPrimary }]}
        >
          <Ionicons name="play-circle-outline" size={16} color="#061024" />
          <Text style={styles.interactiveTourText}>ઇન્ટરેક્ટિવ ટુર (Slide Tour)</Text>
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
                      {tab.labelGu}
                    </Text>
                    <Text
                      style={[
                        styles.tabTextEn,
                        { color: active ? "#CBD5E1" : colors.muted },
                      ]}
                    >
                      {tab.labelEn}
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
                    ૧ મિનિટમાં કોર્ટ-માન્ય કાનૂની અરજી
                  </Text>
                </View>
                <Text style={styles.heroTitle}>ન્યાયસેતુ પ્રો માં આપનું સ્વાગત છે</Text>
                <Text style={styles.heroDesc}>
                  ગુજરાતની અદાલતોના વકીલો માટે ખાસ તૈયાર થયેલું ઝડપી, પેપરલેસ લીગલ ડ્રાફ્ટિંગ સોફ્ટવેર. આ માર્ગદર્શિકા તમને દરેક ફીચર સરળતાથી વાપરવામાં મદદ કરશે.
                </Text>
              </LinearGradient>

              {/* 3 Step Quick Overview */}
              <Text style={[styles.sectionHeading, { color: colors.onSurface }]}>સરળ ૩ પગલાંમાં અરજી બનાવો:</Text>
              
              <View style={[styles.stepCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <View style={[styles.stepNumberBadge, { backgroundColor: colors.brandPrimary }]}>
                  <Text style={styles.stepNumberText}>૧</Text>
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={[styles.stepTitle, { color: colors.onSurface }]}>કેસ ઉમેરો (Add Case)</Text>
                  <Text style={[styles.stepDesc, { color: colors.muted }]}>
                    જિલ્લો, કોર્ટનું નામ, કેસ નંબર અને વાદી-પ્રતિવાદીનું નામ સેવ કરો.
                  </Text>
                </View>
              </View>

              <View style={[styles.stepCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <View style={[styles.stepNumberBadge, { backgroundColor: colors.brandPrimary }]}>
                  <Text style={styles.stepNumberText}>૨</Text>
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={[styles.stepTitle, { color: colors.onSurface }]}>કાનૂની નમૂનો પસંદ કરો (Select Template)</Text>
                  <Text style={[styles.stepDesc, { color: colors.muted }]}>
                    હાજરી મુક્તિ, વોરંટ રદ, મુદ્દત કે વકાલતનામું પસંદ કરો. કેસની તમામ વિગતો આપોઆપ ભરાઈ જશે.
                  </Text>
                </View>
              </View>

              <View style={[styles.stepCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <View style={[styles.stepNumberBadge, { backgroundColor: colors.brandPrimary }]}>
                  <Text style={styles.stepNumberText}>૩</Text>
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={[styles.stepTitle, { color: colors.onSurface }]}>પ્રિન્ટ / WhatsApp કરો (Generate PDF)</Text>
                  <Text style={[styles.stepDesc, { color: colors.muted }]}>
                    ૪૦mm ડાબા માર્જિન સાથે કોર્ટ-માન્ય PDF તરત ડાઉનલોડ કરો અથવા સીધી પ્રિન્ટ કાઢો.
                  </Text>
                </View>
              </View>
            </View>
          )}

          {activeTab === "cases" && (
            <View>
              <Text style={[styles.sectionHeading, { color: colors.onSurface }]}>કેસ મેનેજમેન્ટ સિસ્ટમ (Case Management)</Text>
              <Text style={[styles.sectionSub, { color: colors.muted }]}>
                કેસ સેવ કરવાથી દરેક અરજીમાં કોર્ટ અને પક્ષકારોની વિગત વારંવાર લખવાની જરૂર રહેતી નથી.
              </Text>

              {/* Visual Mockup Card */}
              <View style={[styles.visualCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <View style={[styles.visualHeader, { backgroundColor: colors.brand }]}>
                  <Ionicons name="folder-open" size={16} color="#C5A059" />
                  <Text style={{ color: "#FFF", fontWeight: "700", fontSize: 13, marginLeft: 6 }}>
                    નવો કેસ ઉમેરવાની સ્ક્રીન (New Case Screen)
                  </Text>
                </View>
                <View style={styles.visualContent}>
                  <Text style={[styles.mockFieldLabel, { color: colors.muted }]}>૧. જિલ્લો અને તાલુકો:</Text>
                  <Text style={[styles.mockFieldValue, { color: colors.onSurface }]}>અમદાવાદ ➔ અમદાવાદ શહેર</Text>

                  <Text style={[styles.mockFieldLabel, { color: colors.muted, marginTop: 6 }]}>૨. કોર્ટનું નામ:</Text>
                  <Text style={[styles.mockFieldValue, { color: colors.onSurface }]}>ચીફ જ્યુડિશિયલ મેજીસ્ટ્રેટશ્રીની કોર્ટ</Text>

                  <Text style={[styles.mockFieldLabel, { color: colors.muted, marginTop: 6 }]}>૩. પક્ષકારો:</Text>
                  <Text style={[styles.mockFieldValue, { color: colors.onSurface }]}>ફરિયાદી: રાજેશકુમાર પટેલ | આરોપી: મહેશભાઈ ઠાકોર</Text>
                </View>
              </View>

              <View style={[styles.tipBox, { backgroundColor: "rgba(197,160,89,0.12)", borderColor: colors.brandPrimary }]}>
                <Ionicons name="bulb-outline" size={18} color="#8C6A29" />
                <Text style={{ color: colors.onSurface, fontSize: 12, marginLeft: 8, flex: 1, lineHeight: 18 }}>
                  <Text style={{ fontWeight: "800" }}>પ્રો ટિપ: </Text>
                  જો કોર્ટનું નામ ડ્રોપડાઉનમાં ન મળે તો <Text style={{ fontWeight: "700" }}>"Other / અન્ય"</Text> પસંદ કરી તમારી સ્થાનિક કોર્ટનું નામ જાતે ટાઇપ કરી શકો છો.
                </Text>
              </View>
            </View>
          )}

          {activeTab === "templates" && (
            <View>
              <Text style={[styles.sectionHeading, { color: colors.onSurface }]}>૨૬ અધિકૃત કાનૂની નમૂનાઓ (Legal Templates)</Text>
              <Text style={[styles.sectionSub, { color: colors.muted }]}>
                ગુજરાતની સિવિલ અને ક્રિમિનલ કોર્ટોના રૂલ્સ મુજબ વકીલો દ્વારા ચકાસાયેલ પ્રમાણિત લખાણ.
              </Text>

              <View style={[styles.tableCard, { borderColor: colors.border, backgroundColor: colors.surfaceSecondary }]}>
                <View style={[styles.tableRow, styles.tableHeaderRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableHeaderCell, { color: colors.onSurface, flex: 2 }]}>નમૂનાનું નામ</Text>
                  <Text style={[styles.tableHeaderCell, { color: colors.onSurface, flex: 1 }]}>કેટેગરી</Text>
                </View>

                <View style={[styles.tableRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableCell, { color: colors.onSurface, flex: 2 }]}>વોરંટ રદ કરવાની અરજી</Text>
                  <Text style={[styles.tableBadge, { color: "#C05621", flex: 1 }]}>Criminal</Text>
                </View>
                <View style={[styles.tableRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableCell, { color: colors.onSurface, flex: 2 }]}>હાજરી મુક્તિ અરજી (Exemption Sec 317)</Text>
                  <Text style={[styles.tableBadge, { color: "#C05621", flex: 1 }]}>Criminal</Text>
                </View>
                <View style={[styles.tableRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableCell, { color: colors.onSurface, flex: 2 }]}>એફ.એસ.નો હક બંધ કરવાની અરજી</Text>
                  <Text style={[styles.tableBadge, { color: "#C05621", flex: 1 }]}>Criminal</Text>
                </View>
                <View style={[styles.tableRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableCell, { color: colors.onSurface, flex: 2 }]}>વકાલતનામું (દિવાની / ફોજદારી)</Text>
                  <Text style={[styles.tableBadge, { color: "#2B6CB0", flex: 1 }]}>Civil / Crim.</Text>
                </View>
                <View style={[styles.tableRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableCell, { color: colors.onSurface, flex: 2 }]}>મુદ્દત અરજી (Adjournment)</Text>
                  <Text style={[styles.tableBadge, { color: "#2F855A", flex: 1 }]}>General</Text>
                </View>
                <View style={[styles.tableRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableCell, { color: colors.onSurface, flex: 2 }]}>દસ્તાવેજ પરત લેવાની અરજી</Text>
                  <Text style={[styles.tableBadge, { color: "#2F855A", flex: 1 }]}>General</Text>
                </View>
                <View style={[styles.tableRow, { borderBottomColor: colors.border }]}>
                  <Text style={[styles.tableCell, { color: colors.onSurface, flex: 2 }]}>સર્ટિફાઇડ નકલ અરજી</Text>
                  <Text style={[styles.tableBadge, { color: "#2F855A", flex: 1 }]}>General</Text>
                </View>
              </View>

              {/* Special instructions for Warrant cancellation */}
              <View style={[styles.alertCard, { backgroundColor: "rgba(43,108,176,0.08)", borderColor: "#2B6CB0" }]}>
                <Ionicons name="information-circle" size={18} color="#2B6CB0" />
                <View style={{ marginLeft: 8, flex: 1 }}>
                  <Text style={{ color: "#2B6CB0", fontWeight: "800", fontSize: 13 }}>
                    વોરંટ રદ અરજી માટે નવું અપડેટ:
                  </Text>
                  <Text style={{ color: colors.onSurface, fontSize: 12, marginTop: 2, lineHeight: 18 }}>
                    હવે "કોના તરફે એડવોકેટ" માં ૬ ચોક્કસ હોદ્દા (આરોપી, સામાવાળા, પ્રતિવાદી, ફરિયાદી, અરજદાર, વાદી) ઉપલબ્ધ છે. તેમજ ગેરહાજરીનું કારણ સીધું વ્યાકરણબદ્ધ રીતે ફકરામાં ફિટ બેસે છે.
                  </Text>
                </View>
              </View>
            </View>
          )}

          {activeTab === "pdf" && (
            <View>
              <Text style={[styles.sectionHeading, { color: colors.onSurface }]}>કોર્ટ-માન્ય PDF પ્રિન્ટિંગ નિયમો (Court Filing Rules)</Text>
              <Text style={[styles.sectionSub, { color: colors.muted }]}>
                ગુજરાતની અદાલતોના ફાઇલિંગ નિયમ અનુસાર ચોક્કસ માર્જિન અને લેઆઉટ સાથે પીડીએફ જનરેટ થાય છે.
              </Text>

              <View style={[styles.pdfSpecContainer, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <View style={styles.specItem}>
                  <Ionicons name="resize" size={16} color={colors.brandPrimary} />
                  <Text style={[styles.specTitle, { color: colors.onSurface }]}>ડાબો માર્જિન: ૪૦ mm (1.57 inch)</Text>
                  <Text style={[styles.specDesc, { color: colors.muted }]}>કોર્ટ ફાઇલિંગ પંચિંગ અને દોરી બાંધવા માટે પરફેક્ટ જગ્યા છૂટે છે.</Text>
                </View>
                <View style={styles.specItem}>
                  <Ionicons name="text" size={16} color={colors.brandPrimary} />
                  <Text style={[styles.specTitle, { color: colors.onSurface }]}>અધિકૃત ફોન્ટ્સ: Lohit Gujarati / Times New Roman</Text>
                  <Text style={[styles.specDesc, { color: colors.muted }]}>સ્પષ્ટ અક્ષરો જેથી પ્રિન્ટમાં કોઈ અક્ષર તૂટતો નથી.</Text>
                </View>
                <View style={styles.specItem}>
                  <Ionicons name="checkmark-done" size={16} color={colors.brandPrimary} />
                  <Text style={[styles.specTitle, { color: colors.onSurface }]}>૧-ક્લિક શેરિંગ અને વાઇફાઇ પ્રિન્ટ</Text>
                  <Text style={[styles.specDesc, { color: colors.muted }]}>મોબાઇલમાંથી સીધી પ્રિન્ટ કાઢો અથવા અસીલને વ્હોટ્સએપ પર પીડીએફ મોકલો.</Text>
                </View>
              </View>
            </View>
          )}

          {activeTab === "wallet" && (
            <View>
              <Text style={[styles.sectionHeading, { color: colors.onSurface }]}>વોલેટ અને રિચાર્જ (Wallet & Billing)</Text>
              <Text style={[styles.sectionSub, { color: colors.muted }]}>
                પારદર્શક પેમેન્ટ સિસ્ટમ. પ્રીવ્યૂ જોવા માટે કોઈ ચાર્જ નથી, માત્ર આખરી PDF ડાઉનલોડ વખતે જ ક્રેડિટ કપાશે.
              </Text>

              <View style={[styles.stepCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <Ionicons name="wallet-outline" size={24} color={colors.brandPrimary} />
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={[styles.stepTitle, { color: colors.onSurface }]}>Pay-per-document (દસ્તાવેજ દીઠ)</Text>
                  <Text style={[styles.stepDesc, { color: colors.muted }]}>
                    રૂ. ૧૦૦, ૨૦૦ કે ૫૦૦ નું વોલેટ રિચાર્જ કરો અને જરૂર મુજબ જ ક્રેડિટ વાપરો.
                  </Text>
                </View>
              </View>

              <View style={[styles.stepCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border, marginTop: 8 }]}>
                <Ionicons name="infinite" size={24} color="#10B981" />
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={[styles.stepTitle, { color: colors.onSurface }]}>અનલિમિટેડ પ્લાન્સ (Unlimited Access)</Text>
                  <Text style={[styles.stepDesc, { color: colors.muted }]}>
                    રોજિંદા વધુ કામ ધરાવતી ઓફિસો માટે માસિક કે વાર્ષિક અનલિમિટેડ કાનૂની ડ્રાફ્ટિંગ પ્લાન.
                  </Text>
                </View>
              </View>
            </View>
          )}

          {activeTab === "faq" && (
            <View>
              <Text style={[styles.sectionHeading, { color: colors.onSurface }]}>વારંવાર પૂછાતા પ્રશ્નો (FAQ)</Text>

              <View style={[styles.faqCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <Text style={[styles.faqQ, { color: colors.onSurface }]}>૧. શું આ PDF કોર્ટમાં કાયદેસર રીતે રજૂ કરી શકાય?</Text>
                <Text style={[styles.faqA, { color: colors.muted }]}>
                  હા, ૧૦૦% માન્ય છે. ન્યાયસેતુ પ્રોની તમામ અરજીઓ ગુજરાત હાઇકોર્ટ અને ડિસ્ટ્રિક્ટ કોર્ટ્સના લીગલ ફાઇલિંગ રૂલ્સ (૪૦mm ડાબો માર્જિન, લીગલ સાઈઝ પેપર, કોર્ટ માન્ય ગુજરાતી કાનૂની પરિભાષા) અનુસાર બનેલી છે.
                </Text>
              </View>

              <View style={[styles.faqCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <Text style={[styles.faqQ, { color: colors.onSurface }]}>૨. જો અરજી ભરતી વખતે એપ બંધ થઈ જાય તો?</Text>
                <Text style={[styles.faqA, { color: colors.muted }]}>
                  ચિંતા કરશો નહીં. એપમાં રિયલ-ટાઇમ ઓટો-સેવ ટેકનોલોજી છે. તમે જે પણ શબ્દ લખ્યો હશે તે સર્વર પર ડ્રાફ્ટ તરીકે સાચવેલો જ રહેશે.
                </Text>
              </View>

              <View style={[styles.faqCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
                <Text style={[styles.faqQ, { color: colors.onSurface }]}>૩. અંગ્રેજીમાં અરજી બનાવવી હોય તો?</Text>
                <Text style={[styles.faqA, { color: colors.muted }]}>
                  દરેક અરજી સ્ક્રીનની ઉપર "ગુજરાતી | English" ભાષા ટૉગલ છે. ફક્ત ૧ ક્લિકથી આખી અરજી અંગ્રેજીમાં ટ્રાન્સલેટ થઈ જશે.
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
                    ઓનબોર્ડિંગ પોપઅપ ફરીથી જુઓ (Replay Welcome Tour)
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

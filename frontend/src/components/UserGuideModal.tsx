import React, { useState } from "react";
import {
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAppLanguage } from "@/src/context/AppLanguageContext";
import { Radius, Spacing } from "@/src/theme/tokens";
import { storage } from "@/src/utils/storage";

interface UserGuideModalProps {
  visible: boolean;
  onClose: () => void;
  onComplete?: () => void;
}

interface GuideSlide {
  id: number;
  badge: string;
  badgeEn: string;
  titleGu: string;
  titleEn: string;
  descGu: string;
  descEn: string;
  icon: keyof typeof Ionicons.glyphMap;
  renderMockup: (colors: any, isDark: boolean) => React.ReactNode;
}

export function UserGuideModal({ visible, onClose, onComplete }: UserGuideModalProps) {
  const { colors, isDark } = useTheme();
  const { isGujarati, ui } = useAppLanguage();
  const { width } = useWindowDimensions();
  const isDesktop = width >= 768;
  const [currentSlide, setCurrentSlide] = useState(0);

  const slides: GuideSlide[] = [
    {
      id: 1,
      badge: "પગલું ૧: પ્રોફાઇલ સેટઅપ",
      badgeEn: "Step 1: Profile Setup",
      titleGu: "વકીલ પ્રોફાઇલ સેટઅપ કરો",
      titleEn: "Step 1: Advocate Profile Setup",
      descGu: "આપનું નામ, સનદ નંબર અને ચેમ્બરનું સરનામું સેટ કરો. આ વિગતો આપોઆપ દરેક કાનૂની અરજીના અંતે પ્રિન્ટ થઈ જશે.",
      descEn: "Setup your Advocate name, Sanad / Bar Council number, and office address to automatically stamp documents.",
      icon: "person-circle-outline",
      renderMockup: (c) => (
        <View style={[styles.mockupContainer, { backgroundColor: c.surfaceSecondary, borderColor: c.border }]}>
          <View style={[styles.mockHeader, { backgroundColor: c.brand }]}>
            <View style={styles.mockAvatar}>
              <Text style={{ color: "#FFF", fontWeight: "800", fontSize: 16 }}>RP</Text>
            </View>
            <View style={{ marginLeft: 10 }}>
              <Text style={{ color: "#FFF", fontWeight: "700", fontSize: 14 }}>એડવોકેટ રમેશભાઈ કે. પટેલ</Text>
              <Text style={{ color: "#C5A059", fontSize: 11, fontWeight: "600" }}>Bar No: G/1234/2018</Text>
            </View>
          </View>
          <View style={styles.mockBody}>
            <View style={styles.mockInfoRow}>
              <Ionicons name="call-outline" size={13} color={c.muted} />
              <Text style={[styles.mockInfoText, { color: c.onSurfaceSecondary }]}>+91 98765 43210</Text>
            </View>
            <View style={styles.mockInfoRow}>
              <Ionicons name="location-outline" size={13} color={c.muted} />
              <Text style={[styles.mockInfoText, { color: c.onSurfaceSecondary }]}>ચેમ્બર નં. ૪, સિટી સિવિલ કોર્ટ, અમદાવાદ</Text>
            </View>
            <View style={[styles.verifiedBadge, { backgroundColor: "rgba(30,70,32,0.12)" }]}>
              <Ionicons name="checkmark-circle" size={14} color="#1E4620" />
              <Text style={{ color: "#1E4620", fontSize: 11, fontWeight: "700", marginLeft: 4 }}>
                દરેક અરજીના છેલ્લે સહી-હોદ્દો ઓટો-પ્રિન્ટ થશે
              </Text>
            </View>
          </View>
        </View>
      ),
    },
    {
      id: 2,
      badge: "પગલું ૨: કેસ મેનેજમેન્ટ",
      badgeEn: "Step 2: Case Management",
      titleGu: "કોર્ટ કેસ ઉમેરો અને સાચવો",
      titleEn: "Step 2: Add & Manage Cases",
      descGu: "જિલ્લો, કોર્ટનું નામ, કેસ નંબર અને બંને પક્ષકારોની વિગત એકવાર ભરો. કેસ હિસ્ટ્રી અને આગામી મુદ્દત પણ ટ્રેક કરી શકાશે.",
      descEn: "Save case details once. District, Court, Case Number and Parties will auto-populate across all templates.",
      icon: "briefcase-outline",
      renderMockup: (c) => (
        <View style={[styles.mockupContainer, { backgroundColor: c.surfaceSecondary, borderColor: c.border }]}>
          <View style={[styles.mockCardTop, { borderBottomColor: c.border }]}>
            <Text style={{ color: c.brandPrimary, fontWeight: "800", fontSize: 11 }}>ક્રિમિનલ કેસ નં. ૫૫૫/૨૦૨૬</Text>
            <Text style={{ color: c.muted, fontSize: 10 }}>મુદ્દત: ૧૫/૧૨/૨૦૨૬</Text>
          </View>
          <View style={styles.mockBody}>
            <Text style={{ color: c.onSurface, fontWeight: "700", fontSize: 12 }}>ચીફ જ્યુડિશિયલ મેજીસ્ટ્રેટશ્રીની કોર્ટ, અમદાવાદ</Text>
            <View style={[styles.partyLineBox, { backgroundColor: c.surface, borderColor: c.border }]}>
              <Text style={{ color: c.onSurface, fontSize: 11 }}>
                <Text style={{ fontWeight: "700", color: c.brandPrimary }}>ફરિયાદી: </Text>
                રાજેશકુમાર શાંતિલાલ પટેલ
              </Text>
              <Text style={{ color: c.muted, fontSize: 10, marginVertical: 2 }}>વિરુદ્ધ</Text>
              <Text style={{ color: c.onSurface, fontSize: 11 }}>
                <Text style={{ fontWeight: "700", color: "#C05621" }}>આરોપી: </Text>
                મહેશભાઈ કાનજીભાઈ ઠાકોર
              </Text>
            </View>
          </View>
        </View>
      ),
    },
    {
      id: 3,
      badge: "પગલું ૩: કાનૂની નમૂનાઓ",
      badgeEn: "Step 3: Legal Templates",
      titleGu: "૨૬ દ્વિભાષી કાનૂની અરજીઓ",
      titleEn: "Step 3: 26 Bilingual Legal Templates",
      descGu: "વકાલતનામું, હાજરી મુક્તિ, વોરંટ રદ, એફ.એસ. હક બંધ, મુદ્દત અરજી, દસ્તાવેજ પરત જેવા તમામ પ્રમાણિત નમૂનાઓ ૧ મિનિટમાં તૈયાર કરો.",
      descEn: "Pre-formatted, legally vetted templates in both Gujarati and English ready to file in Gujarat Courts.",
      icon: "document-text-outline",
      renderMockup: (c) => (
        <View style={[styles.mockupContainer, { backgroundColor: c.surfaceSecondary, borderColor: c.border }]}>
          <View style={styles.templateGridPreview}>
            <View style={[styles.mockTplCard, { backgroundColor: c.surface, borderColor: c.border }]}>
              <Ionicons name="document-attach" size={16} color={c.brandPrimary} />
              <Text style={[styles.mockTplName, { color: c.onSurface }]}>વોરંટ રદ કરવાની અરજી</Text>
              <Text style={{ color: c.muted, fontSize: 9 }}>Warrant Cancellation</Text>
            </View>
            <View style={[styles.mockTplCard, { backgroundColor: c.surface, borderColor: c.border }]}>
              <Ionicons name="person-remove" size={16} color="#2B6CB0" />
              <Text style={[styles.mockTplName, { color: c.onSurface }]}>હાજરી મુક્તિ અરજી</Text>
              <Text style={{ color: c.muted, fontSize: 9 }}>Exemption (Sec 317)</Text>
            </View>
            <View style={[styles.mockTplCard, { backgroundColor: c.surface, borderColor: c.border }]}>
              <Ionicons name="time" size={16} color="#D69E2E" />
              <Text style={[styles.mockTplName, { color: c.onSurface }]}>મુદ્દત અરજી</Text>
              <Text style={{ color: c.muted, fontSize: 9 }}>Adjournment Application</Text>
            </View>
            <View style={[styles.mockTplCard, { backgroundColor: c.surface, borderColor: c.border }]}>
              <Ionicons name="shield-checkmark" size={16} color="#38A169" />
              <Text style={[styles.mockTplName, { color: c.onSurface }]}>વકાલતનામું (દિવાની/ફોજદારી)</Text>
              <Text style={{ color: c.muted, fontSize: 9 }}>Vakalatnama Civil/Crim.</Text>
            </View>
          </View>
        </View>
      ),
    },
    {
      id: 4,
      badge: "પગલું ૪: રિયલ-ટાઇમ ઓટોસેવ",
      badgeEn: "Step 4: Real-time Auto-save",
      titleGu: "ડ્રાફ્ટ ઓટો-સેવ & ડેટા સુરક્ષા",
      titleEn: "Step 4: Real-time Auto-save",
      descGu: "તમે ટાઈપ કરો એટલે વિગતો આપોઆપ સર્વર પર સેવ થઈ જાય છે. એપ બંધ થઈ જાય તો પણ અધૂરી અરજી હંમેશા સાચવેલી રહેશે.",
      descEn: "Every keystroke autosaves instantly. Switch between apps or devices without ever losing your legal drafts.",
      icon: "cloud-done-outline",
      renderMockup: (c) => (
        <View style={[styles.mockupContainer, { backgroundColor: c.surfaceSecondary, borderColor: c.border }]}>
          <View style={[styles.autoSaveIndicator, { backgroundColor: "rgba(16,185,129,0.15)" }]}>
            <Ionicons name="checkmark-circle" size={14} color="#10B981" />
            <Text style={{ color: "#10B981", fontSize: 11, fontWeight: "700", marginLeft: 4 }}>
              {ui("Draft autosaved", "ડ્રાફ્ટ આપોઆપ સુરક્ષિત સેવ થયો")}
            </Text>
          </View>
          <View style={styles.mockBody}>
            <Text style={{ color: c.muted, fontSize: 10, fontWeight: "600" }}>કોના તરફે એડવોકેટ:</Text>
            <View style={[styles.mockInputPill, { backgroundColor: c.surface, borderColor: c.brandPrimary }]}>
              <Ionicons name="checkmark" size={13} color={c.brandPrimary} />
              <Text style={{ color: c.onSurface, fontSize: 11, fontWeight: "700", marginLeft: 4 }}>આરોપી તરફે</Text>
            </View>
            <Text style={{ color: c.muted, fontSize: 10, fontWeight: "600", marginTop: 6 }}>ગેરહાજર રહેવાનું કારણ:</Text>
            <View style={[styles.mockInputPill, { backgroundColor: c.surface, borderColor: c.border }]}>
              <Text style={{ color: c.onSurface, fontSize: 11 }}>માંદગીના કારણોસર</Text>
            </View>
          </View>
        </View>
      ),
    },
    {
      id: 5,
      badge: "પગલું ૫: કોર્ટ-માન્ય PDF",
      badgeEn: "Step 5: Court-Compliant PDF",
      titleGu: "કોર્ટ નિયમ અનુસાર ૧-ક્લિક PDF",
      titleEn: "Step 5: Court-Compliant PDF Generation",
      descGu: "ગુજરાત કોર્ટના નિયમ મુજબ ૪૦mm ડાબો માર્જિન, લીગલ સાઈઝ પેપર, કાનૂની ફોન્ટ્સ અને સહી લાઇન સાથે સીધી પ્રિન્ટ કાઢો કે WhatsApp કરો.",
      descEn: "Flawless legal formatting with 40mm filing margins, Gujarati statutory legal wording and instant 1-click print/share.",
      icon: "print-outline",
      renderMockup: (c) => (
        <View style={[styles.mockupContainer, { backgroundColor: "#FFF", borderColor: c.border }]}>
          <View style={styles.pdfSimSheet}>
            <View style={styles.pdfMarginRuler}>
              <Text style={{ color: "#A0AEC0", fontSize: 8, transform: [{ rotate: "-90deg" }] }}>૪૦mm માર્જિન</Text>
            </View>
            <View style={styles.pdfTextContent}>
              <Text style={styles.pdfHeader}>મહેરબાન કોર્ટ સાહેબશ્રીમાં,</Text>
              <Text style={styles.pdfSub}>મુકામ :- અમદાવાદ</Text>
              <Text style={styles.pdfSubject}>બાબત :- વોરંટ રદ કરાવવા બાબત...</Text>
              <Text style={styles.pdfBody} numberOfLines={3}>
                સદર કામમાં અમો આરોપી ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે... આરોપી માંદગીના કારણોસર ગેરહાજર રહેલ છે...
              </Text>
              <View style={styles.pdfSignLine}>
                <Text style={{ fontSize: 9, fontWeight: "700", color: "#2D3748" }}>---------- આરોપી ના એડવોકેટ</Text>
              </View>
            </View>
          </View>
        </View>
      ),
    },
  ];

  const handleNext = async () => {
    if (currentSlide < slides.length - 1) {
      setCurrentSlide((prev) => prev + 1);
    } else {
      await handleDismiss();
    }
  };

  const handlePrev = () => {
    if (currentSlide > 0) {
      setCurrentSlide((prev) => prev - 1);
    }
  };

  const handleDismiss = async () => {
    try {
      await storage.setItem("@nyaysetu_userguide_seen_v1", true);
    } catch {
      // Safe fallback
    }
    if (onComplete) onComplete();
    onClose();
  };

  const handleOpenFullGuide = async () => {
    await handleDismiss();
    router.push("/user-guide" as any);
  };

  const slide = slides[currentSlide];

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={handleDismiss}
    >
      <View style={styles.overlay}>
        <View
          style={[
            styles.modalBox,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
              width: isDesktop ? 620 : "92%",
              maxHeight: isDesktop ? 720 : "90%",
            },
          ]}
        >
          {/* Header */}
          <View style={[styles.header, { borderBottomColor: colors.border }]}>
            <View style={styles.headerLeft}>
              <LinearGradient
                colors={["#0B1B3D", "#C5A059"]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.logoBadge}
              >
                <Ionicons name="school-outline" size={18} color="#FFF" />
              </LinearGradient>
              <View style={{ marginLeft: Spacing.sm }}>
                <Text style={[styles.mainTitle, { color: colors.onSurface }]}>
                  {ui("NyaySetu Pro Guide", "ન્યાયસેતુ પ્રો માર્ગદર્શિકા")}
                </Text>
                <Text style={[styles.subTitle, { color: colors.muted }]}>
                  {ui("How to use NyaySetu Pro", "એપ કેવી રીતે વાપરવી")}
                </Text>
              </View>
            </View>
            <Pressable
              testID="close-guide-modal"
              onPress={handleDismiss}
              style={[styles.closeBtn, { backgroundColor: colors.surfaceSecondary }]}
              hitSlop={10}
            >
              <Ionicons name="close" size={20} color={colors.muted} />
            </Pressable>
          </View>

          {/* Body Slider */}
          <ScrollView contentContainerStyle={styles.bodyContent} showsVerticalScrollIndicator={false}>
            {/* Step badge */}
            <View style={styles.badgeRow}>
              <View style={[styles.stepBadge, { backgroundColor: colors.brandTertiary }]}>
                <Ionicons name={slide.icon} size={14} color={colors.onBrandTertiary} />
                <Text style={[styles.stepBadgeText, { color: colors.onBrandTertiary }]}>
                  {isGujarati ? slide.badge : slide.badgeEn}
                </Text>
              </View>
              <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "600" }}>
                {currentSlide + 1} / {slides.length}
              </Text>
            </View>

            {/* Slide Title */}
            <Text style={[styles.slideHeadingGu, { color: colors.onSurface }]}>
              {isGujarati ? slide.titleGu : slide.titleEn}
            </Text>

            {/* Visual Mockup Card / Simulated Screenshot */}
            <View style={styles.mockupWrapper}>
              {slide.renderMockup(colors, isDark)}
            </View>

            {/* Explanation Prose */}
            <View style={[styles.descBox, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
              <Text style={[styles.descGu, { color: colors.onSurface }]}>
                {isGujarati ? slide.descGu : slide.descEn}
              </Text>
            </View>
          </ScrollView>

          {/* Footer Controls */}
          <View style={[styles.footer, { borderTopColor: colors.border }]}>
            {/* Dot indicators */}
            <View style={styles.dotsRow}>
              {slides.map((_, i) => (
                <Pressable
                  key={i}
                  onPress={() => setCurrentSlide(i)}
                  style={[
                    styles.dot,
                    {
                      backgroundColor: i === currentSlide ? colors.brandPrimary : colors.border,
                      width: i === currentSlide ? 20 : 7,
                    },
                  ]}
                />
              ))}
            </View>

            {/* Buttons */}
            <View style={styles.btnRow}>
              {currentSlide > 0 && (
                <Pressable
                  onPress={handlePrev}
                  style={[styles.navBtn, { borderColor: colors.border, backgroundColor: colors.surfaceSecondary }]}
                >
                  <Ionicons name="arrow-back" size={15} color={colors.onSurface} />
                  <Text style={[styles.navBtnText, { color: colors.onSurface, marginLeft: 4 }]}>{ui("Previous", "પાછળ")}</Text>
                </Pressable>
              )}

              <Pressable
                onPress={handleOpenFullGuide}
                style={[styles.textLinkBtn]}
              >
                <Text style={{ color: colors.brandPrimary, fontSize: 12, fontWeight: "700" }}>
                  {ui("Full Guide", "વિગતવાર ગાઇડ")}
                </Text>
              </Pressable>

              <Pressable
                onPress={handleNext}
                style={[styles.primaryNextBtn, { backgroundColor: colors.brandPrimary }]}
              >
                <Text style={styles.primaryNextText}>
                  {currentSlide === slides.length - 1 ? ui("Get Started", "શરૂ કરો") : ui("Next", "આગળ")}
                </Text>
                <Ionicons
                  name={currentSlide === slides.length - 1 ? "checkmark-circle" : "arrow-forward"}
                  size={16}
                  color="#061024"
                  style={{ marginLeft: 6 }}
                />
              </Pressable>
            </View>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(6, 16, 36, 0.72)",
    justifyContent: "center",
    alignItems: "center",
  },
  modalBox: {
    borderRadius: Radius.lg,
    borderWidth: 1,
    overflow: "hidden",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.25,
    shadowRadius: 20,
    elevation: 15,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
  },
  headerLeft: {
    flexDirection: "row",
    alignItems: "center",
  },
  logoBadge: {
    width: 36,
    height: 36,
    borderRadius: Radius.md,
    justifyContent: "center",
    alignItems: "center",
  },
  mainTitle: {
    fontSize: 16,
    fontWeight: "800",
  },
  subTitle: {
    fontSize: 11,
    fontWeight: "500",
  },
  closeBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: "center",
    alignItems: "center",
  },
  bodyContent: {
    padding: Spacing.lg,
  },
  badgeRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: Spacing.sm,
  },
  stepBadge: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: Radius.sm,
  },
  stepBadgeText: {
    fontSize: 11,
    fontWeight: "800",
    marginLeft: 6,
  },
  slideHeadingGu: {
    fontSize: 19,
    fontWeight: "800",
    marginTop: 2,
  },
  slideHeadingEn: {
    fontSize: 12,
    fontWeight: "600",
    marginBottom: Spacing.md,
  },
  mockupWrapper: {
    marginVertical: Spacing.sm,
  },
  mockupContainer: {
    borderRadius: Radius.md,
    borderWidth: 1,
    overflow: "hidden",
    minHeight: 140,
    justifyContent: "center",
  },
  mockHeader: {
    flexDirection: "row",
    alignItems: "center",
    padding: 12,
  },
  mockAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#C5A059",
    justifyContent: "center",
    alignItems: "center",
  },
  mockBody: {
    padding: 12,
  },
  mockInfoRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 4,
  },
  mockInfoText: {
    fontSize: 11,
    marginLeft: 6,
    fontWeight: "500",
  },
  verifiedBadge: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 6,
    padding: 6,
    borderRadius: Radius.sm,
  },
  mockCardTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderBottomWidth: 1,
  },
  partyLineBox: {
    marginTop: 8,
    padding: 8,
    borderRadius: Radius.sm,
    borderWidth: 1,
  },
  templateGridPreview: {
    flexDirection: "row",
    flexWrap: "wrap",
    padding: 8,
    justifyContent: "space-between",
  },
  mockTplCard: {
    width: "48%",
    padding: 8,
    borderRadius: Radius.sm,
    borderWidth: 1,
    marginBottom: 8,
  },
  mockTplName: {
    fontSize: 11,
    fontWeight: "700",
    marginTop: 4,
  },
  autoSaveIndicator: {
    flexDirection: "row",
    alignItems: "center",
    padding: 8,
  },
  mockInputPill: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderRadius: Radius.sm,
    borderWidth: 1,
    marginTop: 2,
  },
  pdfSimSheet: {
    flexDirection: "row",
    padding: 10,
    backgroundColor: "#FAFAFA",
  },
  pdfMarginRuler: {
    width: 24,
    borderRightWidth: 1,
    borderRightColor: "#E2E8F0",
    borderStyle: "dashed",
    justifyContent: "center",
    alignItems: "center",
  },
  pdfTextContent: {
    flex: 1,
    paddingLeft: 12,
  },
  pdfHeader: {
    fontSize: 10,
    fontWeight: "700",
    color: "#1A202C",
  },
  pdfSub: {
    fontSize: 9,
    color: "#4A5568",
    marginBottom: 4,
  },
  pdfSubject: {
    fontSize: 9,
    fontWeight: "700",
    color: "#2B6CB0",
    marginBottom: 4,
  },
  pdfBody: {
    fontSize: 8.5,
    color: "#4A5568",
    lineHeight: 12,
  },
  pdfSignLine: {
    alignItems: "flex-end",
    marginTop: 8,
  },
  descBox: {
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
    marginTop: Spacing.sm,
  },
  descGu: {
    fontSize: 13,
    fontWeight: "600",
    lineHeight: 19,
  },
  descEn: {
    fontSize: 11,
    marginTop: 4,
    lineHeight: 16,
  },
  footer: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderTopWidth: 1,
  },
  dotsRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  dot: {
    height: 7,
    borderRadius: 3.5,
    marginRight: 5,
  },
  btnRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  navBtn: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: Radius.sm,
    borderWidth: 1,
    marginRight: 8,
  },
  navBtnText: {
    fontSize: 12,
    fontWeight: "700",
  },
  textLinkBtn: {
    paddingHorizontal: 8,
    paddingVertical: 6,
    marginRight: 8,
  },
  primaryNextBtn: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: Radius.sm,
  },
  primaryNextText: {
    fontSize: 13,
    fontWeight: "800",
    color: "#061024",
  },
});

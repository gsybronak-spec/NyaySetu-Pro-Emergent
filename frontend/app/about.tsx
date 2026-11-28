import React from "react";
import { Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";
import { SafeAreaView } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAppLanguage } from "@/src/context/AppLanguageContext";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";
import { safeBack } from "@/src/utils/navigation";

export default function AboutScreen() {
  const { colors, isDark } = useTheme();
  const { t, ui } = useAppLanguage();
  const { isDesktop } = useResponsive();

  const handleBack = () => safeBack("/(tabs)/profile");

  const features = [
    {
      icon: "document-text",
      title: ui("21 Authoritative Court Templates", "૨૧ અધિકૃત કોર્ટ અરજીઓ"),
      desc: ui(
        "Pre-configured according to authoritative Gujarat judiciary practices with 100% legal verbatim accuracy in Gujarati and English.",
        "ગુજરાતની કોર્ટ કાર્યપદ્ધતિ મુજબ ૧૦૦% ચોકસાઈ સાથે ગુજરાતી અને અંગ્રેજીમાં તૈયાર અરજીઓ."
      ),
    },
    {
      icon: "file-tray-full",
      title: ui("Case Master Data Management", "કેસ માસ્ટર ડેટા મેનેજમેન્ટ"),
      desc: ui(
        "Enter case numbers, parties, and court details once. Every routine application automatically inherits all relevant details.",
        "કેસ નંબર, પક્ષકારો અને કોર્ટની વિગતો એકવાર દાખલ કરો — દરેક અરજીમાં આપોઆપ ભરાઈ જશે."
      ),
    },
    {
      icon: "print",
      title: ui("High-Fidelity Document Generation", "ઉચ્ચ ગુણવત્તાવાળા દસ્તાવેજો"),
      desc: ui(
        "Export court-ready printouts in PDF, Microsoft Word (.docx), LibreOffice (.odt), and high-resolution images.",
        "PDF, Microsoft Word (.docx), LibreOffice (.odt) અને ઉચ્ચ રિઝોલ્યુશન ઈમેજમાં પ્રિન્ટ-રેડી ફાઇલો."
      ),
    },
    {
      icon: "shield-checkmark",
      title: ui("Bank-Grade Privacy & Security", "બેંક-ગ્રેડ ગોપનીયતા અને સુરક્ષા"),
      desc: ui(
        "Client documents and case files are encrypted in transit and at rest with role-based access control.",
        "અસીલોના દસ્તાવેજો અને કેસ ફાઇલો સંપૂર્ણ સુરક્ષિત અને એન્ક્રિપ્ટેડ રાખવામાં આવે છે."
      ),
    },
  ];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top", "bottom"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Pressable onPress={handleBack} hitSlop={8} testID="about-back-btn">
          <Ionicons name="arrow-back" size={24} color={colors.onSurface} />
        </Pressable>
        <Text style={[styles.h1, { color: colors.onSurface }]}>{ui("About NyaySetu Pro", "ન્યાયસેતુ પ્રો વિશે")}</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={[styles.container, isDesktop && styles.desktopContainer]}>
        {/* Branding header */}
        <View style={styles.brandBox}>
          <Image
            source={Platform.OS === "web" ? "/logo.webp" : require("../assets/images/logo.png")}
            style={styles.logo}
            contentFit="contain"
           accessibilityLabel="NyaySetu Pro Logo" />
          <Text style={[styles.appName, { color: colors.onSurface }]}>NyaySetu Pro</Text>
          <Text style={[styles.tagline, { color: colors.brandPrimary }]}>{t("tagline")}</Text>
          <View style={[styles.versionBadge, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
            <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "700" }}>{ui("Version 2.5 Production", "વર્ઝન 2.5 પ્રોડક્શન")}</Text>
          </View>
        </View>

        {/* Mission Statement */}
        <View style={[styles.card, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
          <Text style={[styles.sectionTitle, { color: colors.brandPrimary }]}>{ui("OUR MISSION", "અમારું ધ્યેય")}</Text>
          <Text style={[styles.bodyText, { color: colors.onSurface }]}>
            {ui(
              "NyaySetu Pro is India's dedicated legal productivity platform built specifically for practicing advocates in Gujarat and across India. We eliminate repetitive manual drafting, formatting delays, and typographical errors so advocates can focus on legal strategy, client advocacy, and courtroom presentation.",
              "NyaySetu Pro ખાસ ગુજરાત અને ભારતના પ્રેક્ટિસિંગ એડવોકેટ્સ માટે બનાવેલું કાનૂની ડ્રાફ્ટિંગ પ્લેટફોર્મ છે. અમે વારંવારની ટાઇપિંગ અને ફોર્મેટિંગની ઝંઝટ દૂર કરીએ છીએ જેથી વકીલો કોર્ટ દલીલો અને કેસની રણનીતિ પર ધ્યાન આપી શકે."
            )}
          </Text>
        </View>

        {/* Key Features */}
        <Text style={[styles.sectionHeading, { color: colors.onSurfaceSecondary }]}>{ui("CORE CAPABILITIES", "મુખ્ય સુવિધાઓ")}</Text>
        <View style={{ gap: Spacing.sm }}>
          {features.map((f, i) => (
            <View key={i} style={[styles.featureCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
              <View style={[styles.featureIcon, { backgroundColor: colors.brandPrimary + "20" }]}>
                <Ionicons name={f.icon as any} size={22} color={colors.brandPrimary} />
              </View>
              <View style={{ flex: 1, marginLeft: Spacing.md }}>
                <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 14 }}>{f.title}</Text>
                <Text style={{ color: colors.muted, fontSize: 12, marginTop: 3, lineHeight: 18 }}>{f.desc}</Text>
              </View>
            </View>
          ))}
        </View>

        {/* Legal & Compliance Links */}
        <Text style={[styles.sectionHeading, { color: colors.onSurfaceSecondary, marginTop: Spacing.xl }]}>{ui("LEGAL & POLICIES", "કાયદાકીય નીતિઓ")}</Text>
        <View style={[styles.linksCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
          <Pressable
            testID="about-link-privacy"
            onPress={() => router.push("/legal/privacy" as any)}
            style={styles.linkRow}
          >
            <Ionicons name="document-lock-outline" size={18} color={colors.onSurface} />
            <Text style={[styles.linkText, { color: colors.onSurface }]}>{ui("Privacy Policy", "ગોપનીયતા નીતિ")}</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.muted} />
          </Pressable>
          <View style={[styles.divider, { backgroundColor: colors.border }]} />
          <Pressable
            testID="about-link-terms"
            onPress={() => router.push("/legal/terms" as any)}
            style={styles.linkRow}
          >
            <Ionicons name="shield-checkmark-outline" size={18} color={colors.onSurface} />
            <Text style={[styles.linkText, { color: colors.onSurface }]}>{ui("Terms & Conditions", "નિયમો અને શરતો")}</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.muted} />
          </Pressable>
          <View style={[styles.divider, { backgroundColor: colors.border }]} />
          <Pressable
            testID="about-link-refund"
            onPress={() => router.push("/legal/refund" as any)}
            style={styles.linkRow}
          >
            <Ionicons name="refresh-outline" size={18} color={colors.onSurface} />
            <Text style={[styles.linkText, { color: colors.onSurface }]}>{ui("Refund Policy", "રિફંડ નીતિ")}</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.muted} />
          </Pressable>
        </View>

        <Text style={[styles.footerText, { color: colors.muted }]}>
          {ui(
            `© ${new Date().getFullYear()} NyaySetu Pro. All rights reserved. Made with pride for Indian Advocates.`,
            `© ${new Date().getFullYear()} NyaySetu Pro. સર્વ હક્ક અનામત. ભારતીય એડવોકેટ્સ માટે ગૌરવ સાથે નિર્મિત.`
          )}
        </Text>
        <View style={{ height: Spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
  },
  h1: { fontSize: 18, fontWeight: "700" },
  container: {
    padding: Spacing.xl,
  },
  desktopContainer: {
    maxWidth: 640,
    alignSelf: "center",
    width: "100%",
  },
  brandBox: {
    alignItems: "center",
    marginVertical: Spacing.lg,
  },
  logo: {
    width: 72,
    height: 72,
    marginBottom: Spacing.sm,
  },
  appName: {
    fontSize: 24,
    fontWeight: "800",
  },
  tagline: {
    fontSize: 14,
    fontWeight: "600",
    marginTop: 2,
  },
  versionBadge: {
    paddingHorizontal: Spacing.md,
    paddingVertical: 4,
    borderRadius: Radius.pill,
    borderWidth: 1,
    marginTop: Spacing.md,
  },
  card: {
    padding: Spacing.lg,
    borderRadius: Radius.md,
    borderWidth: 1,
    marginBottom: Spacing.xl,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: Spacing.xs,
  },
  sectionHeading: {
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: Spacing.md,
  },
  bodyText: {
    fontSize: 13.5,
    lineHeight: 21,
  },
  featureCard: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  featureIcon: {
    width: 44,
    height: 44,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  linksCard: {
    borderRadius: Radius.md,
    borderWidth: 1,
    overflow: "hidden",
  },
  linkRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
  },
  linkText: {
    fontSize: 14,
    fontWeight: "600",
    marginLeft: Spacing.md,
    flex: 1,
  },
  divider: {
    height: 1,
  },
  footerText: {
    fontSize: 12,
    textAlign: "center",
    marginTop: Spacing.xl,
    lineHeight: 18,
  },
});

import React from "react";
import { Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";
import { SafeAreaView } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";

export default function AboutScreen() {
  const { colors, isDark } = useTheme();
  const { isDesktop } = useResponsive();

  const handleBack = () => {
    if (router.canGoBack()) {
      router.back();
    } else {
      router.replace("/(tabs)/profile" as any);
    }
  };

  const features = [
    {
      icon: "document-text",
      title: "21 Authoritative Court Templates",
      desc: "Pre-configured according to authoritative Gujarat judiciary practices with 100% legal verbatim accuracy in Gujarati and English.",
    },
    {
      icon: "file-tray-full",
      title: "Case Master Data Management",
      desc: "Enter case numbers, parties, and court details once. Every routine application automatically inherits all relevant details.",
    },
    {
      icon: "print",
      title: "High-Fidelity Document Generation",
      desc: "Export court-ready printouts in PDF, Microsoft Word (.docx), LibreOffice (.odt), and high-resolution images.",
    },
    {
      icon: "shield-checkmark",
      title: "Bank-Grade Privacy & Security",
      desc: "Client documents and case files are encrypted in transit and at rest with role-based access control.",
    },
  ];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top", "bottom"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Pressable onPress={handleBack} hitSlop={8} testID="about-back-btn">
          <Ionicons name="arrow-back" size={24} color={colors.onSurface} />
        </Pressable>
        <Text style={[styles.h1, { color: colors.onSurface }]}>About NyaySetu Pro</Text>
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
          <Text style={[styles.tagline, { color: colors.brandPrimary }]}>The New Era of Advocacy</Text>
          <View style={[styles.versionBadge, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
            <Text style={{ color: colors.muted, fontSize: 12, fontWeight: "700" }}>Version 2.5 Production</Text>
          </View>
        </View>

        {/* Mission Statement */}
        <View style={[styles.card, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
          <Text style={[styles.sectionTitle, { color: colors.brandPrimary }]}>OUR MISSION</Text>
          <Text style={[styles.bodyText, { color: colors.onSurface }]}>
            NyaySetu Pro is India's dedicated legal productivity platform built specifically for practicing advocates in Gujarat and across India.
            We eliminate repetitive manual drafting, formatting delays, and typographical errors so advocates can focus on legal strategy, client advocacy, and courtroom presentation.
          </Text>
        </View>

        {/* Key Features */}
        <Text style={[styles.sectionHeading, { color: colors.onSurfaceSecondary }]}>CORE CAPABILITIES</Text>
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
        <Text style={[styles.sectionHeading, { color: colors.onSurfaceSecondary, marginTop: Spacing.xl }]}>LEGAL & POLICIES</Text>
        <View style={[styles.linksCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
          <Pressable
            testID="about-link-privacy"
            onPress={() => router.push("/legal/privacy" as any)}
            style={styles.linkRow}
          >
            <Ionicons name="document-lock-outline" size={18} color={colors.onSurface} />
            <Text style={[styles.linkText, { color: colors.onSurface }]}>Privacy Policy</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.muted} />
          </Pressable>
          <View style={[styles.divider, { backgroundColor: colors.border }]} />
          <Pressable
            testID="about-link-terms"
            onPress={() => router.push("/legal/terms" as any)}
            style={styles.linkRow}
          >
            <Ionicons name="shield-checkmark-outline" size={18} color={colors.onSurface} />
            <Text style={[styles.linkText, { color: colors.onSurface }]}>Terms & Conditions</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.muted} />
          </Pressable>
          <View style={[styles.divider, { backgroundColor: colors.border }]} />
          <Pressable
            testID="about-link-refund"
            onPress={() => router.push("/legal/refund" as any)}
            style={styles.linkRow}
          >
            <Ionicons name="refresh-outline" size={18} color={colors.onSurface} />
            <Text style={[styles.linkText, { color: colors.onSurface }]}>Refund Policy</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.muted} />
          </Pressable>
        </View>

        <Text style={[styles.footerText, { color: colors.muted }]}>
          © {new Date().getFullYear()} NyaySetu Pro. All rights reserved. Made with pride for Indian Advocates.
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

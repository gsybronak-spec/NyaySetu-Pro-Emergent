import React from "react";
import { Alert, Linking, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";

export default function SupportScreen() {
  const { colors, isDark } = useTheme();
  const { isDesktop } = useResponsive();

  const handleEmail = () => {
    const url = "mailto:support@nyaysetupro.in?subject=NyaySetu%20Pro%20Support%20Request";
    Linking.canOpenURL(url)
      .then((supported) => {
        if (supported) {
          Linking.openURL(url);
        } else {
          Alert.alert("Contact Support", "Please send an email to: support@nyaysetupro.in");
        }
      })
      .catch(() => {
        Alert.alert("Contact Support", "Please send an email to: support@nyaysetupro.in");
      });
  };

  const handleBack = () => {
    if (router.canGoBack()) {
      router.back();
    } else {
      router.replace("/(tabs)/profile" as any);
    }
  };

  const faqs = [
    {
      q: "How do template credits work?",
      a: "Each time you download a completed court application (PDF, DOCX, ODT, or Image), 1 credit is consumed. Incomplete drafts and previewing do not consume credits.",
    },
    {
      q: "How do I choose Gujarati or English?",
      a: "When you open any template from the library or from a case, you can select whether you wish to draft in Gujarati (અધિકૃત કોર્ટ અરજી) or English.",
    },
    {
      q: "How do advocate names work on documents?",
      a: "Your profile stores both your Gujarati and English advocate names. Gujarati documents automatically apply your Gujarati name, and English documents automatically apply your English name.",
    },
  ];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top", "bottom"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Pressable onPress={handleBack} hitSlop={8} testID="support-back-btn">
          <Ionicons name="arrow-back" size={24} color={colors.onSurface} />
        </Pressable>
        <Text style={[styles.h1, { color: colors.onSurface }]}>Contact Support</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={[styles.container, isDesktop && styles.desktopContainer]}>
        {/* Support hero banner */}
        <View style={[styles.heroCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
          <View style={[styles.iconCircle, { backgroundColor: colors.brandPrimary + "20" }]}>
            <Ionicons name="headset" size={32} color={colors.brandPrimary} />
          </View>
          <Text style={[styles.heroTitle, { color: colors.onSurface }]}>How can we assist you?</Text>
          <Text style={[styles.heroSub, { color: colors.muted }]}>
            Our legal tech support team is available Monday to Saturday (9:00 AM – 7:00 PM IST) to assist Indian Advocates.
          </Text>
        </View>

        {/* Primary Contact Channel */}
        <Text style={[styles.sectionTitle, { color: colors.onSurfaceSecondary }]}>DIRECT SUPPORT CHANNELS</Text>

        <Pressable
          testID="support-email-card"
          onPress={handleEmail}
          style={({ pressed }) => [
            styles.channelCard,
            { backgroundColor: colors.surfaceSecondary, borderColor: colors.border },
            pressed && { opacity: 0.8 },
          ]}
        >
          <View style={[styles.channelIcon, { backgroundColor: "#3B82F620" }]}>
            <Ionicons name="mail" size={24} color="#3B82F6" />
          </View>
          <View style={{ flex: 1, marginLeft: Spacing.md }}>
            <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 15 }}>Email Support</Text>
            <Text style={{ color: colors.brandPrimary, fontSize: 14, fontWeight: "600", marginTop: 2 }}>
              support@nyaysetupro.in
            </Text>
            <Text style={{ color: colors.muted, fontSize: 12, marginTop: 4 }}>
              Tap to compose email — Average response under 2 hours
            </Text>
          </View>
          <Ionicons name="open-outline" size={20} color={colors.muted} />
        </Pressable>

        {/* FAQs */}
        <Text style={[styles.sectionTitle, { color: colors.onSurfaceSecondary, marginTop: Spacing.xl }]}>
          FREQUENTLY ASKED QUESTIONS
        </Text>

        <View style={{ gap: Spacing.sm }}>
          {faqs.map((faq, idx) => (
            <View
              key={idx}
              style={[styles.faqCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}
            >
              <View style={{ flexDirection: "row", alignItems: "flex-start" }}>
                <Ionicons name="help-circle-outline" size={18} color={colors.brandPrimary} style={{ marginTop: 2 }} />
                <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 14, marginLeft: 8, flex: 1 }}>
                  {faq.q}
                </Text>
              </View>
              <Text style={{ color: colors.muted, fontSize: 13, marginTop: Spacing.xs, lineHeight: 19, paddingLeft: 26 }}>
                {faq.a}
              </Text>
            </View>
          ))}
        </View>

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
  heroCard: {
    padding: Spacing.xl,
    borderRadius: Radius.lg,
    borderWidth: 1,
    alignItems: "center",
    textAlign: "center",
    marginBottom: Spacing.xl,
  },
  iconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: Spacing.md,
  },
  heroTitle: {
    fontSize: 20,
    fontWeight: "700",
    textAlign: "center",
  },
  heroSub: {
    fontSize: 13,
    textAlign: "center",
    marginTop: Spacing.xs,
    lineHeight: 19,
    maxWidth: 460,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: Spacing.md,
  },
  channelCard: {
    flexDirection: "row",
    alignItems: "center",
    padding: Spacing.lg,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  channelIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  faqCard: {
    padding: Spacing.lg,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
});

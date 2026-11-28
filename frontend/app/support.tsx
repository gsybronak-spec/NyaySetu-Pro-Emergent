import React from "react";
import { Alert, Linking, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAppLanguage } from "@/src/context/AppLanguageContext";
import { Radius, Spacing } from "@/src/theme/tokens";
import { useResponsive } from "@/src/hooks/useResponsive";
import { safeBack } from "@/src/utils/navigation";

export default function SupportScreen() {
  const { colors, isDark } = useTheme();
  const { ui } = useAppLanguage();
  const { isDesktop } = useResponsive();

  const handleEmail = () => {
    const url = "mailto:support@nyaysetupro.in?subject=NyaySetu%20Pro%20Support%20Request";
    Linking.canOpenURL(url)
      .then((supported) => {
        if (supported) {
          Linking.openURL(url);
        } else {
          Alert.alert(ui("Contact Support", "સહાય સંપર્ક"), ui("Please send an email to: support@nyaysetupro.in", "કૃપા કરીને આ ઈમેલ પર સંપર્ક કરો: support@nyaysetupro.in"));
        }
      })
      .catch(() => {
        Alert.alert(ui("Contact Support", "સહાય સંપર્ક"), ui("Please send an email to: support@nyaysetupro.in", "કૃપા કરીને આ ઈમેલ પર સંપર્ક કરો: support@nyaysetupro.in"));
      });
  };

  const handleBack = () => safeBack("/(tabs)/profile");

  const faqs = [
    {
      q: ui("How do template credits work?", "ટેમ્પલેટ ક્રેડિટ્સ કેવી રીતે કામ કરે છે?"),
      a: ui(
        "Each time you download a completed court application (PDF, DOCX, ODT, or Image), 1 credit is consumed. Incomplete drafts and previewing do not consume credits.",
        "જ્યારે પણ તમે પૂર્ણ કરેલી કોર્ટ અરજી (PDF, DOCX, ODT અથવા ઈમેજ) ડાઉનલોડ કરો છો ત્યારે ૧ ક્રેડિટ વપરાય છે. અધૂરા ડ્રાફ્ટ અને પ્રિવ્યુ માટે કોઈ ક્રેડિટ કપાતી નથી."
      ),
    },
    {
      q: ui("How do I choose Gujarati or English?", "ગુજરાતી અથવા અંગ્રેજી ભાષા કેવી રીતે પસંદ કરવી?"),
      a: ui(
        "When you open any template from the library or from a case, you can select whether you wish to draft in Gujarati or English.",
        "જ્યારે તમે લાયબ્રેરી અથવા કેસમાંથી કોઈપણ અરજી ખોલો છો, ત્યારે તમે ગુજરાતી અથવા અંગ્રેજી ભાષામાં અરજી બનાવવાનું પસંદ કરી શકો છો."
      ),
    },
    {
      q: ui("How do advocate names work on documents?", "દસ્તાવેજો પર એડવોકેટનું નામ કેવી રીતે આવે છે?"),
      a: ui(
        "Your profile stores both your Gujarati and English advocate names. Gujarati documents automatically apply your Gujarati name, and English documents automatically apply your English name.",
        "તમારી પ્રોફાઇલમાં ગુજરાતી અને અંગ્રેજી બંને નામ સાચવેલા છે. ગુજરાતી અરજીમાં આપોઆપ ગુજરાતી નામ અને અંગ્રેજી અરજીમાં અંગ્રેજી નામ પ્રિન્ટ થાય છે."
      ),
    },
  ];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top", "bottom"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Pressable onPress={handleBack} hitSlop={8} testID="support-back-btn">
          <Ionicons name="arrow-back" size={24} color={colors.onSurface} />
        </Pressable>
        <Text style={[styles.h1, { color: colors.onSurface }]}>{ui("Contact Support", "સહાય સંપર્ક")}</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={[styles.container, isDesktop && styles.desktopContainer]}>
        {/* Support hero banner */}
        <View style={[styles.heroCard, { backgroundColor: colors.surfaceSecondary, borderColor: colors.border }]}>
          <View style={[styles.iconCircle, { backgroundColor: colors.brandPrimary + "20" }]}>
            <Ionicons name="headset" size={32} color={colors.brandPrimary} />
          </View>
          <Text style={[styles.heroTitle, { color: colors.onSurface }]}>{ui("How can we assist you?", "અમે તમને કેવી રીતે મદદ કરી શકીએ?")}</Text>
          <Text style={[styles.heroSub, { color: colors.muted }]}>
            {ui(
              "Our legal tech support team is available Monday to Saturday (9:00 AM – 7:00 PM IST) to assist Indian Advocates.",
              "અમારી સપોર્ટ ટીમ સોમવારથી શનિવાર (સવારે 9:00 થી સાંજે 7:00 IST) એડવોકેટ્સની મદદ માટે ઉપલબ્ધ છે."
            )}
          </Text>
        </View>

        {/* Primary Contact Channel */}
        <Text style={[styles.sectionTitle, { color: colors.onSurfaceSecondary }]}>{ui("DIRECT SUPPORT CHANNELS", "સીધો સંપર્ક")}</Text>

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
            <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 15 }}>{ui("Email Support", "ઈમેલ સપોર્ટ")}</Text>
            <Text style={{ color: colors.brandPrimary, fontSize: 14, fontWeight: "600", marginTop: 2 }}>
              support@nyaysetupro.in
            </Text>
            <Text style={{ color: colors.muted, fontSize: 12, marginTop: 4 }}>
              {ui("Tap to compose email — Average response under 2 hours", "ઈમેલ મોકલવા ટૅપ કરો — સરેરાશ ૨ કલાકમાં જવાબ")}
            </Text>
          </View>
          <Ionicons name="open-outline" size={20} color={colors.muted} />
        </Pressable>

        {/* FAQs */}
        <Text style={[styles.sectionTitle, { color: colors.onSurfaceSecondary, marginTop: Spacing.xl }]}>
          {ui("FREQUENTLY ASKED QUESTIONS", "વારંવાર પૂછાતા પ્રશ્નો")}
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

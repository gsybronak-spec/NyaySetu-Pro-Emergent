import { ScrollView, StyleSheet, Text, View, Pressable } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";

import { useTheme } from "@/src/theme/ThemeContext";
import { Spacing } from "@/src/theme/tokens";

const DOCS: Record<string, { title: string; sections: { h: string; body: string }[] }> = {
  privacy: {
    title: "Privacy Policy",
    sections: [
      {
        h: "Information We Collect",
        body: "NyaySetu Pro collects the information you provide when you register and use the platform — name, mobile number, professional details, and the case and document data you enter to draft legal applications.",
      },
      {
        h: "How We Use Your Information",
        body: "Your data is used to provide the drafting service, maintain your account, wallet and history, and to support document generation. We do not sell your personal information.",
      },
      {
        h: "Data Security",
        body: "Your data is stored securely and access is limited to your own account. You remain responsible for the accuracy of every document you generate and file.",
      },
      {
        h: "Status",
        body: "Pending legal review. This policy will be finalized with our legal counsel before going into effect.",
      },
    ],
  },
  terms: {
    title: "Terms & Conditions",
    sections: [
      {
        h: "Purpose",
        body: "NyaySetu Pro is a document-drafting productivity tool for advocates. Generated documents are drafts for review; they are not a substitute for professional legal judgment.",
      },
      {
        h: "Lawyer Responsibility",
        body: "By using NyaySetu Pro you agree to review each generated document before filing. The advocate remains solely responsible for document accuracy and its legal consequences.",
      },
      {
        h: "Credits & Wallet",
        body: "Template credits are consumed only when a final document is downloaded. Failed generations are refunded automatically. Credit terms are described in the Refund Policy.",
      },
      {
        h: "Status",
        body: "Pending legal review. These terms will be finalized with our legal counsel before going into effect.",
      },
    ],
  },
  refund: {
    title: "Refund Policy",
    sections: [
      {
        h: "Consumed Credits",
        body: "Template credits that have been consumed by a successful document download are non-refundable.",
      },
      {
        h: "Failed Transactions",
        body: "Unused credits from failed transactions are automatically credited back to your wallet. If a document generation fails, the credit is refunded immediately.",
      },
      {
        h: "Unused Credits",
        body: "Unused purchased credits remain available in your wallet until used.",
      },
      {
        h: "Status",
        body: "Pending legal review. This policy will be finalized with our legal counsel before going into effect.",
      },
    ],
  },
};

export default function LegalDoc() {
  const { colors } = useTheme();
  const { doc } = useLocalSearchParams<{ doc: string }>();
  const data = DOCS[String(doc)] || DOCS.privacy;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top"]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Pressable testID="legal-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
        </Pressable>
        <Text style={[styles.h1, { color: colors.onSurface }]}>{data.title}</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: Spacing.lg, paddingBottom: 120 }}>
        <View style={[styles.pending, { backgroundColor: colors.brandTertiary, borderColor: colors.brandPrimary + "40" }]}>
          <Ionicons name="time-outline" size={16} color={colors.onBrandTertiary} />
          <Text style={{ color: colors.onBrandTertiary, fontSize: 12, flex: 1, marginLeft: 6 }}>
            Pending legal review — this document is informational and not yet legally approved.
          </Text>
        </View>
        {data.sections.map((s) => (
          <View key={s.h} style={{ marginBottom: Spacing.lg }}>
            <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 15, marginBottom: 4 }}>{s.h}</Text>
            <Text style={{ color: colors.onSurfaceSecondary, fontSize: 13, lineHeight: 21 }}>{s.body}</Text>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, borderBottomWidth: StyleSheet.hairlineWidth,
  },
  h1: { fontSize: 16, fontWeight: "700", fontFamily: "serif" },
  pending: {
    flexDirection: "row", alignItems: "flex-start", padding: Spacing.md,
    borderRadius: 12, borderWidth: 1, marginBottom: Spacing.lg,
  },
});

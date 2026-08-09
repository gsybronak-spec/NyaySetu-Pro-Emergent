import { StyleSheet, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { Button } from "@/src/components/Button";
import { Spacing } from "@/src/theme/tokens";

export default function Congrats() {
  return (
    <LinearGradient colors={["#061024", "#0B1B3D", "#112240"]} style={{ flex: 1 }}>
      <View style={styles.container}>
        <View style={styles.badge}>
          <Ionicons name="gift" size={56} color="#C5A059" />
        </View>
        <Text style={styles.title}>Congratulations!</Text>
        <Text style={styles.big}>
          You received <Text style={{ color: "#C5A059" }}>5 FREE</Text> Templates
        </Text>
        <Text style={styles.sub}>Start creating professional court applications now.</Text>

        <View style={styles.rowStats}>
          <Stat label="Free Credits" value="5" />
          <Stat label="Templates" value="12+" />
          <Stat label="Languages" value="EN / GU" />
        </View>

        <View style={{ height: Spacing.xxl }} />
        <Button testID="congrats-start-button" title="Start Using NyaySetu Pro" onPress={() => router.replace("/(tabs)/home")} />
      </View>
    </LinearGradient>
  );
}

function Stat({ label, value }: any) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: Spacing.xl, justifyContent: "center" },
  badge: {
    alignSelf: "center",
    width: 108,
    height: 108,
    borderRadius: 30,
    backgroundColor: "rgba(197,160,89,0.12)",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "rgba(197,160,89,0.4)",
    marginBottom: Spacing.xl,
  },
  title: { color: "#C5A059", fontSize: 18, textAlign: "center", letterSpacing: 2, textTransform: "uppercase", fontWeight: "700" },
  big: { color: "#FDFDFD", fontSize: 30, textAlign: "center", marginTop: Spacing.sm, fontFamily: "serif", fontWeight: "700" },
  sub: { color: "#A6B1C2", fontSize: 14, textAlign: "center", marginTop: Spacing.md },
  rowStats: { flexDirection: "row", justifyContent: "space-between", marginTop: Spacing.xxl, paddingHorizontal: Spacing.md },
  stat: {
    flex: 1,
    marginHorizontal: 4,
    paddingVertical: Spacing.md,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.06)",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(197,160,89,0.15)",
  },
  statValue: { color: "#FDFDFD", fontSize: 20, fontWeight: "700" },
  statLabel: { color: "#A6B1C2", fontSize: 11, marginTop: 4 },
});

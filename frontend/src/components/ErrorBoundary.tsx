import React, { Component, ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { safeBack } from "@/src/utils/navigation";
import { useAppLanguage } from "@/src/context/AppLanguageContext";

function ErrorFallback({
  fallbackTitle,
  errorMessage,
  onReset,
}: {
  fallbackTitle?: string;
  errorMessage?: string;
  onReset: () => void;
}) {
  const { t, ui } = useAppLanguage();
  return (
    <SafeAreaView style={styles.container} edges={["top", "bottom"]}>
      <View style={styles.card}>
        <View style={styles.iconCircle}>
          <Ionicons name="alert-circle-outline" size={36} color="#B91C1C" />
        </View>
        <Text style={styles.title}>{fallbackTitle || t("somethingWentWrong")}</Text>
        <Text style={styles.message}>
          {errorMessage ||
            ui(
              "An unexpected display error occurred. Please try reloading.",
              "અનપેક્ષિત ડિસ્પ્લે ભૂલ આવી છે. કૃપા કરીને ફરી લોડ કરો."
            )}
        </Text>
        <View style={styles.btnRow}>
          <Pressable
            testID="boundary-back-btn"
            onPress={() => safeBack("/(tabs)/home")}
            style={styles.backBtn}
          >
            <Text style={styles.backBtnTxt}>{t("back")}</Text>
          </Pressable>
          <Pressable
            testID="boundary-retry-btn"
            onPress={onReset}
            style={styles.retryBtn}
          >
            <Text style={styles.retryBtnTxt}>{t("retry")}</Text>
          </Pressable>
        </View>
      </View>
    </SafeAreaView>
  );
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallbackTitle?: string;
  onRetry?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: any) {
    console.error("[ErrorBoundary] Caught unhandled render exception:", error, info);
  }

  reset = () => {
    this.setState({ hasError: false, error: null });
    this.props.onRetry?.();
  };

  render() {
    if (this.state.hasError) {
      return (
        <ErrorFallback
          fallbackTitle={this.props.fallbackTitle}
          errorMessage={this.state.error?.message}
          onReset={this.reset}
        />
      );
    }

    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F9FAFB",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  card: {
    maxWidth: 420,
    width: "100%",
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 24,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#E5E7EB",
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 3,
  },
  iconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "#FEE2E2",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 16,
  },
  title: {
    fontSize: 17,
    fontWeight: "700",
    color: "#111827",
    textAlign: "center",
  },
  message: {
    fontSize: 13,
    color: "#6B7280",
    textAlign: "center",
    marginTop: 8,
    lineHeight: 18,
  },
  btnRow: {
    flexDirection: "row",
    gap: 12,
    marginTop: 24,
    width: "100%",
  },
  backBtn: {
    flex: 1,
    paddingVertical: 11,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#D1D5DB",
    alignItems: "center",
  },
  backBtnTxt: {
    color: "#374151",
    fontWeight: "600",
    fontSize: 13,
  },
  retryBtn: {
    flex: 1,
    paddingVertical: 11,
    borderRadius: 8,
    backgroundColor: "#0B1B3D",
    alignItems: "center",
  },
  retryBtnTxt: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 13,
  },
});

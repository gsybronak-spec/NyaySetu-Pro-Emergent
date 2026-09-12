import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  StyleProp,
  StyleSheet,
  Text,
  TextStyle,
  ViewStyle,
} from "react-native";
import { api } from "@/src/api/client";
import {
  loadRazorpayScript,
  preloadRazorpayScript,
  prepareRazorpayModal,
  RAZORPAY_THEME_COLOR,
  RAZORPAY_BACKDROP_COLOR,
  RAZORPAY_LOGO_URL,
} from "@/src/utils/razorpay";

export interface RazorpayCheckoutButtonProps {
  /** Amount in paise (e.g. 50000 for ₹500) or specify amountInRupees */
  amount?: number;
  /** Amount in rupees (e.g. 500 for ₹500) */
  amountInRupees?: number;
  currency?: string;
  receipt?: string;
  planId?: string;
  notes?: Record<string, string>;
  title?: string;
  description?: string;
  prefill?: {
    name?: string;
    email?: string;
    contact?: string;
  };
  style?: StyleProp<ViewStyle>;
  textStyle?: StyleProp<TextStyle>;
  disabled?: boolean;
  testID?: string;
  onSuccess?: (data: {
    razorpay_payment_id: string;
    razorpay_order_id: string;
    razorpay_signature: string;
    result: any;
  }) => void;
  onError?: (error: Error) => void;
  onCancel?: () => void;
}

export const RazorpayCheckoutButton: React.FC<RazorpayCheckoutButtonProps> = ({
  amount,
  amountInRupees,
  currency = "INR",
  receipt,
  planId,
  notes,
  title = "Pay with Razorpay",
  description = "Legal Services",
  prefill,
  style,
  textStyle,
  disabled = false,
  testID = "razorpay-checkout-button",
  onSuccess,
  onError,
  onCancel,
}) => {
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    preloadRazorpayScript();
  }, []);

  const calculateAmountPaise = (): number => {
    if (amount !== undefined && amount > 0) return Math.round(amount);
    if (amountInRupees !== undefined && amountInRupees > 0) return Math.round(amountInRupees * 100);
    return 50000;
  };

  const handleCheckout = async () => {
    if (loading || disabled) return;
    setLoading(true);

    try {
      const amountPaise = calculateAmountPaise();
      if (amountPaise < 100) {
        throw new Error("Minimum payment amount is 100 paise (1 INR).");
      }

      // STEP 1: Create order on backend concurrently with script load readiness check
      const [order] = await Promise.all([
        api.createOrder({
          amount: amountPaise,
          currency,
          receipt,
          plan_id: planId,
          notes,
        }),
        Platform.OS === "web" ? loadRazorpayScript() : Promise.resolve(),
      ]);

      if (!order?.order_id) {
        throw new Error("Could not initiate payment order with server.");
      }

      const keyId =
        order.key_id ||
        process.env.EXPO_PUBLIC_RAZORPAY_KEY_ID;

      if (!keyId) {
        throw new Error(
          "Razorpay Key ID is not configured. Please set EXPO_PUBLIC_RAZORPAY_KEY_ID or provide key_id in order response."
        );
      }

      prepareRazorpayModal();

      let paymentResult: {
        razorpay_payment_id: string;
        razorpay_order_id: string;
        razorpay_signature: string;
      };

      // STEP 2: Open Razorpay modal
      if (Platform.OS === "web") {
        const Razorpay = (window as any).Razorpay;
        if (!Razorpay) {
          throw new Error("Razorpay checkout script failed to initialize");
        }

        paymentResult = await new Promise((resolve, reject) => {
          const rz = new Razorpay({
            key: keyId,
            amount: order.amount || amountPaise,
            currency: order.currency || currency,
            order_id: order.order_id,
            name: "NyaySetu Pro",
            description,
            image: RAZORPAY_LOGO_URL,
            prefill: {
              name: prefill?.name || "",
              email: prefill?.email || "",
              contact: prefill?.contact || "",
            },
            theme: {
              color: RAZORPAY_THEME_COLOR,
              backdrop_color: RAZORPAY_BACKDROP_COLOR,
            },
            modal: {
              backdropclose: false,
              escape: true,
              handleback: true,
              confirm_close: true,
              animation: true,
              ondismiss: () => {
                onCancel?.();
                reject(new Error("Payment cancelled by user"));
              },
            },
            handler: (response: any) => resolve(response),
          });

          rz.on("payment.failed", (response: any) => {
            const reason =
              response?.error?.description ||
              response?.error?.reason ||
              "Payment transaction failed";
            reject(new Error(reason));
          });

          rz.open();
        });
      } else {
        const RazorpayCheckout = require("react-native-razorpay").default;
        const nativePayment = await RazorpayCheckout.open({
          key: keyId,
          amount: order.amount || amountPaise,
          currency: order.currency || currency,
          order_id: order.order_id,
          name: "NyaySetu Pro",
          description,
          image: RAZORPAY_LOGO_URL,
          prefill: {
            name: prefill?.name || "",
            email: prefill?.email || "",
            contact: prefill?.contact || "",
          },
          theme: { color: RAZORPAY_THEME_COLOR },
        });

        paymentResult = {
          razorpay_payment_id: nativePayment.razorpay_payment_id,
          razorpay_order_id: nativePayment.razorpay_order_id,
          razorpay_signature: nativePayment.razorpay_signature,
        };
      }

      // STEP 3: Verify signature on backend (POST /api/verify-payment)
      const verifyRes = await api.verifyPayment({
        razorpay_order_id: paymentResult.razorpay_order_id,
        razorpay_payment_id: paymentResult.razorpay_payment_id,
        razorpay_signature: paymentResult.razorpay_signature,
        plan_id: planId,
      });

      if (verifyRes?.success) {
        const successMsg = "Payment verified successfully!";
        if (Platform.OS === "web" && typeof window !== "undefined") {
          window.alert(successMsg);
        } else {
          Alert.alert("Success", successMsg);
        }
        onSuccess?.({
          ...paymentResult,
          result: verifyRes,
        });
      } else {
        throw new Error(verifyRes?.message || "Payment verification failed");
      }
    } catch (err: any) {
      if (err.message !== "Payment cancelled by user") {
        const errMsg = err?.message || "Payment failed. Please try again.";
        if (Platform.OS === "web" && typeof window !== "undefined") {
          window.alert(errMsg);
        } else {
          Alert.alert("Payment Error", errMsg);
        }
        onError?.(err);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Pressable
      testID={testID}
      onPress={handleCheckout}
      disabled={disabled || loading}
      style={[styles.button, style, (disabled || loading) && styles.disabled]}
    >
      {loading ? (
        <ActivityIndicator color="#FFFFFF" size="small" />
      ) : (
        <Text style={[styles.buttonText, textStyle]}>{title}</Text>
      )}
    </Pressable>
  );
};

const styles = StyleSheet.create({
  button: {
    backgroundColor: RAZORPAY_THEME_COLOR,
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
  },
  buttonText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 15,
  },
  disabled: {
    opacity: 0.6,
  },
});

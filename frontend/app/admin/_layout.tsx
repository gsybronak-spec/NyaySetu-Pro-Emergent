import { Stack } from "expo-router";
import { AdminAuthProvider } from "@/src/context/AdminAuthContext";

export default function AdminRootLayout() {
  return (
    <AdminAuthProvider>
      <Stack
        screenOptions={{
          headerShown: false,
          animation: "fade",
          contentStyle: { backgroundColor: "#061024" },
        }}
      />
    </AdminAuthProvider>
  );
}

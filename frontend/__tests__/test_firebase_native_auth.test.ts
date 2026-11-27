import assert from "assert";
import fs from "fs";
import Module from "module";
import path from "path";

const FRONTEND = path.resolve(__dirname, "..");

function loadUseFirebaseAuth(opts: {
  platformOs: "android" | "web";
  nativeMod: any;
  webConfigured?: boolean;
}) {
  const sucrase = require(path.join(FRONTEND, "node_modules/sucrase"));
  const filePath = path.join(FRONTEND, "src/hooks/useFirebaseAuth.ts");
  const code = sucrase.transform(fs.readFileSync(filePath, "utf8"), {
    transforms: ["typescript", "imports"],
    filePath,
  }).code;

  const origLoad = (Module as any)._load;
  (Module as any)._load = function (request: string, parent: any, isMain: boolean) {
    if (request === "react-native") return { Platform: { OS: opts.platformOs } };
    if (request === "@react-native-firebase/auth") return opts.nativeMod;
    if (request === "firebase/auth") return {};
    if (request === "@/src/firebase/config") {
      return {
        firebaseConfigured: Boolean(opts.webConfigured),
        getFirebaseAuth: () => (opts.webConfigured ? { web: true } : null),
      };
    }
    return origLoad.call(this, request, parent, isMain);
  };

  try {
    const mod = { exports: {} as any };
    const fn = new Function("exports", "require", "module", code);
    fn(mod.exports, (r: string) => (Module as any)._load(r, null, false), mod);
    return mod.exports;
  } finally {
    (Module as any)._load = origLoad;
  }
}

export async function runFirebaseNativeAuthTests() {
  console.log("=== EXECUTING NATIVE FIREBASE AUTH (RNFB v26 MODULAR) TESTS ===");

  // Verify installed @react-native-firebase/auth package exposes modular API without default export
  const rnfbDist = fs.readFileSync(
    path.join(FRONTEND, "node_modules/@react-native-firebase/auth/dist/module/index.js"),
    "utf8"
  );
  assert.ok(rnfbDist.includes("export function getAuth("), "Installed RNFB auth must export getAuth");
  assert.ok(rnfbDist.includes("export function signInWithPhoneNumber("), "Installed RNFB auth must export signInWithPhoneNumber");
  assert.ok(!rnfbDist.includes("export default"), "RNFB v26 has no export default (regression guard)");

  const authInstance = { _authTag: "rnfb-auth-v26" };
  const calls: string[] = [];

  // 1. Modular v26 API WITHOUT .default
  const modularAuth = loadUseFirebaseAuth({
    platformOs: "android",
    nativeMod: {
      getAuth: () => authInstance,
      signInWithPhoneNumber: async (auth: any, phone: string) => {
        assert.strictEqual(auth, authInstance);
        assert.strictEqual(phone, "+919898000001");
        calls.push("phone:" + phone);
        return {
          verificationId: "vid-1",
          confirm: async (otp: string) => {
            assert.strictEqual(otp, "654321");
            return { user: { getIdToken: async () => "fb-id-token-123" } };
          },
        };
      },
      signInWithEmailAndPassword: async (auth: any, email: string, pwd: string) => {
        assert.strictEqual(auth, authInstance);
        calls.push(`email:${email}:${pwd}`);
        return { user: { getIdToken: async () => "fb-email-token" } };
      },
      sendPasswordResetEmail: async (auth: any, email: string) => {
        assert.strictEqual(auth, authInstance);
        calls.push("reset:" + email);
      },
      verifyPasswordResetCode: async (auth: any, code: string) => {
        assert.strictEqual(auth, authInstance);
        calls.push("verify:" + code);
        return "user@example.com";
      },
      confirmPasswordReset: async (auth: any, code: string, pwd: string) => {
        assert.strictEqual(auth, authInstance);
        calls.push(`confirmReset:${code}:${pwd}`);
      },
      signOut: async (auth: any) => {
        assert.strictEqual(auth, authInstance);
        calls.push("signOut");
      },
    },
  });

  assert.strictEqual(modularAuth.isFirebaseConfigured(), true, "isFirebaseConfigured must return true for modular RNFB v26");
  const conf = await modularAuth.firebaseSendPhoneOtp("9898000001", null);
  assert.ok(conf && modularAuth.getPendingPhoneConfirmation() === conf);
  const idToken = await modularAuth.firebaseConfirmPhoneOtp(conf, "654321");
  assert.strictEqual(idToken, "fb-id-token-123");
  assert.strictEqual(modularAuth.getPendingPhoneConfirmation(), null);

  const emailRes = await modularAuth.firebaseEmailPasswordLogin("adv@example.com", "secret");
  assert.strictEqual(emailRes?.idToken, "fb-email-token");
  assert.strictEqual(await modularAuth.firebaseSendPasswordReset("adv@example.com"), true);
  assert.strictEqual(await modularAuth.firebaseVerifyPasswordResetCode("oob-1"), "user@example.com");
  await modularAuth.firebaseConfirmPasswordReset("oob-1", "NewPass123");
  await modularAuth.firebaseSignOutClient();

  assert.deepStrictEqual(calls, [
    "phone:+919898000001",
    "email:adv@example.com:secret",
    "reset:adv@example.com",
    "verify:oob-1",
    "confirmReset:oob-1:NewPass123",
    "signOut",
  ]);
  console.log("PASS 1: RNFB v26 modular Android Phone OTP, Email, Reset, SignOut verified.");

  // 2. Expo Go fallback when TurboModule is unlinked (getAuth throws)
  const expoGoFallback = loadUseFirebaseAuth({
    platformOs: "android",
    nativeMod: {
      getAuth: () => {
        throw new Error("Native module RNFBAuthModule is not registered.");
      },
    },
  });
  assert.strictEqual(expoGoFallback.isFirebaseConfigured(), false, "Expo Go without native RNFB must degrade safely to false");
  assert.strictEqual(await expoGoFallback.firebaseSendPhoneOtp("9898000001", null), null);
  console.log("PASS 2: Unlinked native module fallback verified.");
}

if (typeof require !== "undefined" && require.main === module) {
  runFirebaseNativeAuthTests().catch((e) => {
    console.error(e);
    process.exit(1);
  });
}

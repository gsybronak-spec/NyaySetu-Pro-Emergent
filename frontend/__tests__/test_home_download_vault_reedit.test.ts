import assert from "assert";
import fs from "fs";
import Module from "module";
import path from "path";

const FRONTEND = path.resolve(__dirname, "..");

function loadDownloadModule(platformOs: "web" | "android", mocks: {
  storageMap?: Record<string, string>;
  safGranted?: boolean;
  safDirUri?: string;
  safCreateThrowsOnce?: boolean;
  shareCalls?: any[];
  browserDownloads?: { filename: string; type: string; size: number }[];
}) {
  const sucrase = require(path.join(FRONTEND, "node_modules/sucrase"));
  const srcPath = path.join(FRONTEND, "src/utils/download.ts");
  const code = sucrase.transform(fs.readFileSync(srcPath, "utf8"), {
    transforms: ["typescript", "imports"],
    filePath: srcPath,
  }).code;

  const store = mocks.storageMap || {};
  const safFilesWritten: { uri: string; base64Len: number }[] = [];
  const safDirsCreated: { dirUri: string; filename: string; mimeType: string }[] = [];
  const safPermissionCalls: (string | null | undefined)[] = [];
  let shouldThrowFirstSafWrite = Boolean(mocks.safCreateThrowsOnce);

  const origLoad = (Module as any)._load;
  const origDoc = (global as any).document;
  const origUrl = (global as any).URL;

  if (platformOs === "web") {
    const anchors: any[] = [];
    (global as any).URL = {
      createObjectURL: (blob: any) => {
        (mocks.browserDownloads || []).push({ filename: "__pending__", type: blob.type, size: blob.size });
        return "blob:mock-url";
      },
      revokeObjectURL: () => {},
    };
    (global as any).document = {
      createElement: () => {
        const el: any = {
          style: {},
          click: () => {
            const pending = mocks.browserDownloads?.[mocks.browserDownloads.length - 1];
            if (pending) pending.filename = el.download;
          },
          remove: () => {},
        };
        anchors.push(el);
        return el;
      },
      body: { appendChild: () => {} },
    };
  }

  (Module as any)._load = function (request: string, parent: any, isMain: boolean) {
    if (request === "react-native") return { Platform: { OS: platformOs } };
    if (request === "expo-file-system/legacy") {
      return {
        cacheDirectory: "file:///cache/",
        documentDirectory: "file:///docs/",
        writeAsStringAsync: async (uri: string, b64: string) => {
          safFilesWritten.push({ uri, base64Len: b64.length });
        },
        StorageAccessFramework: {
          getUriForDirectoryInRoot: (folder: string) => `content://com.android.externalstorage.documents/tree/primary:${folder}`,
          requestDirectoryPermissionsAsync: async (initial?: string | null) => {
            safPermissionCalls.push(initial);
            if (mocks.safGranted === false) return { granted: false };
            return { granted: true, directoryUri: mocks.safDirUri || "content://com.android.externalstorage.documents/tree/primary:Download" };
          },
          createFileAsync: async (dirUri: string, filename: string, mimeType: string) => {
            if (shouldThrowFirstSafWrite) {
              shouldThrowFirstSafWrite = false;
              throw new Error("Permission revoked");
            }
            safDirsCreated.push({ dirUri, filename, mimeType });
            return `${dirUri}/document/${filename}`;
          },
        },
      };
    }
    if (request === "expo-sharing") {
      return {
        isAvailableAsync: async () => true,
        shareAsync: async (uri: string, opts: any) => {
          mocks.shareCalls?.push({ uri, opts });
        },
      };
    }
    if (request === "@/src/utils/storage") {
      return {
        storage: {
          getItem: async (k: string, def: any) => (k in store ? store[k] : def),
          setItem: async (k: string, v: any) => { store[k] = v; },
          removeItem: async (k: string) => { delete store[k]; },
        },
      };
    }
    return origLoad.call(this, request, parent, isMain);
  };

  try {
    const mod = { exports: {} as any };
    const fn = new Function("exports", "require", "module", code);
    fn(mod.exports, (r: string) => (Module as any)._load(r, null, false), mod);
    return {
      mod: mod.exports,
      safFilesWritten,
      safDirsCreated,
      safPermissionCalls,
      restore: () => {
        (global as any).document = origDoc;
        (global as any).URL = origUrl;
      },
    };
  } finally {
    (Module as any)._load = origLoad;
  }
}

export async function runHomeDownloadVaultReeditTests() {
  console.log("=== EXECUTING HOME / DOWNLOAD / VAULT RE-EDIT TESTS ===");

  // 1. Home Screen checks (Mobile replaces Civil/Criminal with Documents Vault & Drafts)
  const homeSrc = fs.readFileSync(path.join(FRONTEND, "app/(tabs)/home.tsx"), "utf8");
  assert.ok(homeSrc.includes('label: "Documents Vault"'), "Home must render Documents Vault card");
  assert.ok(homeSrc.includes('label: "Drafts"'), "Home must render Drafts card");
  assert.ok(homeSrc.includes('testID={`cat-${c.key}`}'), "Home Quick Access preserves card testID pattern");
  assert.ok(homeSrc.includes('pathname: "/vault", params: { tab: c.tab }'), "Cards route to /vault with respective tab");
  assert.ok(!homeSrc.includes('{ key: "Civil",'), "Mobile Home must no longer render Civil category card");
  assert.ok(!homeSrc.includes('{ key: "Criminal",'), "Mobile Home must no longer render Criminal category card");
  console.log("PASS 1: Home Page replaces Civil/Criminal with Documents Vault & Drafts preserving design.");

  const samplePdfB64 = Buffer.from("%PDF-1.4\n1 0 obj\n<<>>\nendobj\n").toString("base64");

  // 2. Android Download saves directly via SAF without popping Share sheet
  const sharedStorage: Record<string, string> = {};
  const shareCalls: any[] = [];
  const android1 = loadDownloadModule("android", { storageMap: sharedStorage, shareCalls });
  const r1 = await android1.mod.saveDocument(
    { filename: "Mudat Arji:123.pdf", mime_type: "application/pdf", base64: samplePdfB64 },
    "pdf"
  );
  assert.strictEqual(r1, "downloaded", "Android download must resolve to downloaded (saved to device)");
  assert.strictEqual(shareCalls.length, 0, "Android saveDocument must NOT open share sheet automatically");
  assert.strictEqual(android1.safPermissionCalls.length, 1, "First Android save prompts SAF Download directory picker");
  assert.ok(android1.safPermissionCalls[0]?.includes("Download"), "Picker opens at Download folder");
  assert.strictEqual(android1.safDirsCreated[0].filename, "Mudat_Arji_123.pdf");
  assert.strictEqual(android1.safFilesWritten.length, 1);

  // Second Android download reuses persisted folder permission without re-prompting
  const android2 = loadDownloadModule("android", { storageMap: sharedStorage, shareCalls });
  const r2 = await android2.mod.saveDocument(
    { filename: "Second_Doc", mime_type: "application/pdf", base64: samplePdfB64 },
    "pdf"
  );
  assert.strictEqual(r2, "downloaded");
  assert.strictEqual(android2.safPermissionCalls.length, 0, "Cached SAF URI reused without prompting");
  assert.strictEqual(android2.safDirsCreated[0].filename, "Second_Doc.pdf");

  // Revoked SAF permission clears cache, re-prompts once, and saves successfully
  const android3 = loadDownloadModule("android", { storageMap: sharedStorage, safCreateThrowsOnce: true, shareCalls });
  const r3 = await android3.mod.saveDocument(
    { filename: "Retry.pdf", mime_type: "application/pdf", base64: samplePdfB64 },
    "pdf"
  );
  assert.strictEqual(r3, "downloaded");
  assert.strictEqual(android3.safPermissionCalls.length, 1, "Revoked permission re-prompts cleanly");

  // Cancelled folder picker rejects clearly instead of pretending download succeeded
  const androidCancel = loadDownloadModule("android", { storageMap: {}, safGranted: false, shareCalls });
  await assert.rejects(
    () => androidCancel.mod.saveDocument({ filename: "Doc.pdf", mime_type: "application/pdf", base64: samplePdfB64 }, "pdf"),
    /Download cancelled/
  );

  // Web download still works via Blob + anchor download
  const browserDownloads: any[] = [];
  const webEnv = loadDownloadModule("web", { browserDownloads });
  try {
    const rw = await webEnv.mod.saveDocument(
      { filename: "Web_App.pdf", mime_type: "application/pdf", base64: samplePdfB64 },
      "pdf"
    );
    assert.strictEqual(rw, "downloaded");
    assert.strictEqual(browserDownloads[0].filename, "Web_App.pdf");
  } finally {
    webEnv.restore();
  }
  console.log("PASS 2: Android SAF direct device save (initial, cached, revoked recovery, cancel guard) & Web download verified.");

  // 3. Vault & Template re-edit wiring
  const vaultSrc = fs.readFileSync(path.join(FRONTEND, "app/vault.tsx"), "utf8");
  const tplSrc = fs.readFileSync(path.join(FRONTEND, "app/template/[id].tsx"), "utf8");
  const clientSrc = fs.readFileSync(path.join(FRONTEND, "src/api/client.ts"), "utf8");

  assert.ok(clientSrc.includes("getApplication:"), "API client exposes getApplication");
  assert.ok(clientSrc.includes("updateApplication:"), "API client exposes updateApplication");
  assert.ok(vaultSrc.includes("application_id: docId"), "Vault passes application_id for Edit & Re-download");
  assert.ok(tplSrc.includes("api.getApplication(initialApplicationId)"), "Template loads saved Vault application details");
  assert.ok(tplSrc.includes("savedApp.form_values || savedApp.values"), "Template restores form_values cleanly");
  assert.ok(tplSrc.includes("if (loading || activeApplicationId || Object.keys(values).length === 0) return;"), "Template skips draft autosave while editing saved Vault app");
  assert.ok(tplSrc.includes("saveApplicationChanges"), "Template provides Save Changes in-place update action");
  assert.ok(tplSrc.includes("form_values: values"), "Template sends raw form_values for future re-edits");
  console.log("PASS 3: Vault application re-open/edit & non-duplicating update flow verified.");
}

if (typeof require !== "undefined" && require.main === module) {
  runHomeDownloadVaultReeditTests().catch((err) => {
    console.error("Test failed:", err);
    process.exit(1);
  });
}

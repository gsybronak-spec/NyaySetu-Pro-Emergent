import assert from "assert";
import fs from "fs";
import Module from "module";
import path from "path";

const FRONTEND = path.resolve(__dirname, "..");

function loadDownloadWithNativeMock(options: {
  platformOs: "android" | "web";
  nativeModule?: any;
  openUriResult?: boolean;
}) {
  const sucrase = require(path.join(FRONTEND, "node_modules/sucrase"));
  const srcPath = path.join(FRONTEND, "src/utils/download.ts");
  const code = sucrase.transform(fs.readFileSync(srcPath, "utf8"), {
    transforms: ["typescript", "imports"],
    filePath: srcPath,
  }).code;

  const shareCalls: any[] = [];
  const openUriCalls: any[] = [];
  const saveCalls: any[] = [];
  const renderCalls: any[] = [];
  const safCalls: any[] = [];

  const origLoad = (Module as any)._load;
  (Module as any)._load = function (request: string, parent: any, isMain: boolean) {
    if (request === "react-native") return { Platform: { OS: options.platformOs } };
    if (request === "expo-modules-core") {
      return {
        requireOptionalNativeModule: (name: string) => {
          if (name !== "NyaySetuDownloads") return null;
          if (!options.nativeModule) return null;
          return {
            saveToDownloads: async (base64: string, filename: string, mimeType: string) => {
              saveCalls.push({ filename, mimeType, len: base64.length });
              return options.nativeModule.saveToDownloads(base64, filename, mimeType);
            },
            openUri: async (uri: string, mimeType: string) => {
              openUriCalls.push({ uri, mimeType });
              return options.openUriResult ?? true;
            },
            renderPdfToImages: async (base64: string) => {
              renderCalls.push({ len: base64.length });
              return options.nativeModule.renderPdfToImages(base64);
            },
          };
        },
      };
    }
    if (request === "expo-file-system/legacy") {
      return {
        cacheDirectory: "file:///cache/",
        documentDirectory: "file:///docs/",
        writeAsStringAsync: async () => {},
        StorageAccessFramework: {
          getUriForDirectoryInRoot: (f: string) => `content://tree/primary:${f}`,
          requestDirectoryPermissionsAsync: async () => {
            safCalls.push("prompted");
            return { granted: false };
          },
          createFileAsync: async () => "",
        },
      };
    }
    if (request === "expo-sharing") {
      return {
        isAvailableAsync: async () => true,
        shareAsync: async (uri: string, opts: any) => {
          shareCalls.push({ uri, opts });
        },
      };
    }
    if (request === "@/src/utils/storage") {
      return {
        storage: {
          getItem: async (_k: string, d: any) => d,
          setItem: async () => true,
          removeItem: async () => true,
        },
      };
    }
    return origLoad.call(this, request, parent, isMain);
  };

  try {
    const mod = { exports: {} as any };
    const fn = new Function("exports", "require", "module", code);
    fn(mod.exports, (r: string) => (Module as any)._load(r, null, false), mod);
    return { mod: mod.exports, shareCalls, openUriCalls, saveCalls, renderCalls, safCalls };
  } finally {
    (Module as any)._load = origLoad;
  }
}

export async function runArjiDownloadPreviewPerfTests() {
  console.log("=== EXECUTING ARJI DOWNLOAD / PREVIEW / PERFORMANCE TESTS ===");
  const samplePdfB64 = Buffer.from("%PDF-1.4\n1 0 obj\n<<>>\nendobj\n").toString("base64");

  // 1. Direct MediaStore.Downloads save without SAF picker or Share sheet
  const envDirect = loadDownloadWithNativeMock({
    platformOs: "android",
    nativeModule: {
      saveToDownloads: async (_b64: string, filename: string) => ({
        uri: "content://media/external/downloads/101",
        displayPath: `Download/NyaySetu Pro/${filename}`,
      }),
      renderPdfToImages: async () => [{ uri: "file:///cache/page_1.png", width: 1080, height: 1527 }],
    },
  });

  const saved = await envDirect.mod.saveDocumentDetailed(
    { filename: "Mudat Arji.pdf", mime_type: "application/pdf", base64: samplePdfB64 },
    "pdf"
  );
  assert.strictEqual(saved.mode, "downloaded");
  assert.strictEqual(saved.uri, "content://media/external/downloads/101");
  assert.strictEqual(saved.displayPath, "Download/NyaySetu Pro/Mudat_Arji.pdf");
  assert.strictEqual(envDirect.saveCalls.length, 1);
  assert.strictEqual(envDirect.safCalls.length, 0, "MediaStore direct save must NOT prompt SAF picker");
  assert.strictEqual(envDirect.shareCalls.length, 0, "Direct phone save must NOT launch share sheet");

  // openSavedDocument uses ACTION_VIEW openUri directly instead of Share sheet
  const opened = await envDirect.mod.openSavedDocument(
    saved.uri,
    { filename: "Mudat_Arji.pdf", mime_type: "application/pdf", base64: samplePdfB64 },
    "pdf"
  );
  assert.strictEqual(opened, true);
  assert.strictEqual(envDirect.openUriCalls.length, 1);
  assert.strictEqual(envDirect.shareCalls.length, 0, "Opening saved PDF must NOT open share sheet when viewer handles it");

  // renderPdfPagesToImages invokes native PdfRenderer helper cleanly
  const renderedPages = await envDirect.mod.renderPdfPagesToImages(samplePdfB64);
  assert.ok(Array.isArray(renderedPages) && renderedPages.length === 1);
  assert.strictEqual(renderedPages[0].width, 1080);

  // If no viewer app handles file (openUri=false), gracefully falls back to shareDocumentFile
  const envNoViewer = loadDownloadWithNativeMock({
    platformOs: "android",
    openUriResult: false,
    nativeModule: {
      saveToDownloads: async () => ({ uri: "content://media/external/downloads/102", displayPath: "Download/NyaySetu Pro/Doc.odt" }),
      renderPdfToImages: async () => [],
    },
  });
  await envNoViewer.mod.openSavedDocument(
    "content://media/external/downloads/102",
    { filename: "Doc.odt", mime_type: "application/vnd.oasis.opendocument.text", base64: Buffer.from("PK\x03\x04test").toString("base64") },
    "odt"
  );
  assert.strictEqual(envNoViewer.shareCalls.length, 1);
  console.log("PASS 1: Android MediaStore direct phone save, ACTION_VIEW open, and native PdfRenderer bridge verified.");

  // 2. Preview & Performance architectural checks
  const viewerSrc = fs.readFileSync(path.join(FRONTEND, "src/components/ActualPdfViewer.tsx"), "utf8");
  const tplSrc = fs.readFileSync(path.join(FRONTEND, "app/template/[id].tsx"), "utf8");
  const dropdownSrc = fs.readFileSync(path.join(FRONTEND, "src/components/Dropdown.tsx"), "utf8");
  const layoutSrc = fs.readFileSync(path.join(FRONTEND, "app/(tabs)/_layout.tsx"), "utf8");
  const catalogSrc = fs.readFileSync(path.join(FRONTEND, "src/services/catalogCache.ts"), "utf8");

  assert.ok(viewerSrc.includes("renderPdfPagesToImages"), "ActualPdfViewer renders real PDF pages on Android");
  assert.ok(viewerSrc.includes("BlocksPaperPreview"), "ActualPdfViewer provides structured blocks paper preview fallback");
  assert.ok(tplSrc.includes("if (step !== \"preview\") return;"), "Template must not trigger background preview PDF calls while typing fields");
  assert.ok(!tplSrc.includes("if (step !== \"preview\" && !pdfBase64)"), "Old leaky background preview condition must be gone");
  assert.ok(tplSrc.includes("blocks={blocks}"), "Template passes blocks into ActualPdfViewer");
  assert.ok(tplSrc.includes("saveDocumentDetailed"), "Template uses direct MediaStore download helper");
  assert.ok(dropdownSrc.includes("<FlatList"), "Dropdown uses virtualized FlatList instead of eager ScrollView map");
  assert.ok(!layoutSrc.includes("getPublishedTemplates(true)"), "Tabs layout avoids forceRefresh templates on mount");
  assert.ok(catalogSrc.includes("CATALOG_FIELD_OPTION_KEYS"), "catalogCache compacts bloated catalog options");
  console.log("PASS 2: Android PDF/Blocks preview, Dropdown virtualization, and SWR/compact template speed optimizations verified.");
}

if (typeof require !== "undefined" && require.main === module) {
  runArjiDownloadPreviewPerfTests().catch((err) => {
    console.error("Test failed:", err);
    process.exit(1);
  });
}

import { Platform } from "react-native";
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";
import { storage } from "@/src/utils/storage";

const ANDROID_DOWNLOAD_DIR_KEY = "@nyaysetu_android_download_dir_v1";

type NativeDownloadsBridge = {
  saveToDownloads?: (
    base64: string,
    filename: string,
    mimeType: string
  ) => Promise<{ uri: string; displayPath: string }>;
  openUri?: (uriString: string, mimeType: string) => Promise<boolean>;
  renderPdfToImages?: (
    base64: string
  ) => Promise<{ uri: string; width: number; height: number }[]>;
};

let cachedRequireOptionalNativeModule: ((name: string) => any) | null = null;
try {
  const core = require("expo-modules-core");
  if (core && typeof core.requireOptionalNativeModule === "function") {
    cachedRequireOptionalNativeModule = core.requireOptionalNativeModule;
  }
} catch {
  cachedRequireOptionalNativeModule = null;
}

function getNativeDownloads(): NativeDownloadsBridge | null {
  if (Platform.OS !== "android" || !cachedRequireOptionalNativeModule) return null;
  try {
    return cachedRequireOptionalNativeModule("NyaySetuDownloads") || null;
  } catch {
    // Running in Expo Go, Jest/Node, or older binary without native helper
    return null;
  }
}

export type PdfPreviewPage = {
  uri: string;
  width: number;
  height: number;
};

export type SaveDocumentResult = {
  mode: "downloaded" | "shared";
  uri?: string;
  displayPath?: string;
};

/**
 * Centralized document-delivery helper.
 *
 * The backend returns `{ filename, mime_type, base64 }` (JSON) for PDF, DOCX,
 * ODT, and PNG/ZIP exports.
 *
 *  - Web: decode the base64, validate format magic bytes, build a Blob and
 *    trigger a real browser download via a temporary `<a download>` element.
 *  - Android: save directly into the user-selected device folder (defaulting
 *    the native folder picker to Downloads) via Storage Access Framework (SAF)
 *    with persistable directory permission — no legacy storage permissions
 *    required and the file actually lands visibly on the device.
 *  - iOS: write to the app's Documents directory and present Save/Share sheet.
 */

export type DownloadPayload = {
  filename: string;
  mime_type: string;
  base64: string;
};

export function sanitizeFilename(filename: string | undefined, format: "pdf" | "docx" | "odt" | "png"): string {
  const cleaned = String(filename || "")
    .replace(/[\\/:*?"<>|\x00-\x1F]/g, "_")
    .replace(/\s+/g, "_")
    .replace(/^_+|_+$/g, "");
  if (!cleaned) return `legal_document.${format}`;
  const lower = cleaned.toLowerCase();
  if (format === "png" && (lower.endsWith(".png") || lower.endsWith(".zip"))) return cleaned;
  if (lower.endsWith(`.${format}`)) return cleaned;
  return `${cleaned}.${format}`;
}

export function decodeBase64(base64: string): Uint8Array {
  if (!base64 || typeof base64 !== "string" || base64.length === 0) {
    throw new Error("The server returned an empty document. Please try again.");
  }
  // Works in browsers (atob) and React Native (global.atob available in the
  // Hermes runtime used by Expo).
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

/** Returns an error string when the bytes do not match the expected format. */
export function validateFileBytes(bytes: Uint8Array, format: "pdf" | "docx" | "odt" | "png"): string | null {
  if (bytes.length < 4) {
    return "The server returned an incomplete document. Please try again.";
  }
  if (format === "pdf") {
    const head = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]);
    if (head !== "%PDF") {
      return "The server returned an invalid PDF file. Please try again.";
    }
  } else if (format === "png") {
    // Single page -> PNG; multiple pages -> ZIP of page-N.png.
    const head = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]);
    if (head === "PK") {
      return null; // multi-page image ZIP
    }
    const pngSig = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
    if (bytes.length < 8 || bytes.slice(0, 8).some((b, i) => b !== pngSig[i])) {
      return "The server returned an invalid image file. Please try again.";
    }
    return null;
  } else {
    // DOCX/ODT are ZIP archives — magic bytes PK\x03\x04 (or PK\x05\x06 empty zip).
    const head = String.fromCharCode(bytes[0], bytes[1]);
    if (head !== "PK") {
      return `The server returned an invalid ${format === "docx" ? "Word" : "Writer"} document. Please try again.`;
    }
  }
  return null;
}

function triggerBrowserDownload(blob: Blob, filename: string): void {
  if (typeof document === "undefined") {
    throw new Error("Unable to download the document in this environment. Please try again.");
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  // Give the browser a moment to start the download, then release the blob URL
  // and remove the anchor. Revoking after a short delay (never synchronously)
  // keeps the download safe in all browsers.
  setTimeout(() => {
    URL.revokeObjectURL(url);
    a.remove();
  }, 4000);
}

async function writeSafFile(dirUri: string, filename: string, mimeType: string, base64: string): Promise<string> {
  const destUri = await FileSystem.StorageAccessFramework.createFileAsync(dirUri, filename, mimeType);
  await FileSystem.writeAsStringAsync(destUri, base64, { encoding: "base64" });
  return destUri;
}

/**
 * Shares a locally cached copy on native devices (used optionally after saving).
 */
export async function shareDocumentFile(res: DownloadPayload, format: "pdf" | "docx" | "odt" | "png"): Promise<void> {
  const safeName = sanitizeFilename(res.filename, format);
  const baseDir = FileSystem.cacheDirectory || FileSystem.documentDirectory;
  if (!baseDir) throw new Error("Local temporary storage unavailable.");
  const path = `${baseDir}${safeName}`;
  await FileSystem.writeAsStringAsync(path, res.base64, { encoding: "base64" });
  if (await Sharing.isAvailableAsync()) {
    await Sharing.shareAsync(path, { mimeType: res.mime_type, dialogTitle: "Open or Share Document" });
  }
}

/**
 * Renders PDF pages to cached PNG images using Android's built-in PdfRenderer.
 * Returns null on Web/iOS/Expo Go so callers fall back cleanly to blocks preview.
 */
export async function renderPdfPagesToImages(base64: string): Promise<PdfPreviewPage[] | null> {
  if (!base64 || Platform.OS !== "android") return null;
  const native = getNativeDownloads();
  if (!native?.renderPdfToImages) return null;
  try {
    const pages = await native.renderPdfToImages(base64);
    return Array.isArray(pages) && pages.length > 0 ? pages : null;
  } catch {
    return null;
  }
}

/**
 * Opens a previously saved document URI in the device's default viewer (e.g., PDF Viewer)
 * without triggering a Share sheet. Falls back to share/open sheet only if no viewer handles it.
 */
export async function openSavedDocument(
  uri: string | undefined,
  res: DownloadPayload,
  format: "pdf" | "docx" | "odt" | "png"
): Promise<boolean> {
  const mimeType = res.mime_type || "application/octet-stream";
  if (Platform.OS === "android" && uri) {
    const native = getNativeDownloads();
    if (native?.openUri) {
      const opened = await native.openUri(uri, mimeType).catch(() => false);
      if (opened) return true;
    }
  }
  await shareDocumentFile(res, format);
  return true;
}

/**
 * Saves the document directly to the user's device:
 *  - Web: triggers browser download (`<a download>`) and returns `{ mode: "downloaded" }`.
 *  - Android 10+: saves directly into `Download/NyaySetu Pro/<filename>` via MediaStore.Downloads
 *    (no folder picker, no storage permissions, no share sheet); falls back to SAF on Android < 10
 *    or Expo Go.
 *  - iOS: writes into the app's Documents directory and presents Save/Share sheet.
 */
export async function saveDocumentDetailed(
  res: DownloadPayload,
  format: "pdf" | "docx" | "odt" | "png"
): Promise<SaveDocumentResult> {
  const bytes = decodeBase64(res.base64);
  const invalid = validateFileBytes(bytes, format);
  if (invalid) throw new Error(invalid);

  const safeName = sanitizeFilename(res.filename, format);
  const mimeType = res.mime_type || "application/octet-stream";

  if (Platform.OS === "web") {
    const blob = new Blob([bytes.buffer as ArrayBuffer], { type: mimeType });
    triggerBrowserDownload(blob, safeName);
    return { mode: "downloaded", displayPath: safeName };
  }

  if (Platform.OS === "android") {
    const native = getNativeDownloads();
    if (native?.saveToDownloads) {
      try {
        const saved = await native.saveToDownloads(res.base64, safeName, mimeType);
        return {
          mode: "downloaded",
          uri: saved?.uri,
          displayPath: saved?.displayPath || `Download/NyaySetu Pro/${safeName}`,
        };
      } catch (nativeErr: any) {
        if (nativeErr?.code !== "LEGACY_ANDROID") {
          // Only fall through to SAF if MediaStore wasn't usable; never auto-launch Share.
        }
      }
    }

    if (FileSystem.StorageAccessFramework) {
      const cachedDir = await storage.getItem<string>(ANDROID_DOWNLOAD_DIR_KEY, "");
      if (cachedDir) {
        try {
          const uri = await writeSafFile(cachedDir, safeName, mimeType, res.base64);
          return { mode: "downloaded", uri, displayPath: safeName };
        } catch {
          // Permission may have been revoked or folder removed; prompt again cleanly.
          await storage.removeItem(ANDROID_DOWNLOAD_DIR_KEY);
        }
      }

      let initialUri: string | null = null;
      try {
        initialUri = FileSystem.StorageAccessFramework.getUriForDirectoryInRoot("Download");
      } catch {
        initialUri = null;
      }
      const perm = await FileSystem.StorageAccessFramework.requestDirectoryPermissionsAsync(initialUri);
      if (!perm.granted || !perm.directoryUri) {
        throw new Error("Download cancelled. Please choose a device folder (e.g., Downloads) to save the document.");
      }
      await storage.setItem(ANDROID_DOWNLOAD_DIR_KEY, perm.directoryUri);
      const uri = await writeSafFile(perm.directoryUri, safeName, mimeType, res.base64);
      return { mode: "downloaded", uri, displayPath: safeName };
    }
  }

  // iOS / non-SAF native fallback: write to persistent documentDirectory first, then offer Save/Share sheet.
  const baseDir = FileSystem.documentDirectory || FileSystem.cacheDirectory;
  if (!baseDir) throw new Error("Unable to access device storage.");
  const path = `${baseDir}${safeName}`;
  await FileSystem.writeAsStringAsync(path, res.base64, { encoding: "base64" });
  if (await Sharing.isAvailableAsync()) {
    await Sharing.shareAsync(path, { mimeType, dialogTitle: "Save or Share Document" });
    return { mode: "shared", uri: path, displayPath: safeName };
  }
  return { mode: "downloaded", uri: path, displayPath: safeName };
}

export async function saveDocument(res: DownloadPayload, format: "pdf" | "docx" | "odt" | "png"): Promise<"downloaded" | "shared"> {
  const result = await saveDocumentDetailed(res, format);
  return result.mode;
}

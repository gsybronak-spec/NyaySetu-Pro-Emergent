import { Platform } from "react-native";
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";

/**
 * Centralized document-delivery helper.
 *
 * The backend returns `{ filename, mime_type, base64 }` (JSON) for both PDF
 * and DOCX. Delivering that to the user is a PLATFORM concern:
 *
 *  - Web: decode the base64, verify the bytes are actually the requested file
 *    type (PDF magic `%PDF`, DOCX zip magic `PK`), build a Blob and trigger a
 *    real browser download via a temporary <a download> element. This is the
 *    ONLY reliable path on desktop browsers — `expo-sharing` is a no-op there
 *    (its web `isAvailableAsync` returns `navigator.share ? true : false`,
 *    which is false on Chrome/Edge desktop), and `expo-file-system` writes to
 *    an in-memory virtual FS on web, never to a real file.
 *
 *  - Native: write the base64 to the cache directory and open the share sheet
 *    (real file on disk, shareable).
 *
 * The function NEVER resolves with a success that did not happen: it throws a
 * user-readable Error if the response is empty, not decodable, or not the
 * expected file type.
 */

export type DownloadPayload = {
  filename: string;
  mime_type: string;
  base64: string;
};

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

/**
 * Saves/generates the document for the user.
 * Returns "downloaded" (web download or native cache save) or "shared"
 * (native share sheet used). Throws a user-readable Error on any failure —
 * it never silently drops the file.
 */
export async function saveDocument(res: DownloadPayload, format: "pdf" | "docx" | "odt" | "png"): Promise<"downloaded" | "shared"> {
  const bytes = decodeBase64(res.base64);
  const invalid = validateFileBytes(bytes, format);
  if (invalid) throw new Error(invalid);

  if (Platform.OS === "web") {
    // decodeBase64 allocates an exact-size buffer, so the view IS the whole
    // buffer — safe to hand to Blob as an ArrayBuffer.
    const blob = new Blob([bytes.buffer as ArrayBuffer], { type: res.mime_type });
    triggerBrowserDownload(blob, res.filename);
    return "downloaded";
  }

  // Native: real file in the cache directory, then open the share sheet.
  const path = `${FileSystem.cacheDirectory}${res.filename}`;
  await FileSystem.writeAsStringAsync(path, res.base64, { encoding: "base64" });
  const canShare = await Sharing.isAvailableAsync();
  if (canShare) {
    await Sharing.shareAsync(path, { mimeType: res.mime_type, dialogTitle: "Save or Share Document" });
    return "shared";
  }
  // No share sheet (rare) — the file is still safely on disk in the cache.
  return "downloaded";
}

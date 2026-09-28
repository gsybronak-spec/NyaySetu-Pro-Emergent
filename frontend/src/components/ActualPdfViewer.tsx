import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  ActivityIndicator,
  StyleSheet,
  Platform,
} from "react-native";

interface ActualPdfViewerProps {
  base64: string;
  loading?: boolean;
  testID?: string;
}

// Global script loading state to prevent redundant script injection
let pdfjsPromise: Promise<any> | null = null;

function getPdfJs(): Promise<any> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("window is not available"));
  }

  const existing = (window as any).pdfjsLib;
  if (existing) {
    return Promise.resolve(existing);
  }

  if (pdfjsPromise) {
    return pdfjsPromise;
  }

  pdfjsPromise = new Promise((resolve, reject) => {
    // 1. Try local vendored pdf.min.js
    const script = document.createElement("script");
    script.src = "/vendor/pdfjs/pdf.min.js";
    script.async = true;

    script.onload = () => {
      const lib = (window as any).pdfjsLib;
      if (lib) {
        try {
          lib.GlobalWorkerOptions.workerSrc = "/vendor/pdfjs/pdf.worker.min.js";
        } catch (_) {}
        resolve(lib);
      } else {
        fallbackCdn().then(resolve).catch(reject);
      }
    };

    script.onerror = () => {
      fallbackCdn().then(resolve).catch(reject);
    };

    document.head.appendChild(script);

    function fallbackCdn(): Promise<any> {
      return new Promise((res, rej) => {
        const cdnScript = document.createElement("script");
        cdnScript.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
        cdnScript.async = true;
        cdnScript.onload = () => {
          const cdnLib = (window as any).pdfjsLib;
          if (cdnLib) {
            try {
              cdnLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
            } catch (_) {}
            res(cdnLib);
          } else {
            rej(new Error("Failed to load PDF.js from CDN"));
          }
        };
        cdnScript.onerror = () => rej(new Error("Failed to load PDF.js"));
        document.head.appendChild(cdnScript);
      });
    }
  });

  return pdfjsPromise;
}

export const ActualPdfViewer: React.FC<ActualPdfViewerProps> = ({
  base64,
  loading = false,
  testID,
}) => {
  const containerRef = useRef<any>(null);
  const [rendering, setRendering] = useState<boolean>(true);
  const [numPages, setNumPages] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [fallbackBlobUrl, setFallbackBlobUrl] = useState<string | null>(null);
  const currentRenderTaskRef = useRef<number>(0);

  useEffect(() => {
    if (!base64 || Platform.OS !== "web") {
      setRendering(false);
      return;
    }

    const taskId = ++currentRenderTaskRef.current;
    setRendering(true);
    setError(null);

    try {
      const raw = atob(base64);
      const uint8 = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) uint8[i] = raw.charCodeAt(i);
      const blob = new Blob([uint8.buffer], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      setFallbackBlobUrl(url);

      getPdfJs()
        .then(async (pdfjs) => {
          if (taskId !== currentRenderTaskRef.current) return;

          const doc = await pdfjs.getDocument({ data: uint8 }).promise;
          if (taskId !== currentRenderTaskRef.current) return;

          setNumPages(doc.numPages);

          const container = containerRef.current;
          if (!container) return;

          while (container.firstChild) {
            container.removeChild(container.firstChild);
          }

          const containerWidth = container.clientWidth || 780;
          const targetWidth = Math.min(Math.max(containerWidth, 320), 780);
          const dpr = Math.min(window.devicePixelRatio || 1, 2.5);

          for (let pageNum = 1; pageNum <= doc.numPages; pageNum++) {
            if (taskId !== currentRenderTaskRef.current) return;

            const page = await doc.getPage(pageNum);
            const unscaledViewport = page.getViewport({ scale: 1.0 });
            const scale = targetWidth / unscaledViewport.width;
            const viewport = page.getViewport({ scale });

            const pageCard = document.createElement("div");
            pageCard.className = "actual-pdf-page-card";
            pageCard.style.cssText = [
              "background: #FFFFFF;",
              "box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08), 0 1px 4px rgba(0, 0, 0, 0.04);",
              "border: 1px solid #E5E7EB;",
              "border-radius: 6px;",
              "margin-bottom: 24px;",
              "width: 100%;",
              "max-width: 780px;",
              "position: relative;",
              "overflow: hidden;",
              "box-sizing: border-box;",
            ].join(" ");

            const canvas = document.createElement("canvas");
            canvas.style.cssText = [
              "display: block;",
              "width: 100%;",
              "height: auto;",
            ].join(" ");

            canvas.width = Math.floor(viewport.width * dpr);
            canvas.height = Math.floor(viewport.height * dpr);

            const ctx = canvas.getContext("2d");
            if (ctx) {
              ctx.scale(dpr, dpr);
              await page.render({
                canvasContext: ctx,
                viewport,
              }).promise;
            }

            pageCard.appendChild(canvas);

            if (doc.numPages > 1) {
              const badge = document.createElement("div");
              badge.style.cssText = [
                "position: absolute;",
                "bottom: 10px;",
                "right: 14px;",
                "background: rgba(15, 23, 42, 0.7);",
                "color: #FFFFFF;",
                "padding: 3px 10px;",
                "border-radius: 12px;",
                "font-size: 11px;",
                "font-weight: 600;",
                "letter-spacing: 0.5px;",
                "pointer-events: none;",
              ].join(" ");
              badge.textContent = `${pageNum} / ${doc.numPages}`;
              pageCard.appendChild(badge);
            }

            container.appendChild(pageCard);
          }

          if (taskId === currentRenderTaskRef.current) {
            setRendering(false);
          }
        })
        .catch((err) => {
          if (taskId === currentRenderTaskRef.current) {
            console.warn("PDF.js render fallback to embedded viewer:", err);
            setError(err?.message || "PDF render error");
            setRendering(false);
          }
        });

      return () => {
        URL.revokeObjectURL(url);
      };
    } catch (e: any) {
      setError(e?.message || "Failed to decode PDF");
      setRendering(false);
    }
  }, [base64]);

  return (
    <View testID={testID || "actual-pdf-viewer"} style={styles.container}>
      {(loading || rendering) && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#1A365D" />
          <Text style={styles.loadingText}>
            PDF પ્રીવ્યૂ તૈયાર થાય છે…
          </Text>
          <Text style={styles.subLoadingText}>
            Generating actual production PDF preview…
          </Text>
        </View>
      )}

      {Platform.OS === "web" && (
        <div
          ref={containerRef}
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            width: "100%",
            maxWidth: "780px",
            margin: "0 auto",
            opacity: loading || rendering ? 0.4 : 1,
            transition: "opacity 0.2s ease-in-out",
          }}
        />
      )}

      {Platform.OS === "web" && error && fallbackBlobUrl && (
        <div style={{ width: "100%", maxWidth: "780px", height: "800px", margin: "0 auto" }}>
          <object
            data={fallbackBlobUrl}
            type="application/pdf"
            width="100%"
            height="100%"
            style={{ border: "1px solid #E5E7EB", borderRadius: "6px" }}
          >
            <p>PDF preview not supported in this browser.</p>
          </object>
        </div>
      )}

      {Platform.OS !== "web" && (
        <View style={styles.nativeFallback}>
          <Text style={styles.loadingText}>
            PDF દસ્તાવેજ તૈયાર છે.
          </Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: "100%",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
  },
  loadingOverlay: {
    paddingVertical: 32,
    alignItems: "center",
    justifyContent: "center",
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    fontWeight: "700",
    color: "#1A365D",
  },
  subLoadingText: {
    marginTop: 4,
    fontSize: 12,
    color: "#64748B",
  },
  nativeFallback: {
    padding: 24,
    alignItems: "center",
  },
});

export default ActualPdfViewer;

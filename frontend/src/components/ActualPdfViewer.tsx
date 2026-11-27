import React, { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Platform,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { PdfPreviewPage, renderPdfPagesToImages } from "@/src/utils/download";
import { Radius, Spacing } from "@/src/theme/tokens";

interface ActualPdfViewerProps {
  base64: string;
  blocks?: any[];
  loading?: boolean;
  language?: "gu" | "en";
  isDesktop?: boolean;
  borderColor?: string;
  testID?: string;
}

// Global script loading state to prevent redundant script injection on Web
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
              cdnLib.GlobalWorkerOptions.workerSrc =
                "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
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

export const BlocksPaperPreview: React.FC<{
  blocks: any[];
  isDesktop?: boolean;
  borderColor?: string;
}> = ({ blocks, isDesktop = false, borderColor = "#E5E7EB" }) => {
  if (!Array.isArray(blocks) || blocks.length === 0) {
    return null;
  }

  return (
    <View style={[styles.doc, isDesktop && styles.docDesktop, { backgroundColor: "#FFFFFF", borderColor }]}>
      {blocks.map((b, i) => {
        if (b.section === "table" && Array.isArray(b.rows) && b.rows.length > 0) {
          const metaCols = b.meta?.cols || [];
          const totalColWidth = metaCols.reduce((acc: number, val: number) => acc + val, 0) || 100;
          const defaultAligns = b.meta?.align || [];

          return (
            <View key={i} testID={`preview-table-${i}`} style={[styles.previewTable, { borderColor: "#000000" }]}>
              {b.rows.map((row: string[], rIdx: number) => {
                const rMeta = b.row_meta?.[rIdx] || {};
                const isHeader = !!rMeta.is_header;
                const isSpan = row.length === 1 && metaCols.length > 1;

                return (
                  <View
                    key={rIdx}
                    style={[styles.previewTableRow, isHeader && { backgroundColor: "#F3F4F6" }]}
                  >
                    {row.map((cellText: string, cIdx: number) => {
                      const cellAlign = (rMeta.align?.[cIdx] ||
                        (isHeader ? "center" : defaultAligns[cIdx]) ||
                        (isSpan ? defaultAligns[0] || "right" : "left")) as "left" | "right" | "center";
                      const cellBold = isHeader || !!rMeta.bold?.[cIdx];

                      let colWidthPercent = "100%";
                      if (!isSpan && metaCols.length > cIdx) {
                        colWidthPercent = `${(metaCols[cIdx] / totalColWidth) * 100}%`;
                      } else if (!isSpan && metaCols.length === 0 && row.length > 0) {
                        colWidthPercent = `${100 / row.length}%`;
                      }

                      return (
                        <View
                          key={cIdx}
                          testID={`preview-table-cell-${rIdx}-${cIdx}`}
                          style={[
                            styles.previewTableCell,
                            {
                              width: colWidthPercent as any,
                              borderColor: "#000000",
                              alignItems:
                                cellAlign === "right"
                                  ? "flex-end"
                                  : cellAlign === "center"
                                  ? "center"
                                  : "flex-start",
                              justifyContent: "center",
                            },
                          ]}
                        >
                          <Text
                            selectable
                            style={[
                              styles.docText,
                              {
                                textAlign: cellAlign,
                                fontWeight: cellBold ? "700" : "400",
                                fontSize: 13,
                                color: "#111111",
                                lineHeight: 20,
                              },
                            ]}
                          >
                            {cellText || " "}
                          </Text>
                        </View>
                      );
                    })}
                  </View>
                );
              })}
            </View>
          );
        }

        if (b.section === "page_break") {
          return (
            <View
              key={i}
              style={{
                borderBottomWidth: 1,
                borderBottomColor: "#D1D5DB",
                borderStyle: "dashed",
                marginVertical: 14,
              }}
            />
          );
        }

        return (
          <Text
            key={i}
            selectable
            style={[
              styles.docText,
              {
                textAlign: b.align === "center" ? "center" : b.align === "right" ? "right" : "left",
                fontWeight: b.bold ? "700" : "400",
                fontSize: b.bold ? 15 : 13,
                textDecorationLine: b.underline || b.section === "title" ? "underline" : "none",
                marginBottom: b.text ? 6 : 10,
              },
            ]}
          >
            {b.text || " "}
          </Text>
        );
      })}
    </View>
  );
};

export const ActualPdfViewer: React.FC<ActualPdfViewerProps> = ({
  base64,
  blocks = [],
  loading = false,
  language = "gu",
  isDesktop = false,
  borderColor = "#E5E7EB",
  testID,
}) => {
  const containerRef = useRef<any>(null);
  const [rendering, setRendering] = useState<boolean>(true);
  const [numPages, setNumPages] = useState<number>(0);
  const [nativePages, setNativePages] = useState<PdfPreviewPage[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fallbackBlobUrl, setFallbackBlobUrl] = useState<string | null>(null);
  const currentRenderTaskRef = useRef<number>(0);

  // Native (Android/iOS) PDF page rasterization via built-in Android PdfRenderer (with blocks fallback)
  useEffect(() => {
    if (Platform.OS === "web") return;
    if (!base64) {
      setNativePages(null);
      setRendering(false);
      return;
    }

    const taskId = ++currentRenderTaskRef.current;
    setRendering(true);
    setError(null);

    renderPdfPagesToImages(base64)
      .then((pages) => {
        if (taskId !== currentRenderTaskRef.current) return;
        setNativePages(pages);
        setNumPages(pages ? pages.length : 0);
        setRendering(false);
      })
      .catch(() => {
        if (taskId !== currentRenderTaskRef.current) return;
        setNativePages(null);
        setRendering(false);
      });
  }, [base64]);

  // Web PDF.js canvas rendering
  useEffect(() => {
    if (!base64 || Platform.OS !== "web") {
      if (Platform.OS === "web") setRendering(false);
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

  const hasBlocks = Array.isArray(blocks) && blocks.length > 0;

  return (
    <View testID={testID || "actual-pdf-viewer"} style={styles.container}>
      {(loading || (rendering && !nativePages && !hasBlocks)) && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#1A365D" />
          <Text style={styles.loadingText}>
            {language === "gu" ? "PDF પ્રીવ્યૂ તૈયાર થાય છે…" : "Generating PDF preview…"}
          </Text>
          <Text style={styles.subLoadingText}>
            {language === "gu" ? "કૃપા કરીને થોડી ક્ષણ રાહ જુઓ…" : "Rendering formatted legal pages…"}
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

      {Platform.OS !== "web" && nativePages && nativePages.length > 0 && (
        <View style={styles.nativePagesWrap} testID="native-pdf-pages">
          {nativePages.map((pg, idx) => (
            <View key={`${pg.uri}-${idx}`} style={[styles.nativePageCard, { borderColor }]}>
              <Image
                source={{ uri: pg.uri }}
                style={{ width: "100%", aspectRatio: pg.width / Math.max(pg.height, 1) }}
                resizeMode="contain"
              />
              {numPages > 1 && (
                <View style={styles.pageBadge}>
                  <Text style={styles.pageBadgeText}>
                    {idx + 1} / {numPages}
                  </Text>
                </View>
              )}
            </View>
          ))}
        </View>
      )}

      {Platform.OS !== "web" && (!nativePages || nativePages.length === 0) && hasBlocks && (
        <BlocksPaperPreview blocks={blocks} isDesktop={isDesktop} borderColor={borderColor} />
      )}

      {Platform.OS !== "web" && (!nativePages || nativePages.length === 0) && !hasBlocks && !loading && !rendering && (
        <View style={styles.nativeFallback}>
          <Text style={styles.loadingText}>
            {language === "gu" ? "PDF દસ્તાવેજ તૈયાર છે." : "PDF document is ready."}
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
  nativePagesWrap: {
    width: "100%",
    gap: 16,
  },
  nativePageCard: {
    width: "100%",
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    borderWidth: 1,
    overflow: "hidden",
    position: "relative",
    shadowColor: "#000",
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 3 },
    elevation: 3,
  },
  pageBadge: {
    position: "absolute",
    bottom: 10,
    right: 12,
    backgroundColor: "rgba(15, 23, 42, 0.72)",
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 12,
  },
  pageBadgeText: {
    color: "#FFFFFF",
    fontSize: 11,
    fontWeight: "700",
  },
  nativeFallback: {
    padding: 24,
    alignItems: "center",
  },
  doc: {
    width: "100%",
    padding: Spacing.lg,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  docDesktop: {
    maxWidth: 780,
    width: "100%",
    minHeight: 1000,
    padding: Spacing.xxxl,
    borderRadius: 4,
    shadowColor: "#000",
    shadowOpacity: 0.12,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  },
  docText: {
    color: "#111",
    fontSize: 13,
    lineHeight: 22,
  },
  previewTable: {
    borderTopWidth: 1,
    borderLeftWidth: 1,
    marginVertical: 10,
    width: "100%",
  },
  previewTableRow: {
    flexDirection: "row",
    width: "100%",
  },
  previewTableCell: {
    borderRightWidth: 1,
    borderBottomWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 6,
  },
});

export default ActualPdfViewer;

// @ts-nocheck
import { ScrollViewStyleReset } from "expo-router/html";
import type { PropsWithChildren } from "react";

export default function Root({ children }: PropsWithChildren) {
  return (
    <html lang="en" style={{ height: "100%" }}>
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, shrink-to-fit=no"
        />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Anek+Gujarati:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <link rel="manifest" href="/manifest.json?v=2" />
        <link rel="icon" type="image/png" sizes="32x32" href="/icons/favicon-32x32.v2.png" />
        <link rel="icon" type="image/png" sizes="16x16" href="/icons/favicon-16x16.v2.png" />
        <link rel="apple-touch-icon" sizes="180x180" href="/icons/apple-touch-icon.v2.png" />
        <meta name="theme-color" content="#0B1B3D" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="NyaySetu Pro" />
        <meta name="application-name" content="NyaySetu Pro" />
        {/*
          Disable body scrolling on web to make ScrollView components work correctly.
          If you want to enable scrolling, remove `ScrollViewStyleReset` and
          set `overflow: auto` on the body style below.
        */}
        <ScrollViewStyleReset />
        <style
          dangerouslySetInnerHTML={{
            __html: `
              body > div:first-child { position: fixed !important; top: 0; left: 0; right: 0; bottom: 0; }
              [role="tablist"] [role="tab"] * { overflow: visible !important; }
              [role="heading"], [role="heading"] * { overflow: visible !important; }
              body, input, textarea, select, button, div, span, p, a, h1, h2, h3, h4, h5, h6 {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", "Anek Gujarati", sans-serif;
              }
            `,
          }}
        />
      </head>
      <body
        style={{
          margin: 0,
          height: "100%",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {children}
      </body>
    </html>
  );
}

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
        <title>NyaySetu Pro — The New Era of Advocacy</title>
        <meta
          name="description"
          content="NyaySetu Pro — The New Era of Advocacy. High-speed legal drafting and court case management platform for advocates in Gujarat and India."
        />

        {/* DNS Preconnect for Google Fonts & Razorpay */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link rel="preconnect" href="https://checkout.razorpay.com" />

        {/* Razorpay Standard Checkout */}
        <script src="https://checkout.razorpay.com/v1/checkout.js" async />

        {/* High-priority Preload for LCP Brand Logo */}
        <link rel="preload" as="image" href="/logo.webp" type="image/webp" fetchpriority="high" />

        {/* Non-Render-Blocking Google Fonts */}
        <link
          rel="preload"
          as="style"
          href="https://fonts.googleapis.com/css2?family=Anek+Gujarati:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Anek+Gujarati:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
          media="print"
          onLoad="this.media='all'"
        />
        <noscript>
          <link
            href="https://fonts.googleapis.com/css2?family=Anek+Gujarati:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap"
            rel="stylesheet"
          />
        </noscript>

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

        {/* Register Service Worker on idle/load with seamless background update */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  var hadController = !!navigator.serviceWorker.controller;
                  navigator.serviceWorker.register('/sw.js').then(function(reg) {
                    reg.update().catch(function() {});
                    document.addEventListener('visibilitychange', function() {
                      if (document.visibilityState === 'visible') {
                        reg.update().catch(function() {});
                      }
                    });
                  }).catch(function() {});
                  navigator.serviceWorker.addEventListener('controllerchange', function() {
                    if (hadController) {
                      window.location.reload();
                    }
                  });
                });
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
        <div id="splash-loader" style={{ display: "flex", flex: 1, alignItems: "center", justifyContent: "center", background: "linear-gradient(180deg,#061024,#0B1B3D,#112240)", height: "100%", flexDirection: "column" }}>
          <img src="/logo.webp" alt="NyaySetu Pro Logo" width="120" height="129" style={{ objectFit: "contain" }} fetchpriority="high" />
          <div style={{ color: "#FDFDFD", fontSize: "32px", fontWeight: "700", marginTop: "24px", letterSpacing: "0.5px", fontFamily: "serif" }}>NyaySetu Pro</div>
          <div style={{ color: "#C5A059", fontSize: "14px", marginTop: "8px", letterSpacing: "1.5px", textTransform: "uppercase", fontWeight: "600" }}>The New Era of Advocacy</div>
        </div>
        {children}
      </body>
    </html>
  );
}

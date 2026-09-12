const fs = require('fs');
const path = require('path');

const distDir = path.join(__dirname, '..', 'dist');

const pwaAndFontTags = `
    <title>NyaySetu Pro - The New Era of Advocacy</title>
    <meta name="description" content="NyaySetu Pro - The New Era of Advocacy. High-speed legal drafting and court case management platform for advocates in Gujarat and India." />

    <!-- Google Fonts Preconnect -->
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />

    <!-- High-priority Preload for LCP Brand Logo -->
    <link rel="preload" as="image" href="/logo.webp" type="image/webp" fetchpriority="high" />

    <!-- Non-Render-Blocking Google Fonts (Anek Gujarati & Inter) -->
    <link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Anek+Gujarati:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" />
    <link href="https://fonts.googleapis.com/css2?family=Anek+Gujarati:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'" />
    <noscript>
      <link href="https://fonts.googleapis.com/css2?family=Anek+Gujarati:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
    </noscript>
    
    <!-- PWA & Android / iOS High-Resolution Icons -->
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
    
    <!-- High-speed preloading for Razorpay Checkout script -->
    <link rel="preload" href="https://checkout.razorpay.com/v1/checkout.js" as="script" />

    <style>
      body, input, textarea, select, button, div, span, p, a, h1, h2, h3, h4, h5, h6 {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", "Anek Gujarati", sans-serif;
      }
      /* Razorpay Standard Checkout Viewport Centering */
      .razorpay-container {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        height: 100dvh !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        z-index: 2147483647 !important;
      }
      .razorpay-container > iframe {
        margin: auto !important;
      }
    </style>

    <!-- Register Service Worker on idle/load with seamless background update -->
    <script>
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
    </script>`;

function processHtmlFiles(dir) {
  if (!fs.existsSync(dir)) return;
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const fullPath = path.join(dir, file);
    if (fs.statSync(fullPath).isDirectory()) {
      // Skip the admin directory to avoid breaking the Vite build
      if (file !== 'admin') {
        processHtmlFiles(fullPath);
      }
    } else if (file.endsWith('.html')) {
      let html = fs.readFileSync(fullPath, 'utf8');
      
      // Clean up duplicate generic title added by Expo Router
      if (html.includes('<title>NyaySetu Pro</title>')) {
        html = html.replace('<title>NyaySetu Pro</title>', '');
      }

      // Inject Splash Loader inside <div id="root"> if missing
      const splashHTML = `<main><div id="splash-loader" style="display:flex;flex:1;align-items:center;justify-content:center;background:linear-gradient(180deg,#061024,#0B1B3D,#112240);height:100%;flex-direction:column;width:100%;position:absolute;z-index:999999;">
        <img fetchpriority="high" src="/logo.webp" alt="NyaySetu Pro Logo" width="120" height="129" style="object-fit:contain" />
        <div style="color:#FDFDFD;font-size:32px;font-weight:700;margin-top:24px;letter-spacing:0.5px;font-family:serif">NyaySetu Pro</div>
        <div style="color:#C5A059;font-size:14px;margin-top:8px;letter-spacing:1.5px;text-transform:uppercase;font-weight:600">The New Era of Advocacy</div>
      </div></main>`;

      if (!html.includes('splash-loader') && html.includes('<div id="root"></div>')) {
        html = html.replace('<div id="root"></div>', `<div id="root">${splashHTML}</div>`);
        console.log(`✓ Injected static LCP splash skeleton into ${file}`);
      }

      if (!html.includes('family=Anek+Gujarati')) {
        html = html.replace('</head>', `${pwaAndFontTags}\n  </head>`);
        fs.writeFileSync(fullPath, html, 'utf8');
        console.log(`✓ Injected PWA tags into ${path.relative(distDir, fullPath)}`);
      } else {
        // Just write if title or splash was replaced
        fs.writeFileSync(fullPath, html, 'utf8');
      }
    }
  }
}

processHtmlFiles(distDir);

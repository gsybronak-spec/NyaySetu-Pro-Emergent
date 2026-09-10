const fs = require('fs');
const path = require('path');

const distDir = path.join(__dirname, '..', 'dist');

const pwaAndFontTags = `
    <title>NyaySetu Pro — The New Era of Advocacy</title>
    <meta name="description" content="NyaySetu Pro — The New Era of Advocacy. High-speed legal drafting and court case management platform for advocates in Gujarat and India." />

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
    
    <style>
      body, input, textarea, select, button, div, span, p, a, h1, h2, h3, h4, h5, h6 {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", "Anek Gujarati", sans-serif;
      }
    </style>

    <!-- Register Service Worker on idle/load -->
    <script>
      if ('serviceWorker' in navigator) {
        window.addEventListener('load', function() {
          navigator.serviceWorker.register('/sw.js').catch(function() {});
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

      if (!html.includes('family=Anek+Gujarati')) {
        html = html.replace('</head>', `${pwaAndFontTags}\n  </head>`);
        fs.writeFileSync(fullPath, html, 'utf8');
        console.log(`✓ Injected PWA tags into ${path.relative(distDir, fullPath)}`);
      } else {
        // Just write if title was replaced
        fs.writeFileSync(fullPath, html, 'utf8');
      }
    }
  }
}

processHtmlFiles(distDir);

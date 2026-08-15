const fs = require('fs');
const path = require('path');

const distHtmlPath = path.join(__dirname, '..', 'dist', 'index.html');

if (fs.existsSync(distHtmlPath)) {
  let html = fs.readFileSync(distHtmlPath, 'utf8');
  
  const pwaAndFontTags = `
    <!-- Google Fonts: Anek Gujarati & Inter -->
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Anek+Gujarati:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
    
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
    </style>`;
  
  if (!html.includes('family=Anek+Gujarati')) {
    html = html.replace('</head>', `${pwaAndFontTags}\n  </head>`);
    fs.writeFileSync(distHtmlPath, html, 'utf8');
    console.log('✓ Successfully injected Anek Gujarati web fonts and PWA meta tags into dist/index.html');
  }
}

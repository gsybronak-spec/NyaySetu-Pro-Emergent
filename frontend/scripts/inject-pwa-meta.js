const fs = require('fs');
const path = require('path');

const distHtmlPath = path.join(__dirname, '..', 'dist', 'index.html');

if (fs.existsSync(distHtmlPath)) {
  let html = fs.readFileSync(distHtmlPath, 'utf8');
  
  const pwaTags = `
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
    <meta name="application-name" content="NyaySetu Pro" />`;
  
  if (!html.includes('rel="manifest"')) {
    html = html.replace('</head>', `${pwaTags}\n  </head>`);
    fs.writeFileSync(distHtmlPath, html, 'utf8');
    console.log('✓ Successfully injected PWA manifest and high-res icon meta tags into dist/index.html');
  }
}

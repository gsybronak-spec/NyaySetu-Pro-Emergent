const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const adminDir = path.join(__dirname, '..', '..', 'admin');
const adminDist = path.join(adminDir, 'dist');
const targetAdminDist = path.join(__dirname, '..', 'dist', 'admin');
const publicAdminDir = path.join(__dirname, '..', 'public', 'admin');

if (!fs.existsSync(path.join(__dirname, '..', 'dist'))) {
  fs.mkdirSync(path.join(__dirname, '..', 'dist'), { recursive: true });
}

// First ensure dist/admin has the verified pre-bundled admin portal
if (fs.existsSync(publicAdminDir)) {
  fs.cpSync(publicAdminDir, targetAdminDist, { recursive: true });
  console.log('✓ Seeded frontend/dist/admin/ from public/admin/');
}

// In local environment with full node_modules, build fresh
if (fs.existsSync(path.join(adminDir, 'node_modules'))) {
  try {
    console.log('Building fresh Admin Portal from admin/...');
    execSync('npm run build', { cwd: adminDir, stdio: 'inherit' });
    if (fs.existsSync(adminDist)) {
      fs.cpSync(adminDist, targetAdminDist, { recursive: true });
      fs.cpSync(adminDist, publicAdminDir, { recursive: true });
      console.log('✓ Fresh Admin Portal build copied to dist/admin/ and public/admin/');
    }
  } catch (err) {
    console.warn('Notice: admin build failed or skipped, retained verified bundle in public/admin/');
  }
} else {
  console.log('✓ CI/Vercel build: using verified pre-bundled Admin Portal from public/admin/');
}

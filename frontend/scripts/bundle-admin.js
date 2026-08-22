const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const adminDir = path.join(__dirname, '..', '..', 'admin');
const adminDist = path.join(adminDir, 'dist');
const targetAdminDist = path.join(__dirname, '..', 'dist', 'admin');

if (fs.existsSync(adminDir)) {
  console.log('Building original Admin Portal in admin/...');
  execSync('npm run build', { cwd: adminDir, stdio: 'inherit' });

  if (fs.existsSync(adminDist)) {
    if (!fs.existsSync(path.join(__dirname, '..', 'dist'))) {
      fs.mkdirSync(path.join(__dirname, '..', 'dist'), { recursive: true });
    }
    if (fs.existsSync(targetAdminDist)) {
      fs.rmSync(targetAdminDist, { recursive: true, force: true });
    }
    fs.cpSync(adminDist, targetAdminDist, { recursive: true });
    console.log('✓ Successfully bundled original Admin Portal into frontend/dist/admin/');
  } else {
    console.error('Error: admin/dist was not produced by build.');
    process.exit(1);
  }
} else {
  console.warn('Warning: admin directory not found at', adminDir);
}

const path = require("path");
const Module = require("module");

// Node polyfill for window.localStorage used by web storage
if (typeof global.window === "undefined") {
  const store = new Map();
  const mockStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
    clear: () => store.clear(),
  };
  global.window = {
    localStorage: mockStorage,
    dispatchEvent: () => true,
    addEventListener: () => {},
    removeEventListener: () => {},
  };
  global.localStorage = mockStorage;
  global.CustomEvent = class CustomEvent {
    constructor(type, init) {
      this.type = type;
      this.detail = init && init.detail;
    }
  };
}

// Hook require to resolve '@/...' to frontend/... and transpile ts files with sucrase
const originalResolveFilename = Module._resolveFilename;
Module._resolveFilename = function (request, parent, isMain, options) {
  if (request === "@/src/utils/storage" || request === "@/src/utils/storage/index") {
    const resolvedPath = path.resolve(__dirname, "..", "src/utils/storage/index.web.ts");
    return originalResolveFilename.call(this, resolvedPath, parent, isMain, options);
  }
  if (request.startsWith("@/")) {
    const sub = request.slice(2);
    const resolvedPath = path.resolve(__dirname, "..", sub);
    return originalResolveFilename.call(this, resolvedPath, parent, isMain, options);
  }
  return originalResolveFilename.call(this, request, parent, isMain, options);
};

const sucrase = require("../node_modules/sucrase");
const vm = require("vm");
require.extensions[".ts"] = function (module, filename) {
  const fs = require("fs");
  let code = fs.readFileSync(filename, "utf8");
  if (filename.includes("admin")) {
    code = code.replace(/import\.meta/g, "({ env: process.env })");
  }
  const transformed = sucrase.transform(code, {
    transforms: ["typescript", "imports"],
    filePath: filename,
  });
  const wrapper = Module.wrap(transformed.code);
  const compiled = vm.runInThisContext(wrapper, { filename });
  const localRequire = Module.createRequire ? Module.createRequire(filename) : require;
  compiled.call(module.exports, module.exports, localRequire, module, filename, path.dirname(filename));
};

require("./test_template_opening.test.ts");
const { runCatalogPaginationTests } = require("./catalog_pagination.test.ts");
runCatalogPaginationTests();
const { runPhase4CDynamicAlignmentTests } = require("./phase4c_dynamic_alignment.test.ts");
const { runPhase4DAdminInvalidationTests } = require("./phase4d_admin_invalidation.test.ts");
const { runComprehensive10xStressSyncTests } = require("./comprehensive_10x_stress_sync.test.ts");

async function main() {
  await runPhase4CDynamicAlignmentTests();
  await runPhase4DAdminInvalidationTests();
  await runComprehensive10xStressSyncTests();
  process.exit(0);
}

main().catch((err) => {
  console.error("Test execution FAILED:", err);
  process.exit(1);
});




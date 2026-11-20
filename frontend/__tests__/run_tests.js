const path = require("path");
const Module = require("module");

// Hook require to resolve '@/...' to frontend/... and transpile ts files with sucrase
const originalResolveFilename = Module._resolveFilename;
Module._resolveFilename = function (request, parent, isMain, options) {
  if (request.startsWith("@/")) {
    const sub = request.slice(2);
    const resolvedPath = path.resolve(__dirname, "..", sub);
    return originalResolveFilename.call(this, resolvedPath, parent, isMain, options);
  }
  return originalResolveFilename.call(this, request, parent, isMain, options);
};

let transpile;
try {
  const sucrase = require("../node_modules/sucrase");
  transpile = (code, filename) => sucrase.transform(code, { transforms: ["typescript", "imports"], filePath: filename }).code;
} catch {
  const ts = require(path.resolve(__dirname, "../../admin/node_modules/typescript"));
  transpile = (code, filename) => ts.transpileModule(code, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
    fileName: filename
  }).outputText;
}

require.extensions[".ts"] = function (module, filename) {
  const fs = require("fs");
  const code = fs.readFileSync(filename, "utf8");
  module._compile(transpile(code, filename), filename);
};

require("./test_template_opening.test.ts");
const { runCatalogPaginationTests } = require("./catalog_pagination.test.ts");
runCatalogPaginationTests();
const { runFinalThreeRequirementsFrontendTests } = require("./final_three_requirements.test.ts");
runFinalThreeRequirementsFrontendTests();
const { runTemplateOrderConsistencyTests } = require("./test_template_order_consistency.test.ts");
runTemplateOrderConsistencyTests();
const { runInstantStartupCacheTests } = require("./test_instant_startup_cache.test.ts");
runInstantStartupCacheTests();
const { runDraftBulkDeleteTests } = require("./test_draft_bulk_delete.test.ts");
const { runFinalUIFixesTests } = require("./test_final_ui_fixes.test.ts");
(async () => {
  await runDraftBulkDeleteTests();
  await runFinalUIFixesTests();
  require("./verify_browser_behavior.js");
})().catch((err) => {
  console.error("Test runner failed:", err);
  process.exit(1);
});




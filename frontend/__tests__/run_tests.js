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

const sucrase = require("../node_modules/sucrase");
require.extensions[".ts"] = function (module, filename) {
  const fs = require("fs");
  const code = fs.readFileSync(filename, "utf8");
  const transformed = sucrase.transform(code, {
    transforms: ["typescript", "imports"],
    filePath: filename,
  });
  module._compile(transformed.code, filename);
};

require("./test_template_opening.test.ts");
const { runCatalogPaginationTests } = require("./catalog_pagination.test.ts");
runCatalogPaginationTests();


import { access, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outputRoot = path.join(packageRoot, "dist");

for (const file of ["architecture_snapshot.json", "README.md", "SUMMARY.md", "manifest.json"]) {
  await access(path.join(outputRoot, file));
}

const snapshot = JSON.parse(await readFile(path.join(outputRoot, "architecture_snapshot.json"), "utf8"));
if (!snapshot.schema_version || !Array.isArray(snapshot.modules) || !Array.isArray(snapshot.entities)) {
  throw new Error("Architecture snapshot package is incomplete");
}

console.log(`Architecture model package is valid: ${snapshot.modules.length} modules, ${snapshot.entities.length} entities`);

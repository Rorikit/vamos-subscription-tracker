import { cp, mkdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(packageRoot, "../..");
const sourceRoot = path.join(repositoryRoot, "docs", "architecture");
const outputRoot = path.join(packageRoot, "dist");
const files = ["architecture_snapshot.json", "README.md", "SUMMARY.md"];

await mkdir(outputRoot, { recursive: true });

for (const file of files) {
  await cp(path.join(sourceRoot, file), path.join(outputRoot, file));
}

const snapshotPath = path.join(outputRoot, "architecture_snapshot.json");
const snapshot = JSON.parse(await readFile(snapshotPath, "utf8"));
const manifest = {
  package_version: JSON.parse(await readFile(path.join(packageRoot, "package.json"), "utf8")).version,
  schema_version: snapshot.schema_version,
  model_contract_version: snapshot.model_contract_version,
  git_commit: snapshot.metadata?.git_commit ?? null,
  generated_at: snapshot.metadata?.generated_at ?? null
};

await writeFile(path.join(outputRoot, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(`Architecture model package built from ${sourceRoot}`);

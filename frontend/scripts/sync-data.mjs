// Copies research results (JSON) and report figures (PNG) into public/data so the
// Results and Report pages work on plain static hosting, without the API.
//   ../reports/results/*.json  -> public/data/results/   (*.npz excluded)
//   ../reports/figures/*.png   -> public/data/figures/
import { copyFileSync, existsSync, mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const project = resolve(root, "..");

const jobs = [
  { from: join(project, "reports", "results"), to: join(root, "public", "data", "results"), ext: [".json"] },
  { from: join(project, "reports", "figures"), to: join(root, "public", "data", "figures"), ext: [".png"] },
  // the project reports, so the Report page's download links work on static hosting too
  { from: join(project, "docs"), to: join(root, "public", "docs"), ext: [".pdf", ".docx"] },
];

for (const { from, to, ext } of jobs) {
  mkdirSync(to, { recursive: true });
  if (!existsSync(from)) {
    // e.g. a static-host build (Vercel) where only frontend/ is checked out:
    // keep whatever is already committed in public/ and carry on.
    console.log(`sync-data: ${from} not found, keeping the committed copies in ${to}`);
    continue;
  }
  const files = readdirSync(from).filter((f) => ext.some((e) => f.toLowerCase().endsWith(e)));
  for (const f of files) copyFileSync(join(from, f), join(to, f));
  // manifest lets the UI know which static files exist without probing each one
  writeFileSync(join(to, "manifest.json"), JSON.stringify({ files, synced_at: new Date().toISOString() }, null, 2));
  console.log(`sync-data: copied ${files.length} ${ext} file(s) -> ${to}`);
}

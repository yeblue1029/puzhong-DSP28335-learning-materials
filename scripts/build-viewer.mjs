#!/usr/bin/env node
/**
 * build-viewer.mjs — Fetch the official Mozilla PDF.js prebuilt distribution,
 * trim it to a minimal footprint, apply the cross-origin patch, and place the
 * result into viewer/build + viewer/web.
 *
 * The PDF.js binaries are NOT committed to the repository (keeps history clean
 * and makes upgrades a one-line version bump). This script regenerates them
 * identically both locally and in GitHub Actions, so what you test locally is
 * exactly what gets deployed.
 *
 * Run:  node scripts/build-viewer.mjs
 *
 * Reproducible: same version + same patch => byte-identical viewer/ contents.
 */

import { execSync } from "node:child_process";
import {
  mkdirSync,
  rmSync,
  cpSync,
  readdirSync,
  readFileSync,
  writeFileSync,
  existsSync,
} from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, "..");
const VIEWER = join(REPO_ROOT, "viewer");

// --- configuration --------------------------------------------------------
const PDFJS_VERSION = "6.2.108";
const DIST_URL = `https://github.com/mozilla/pdf.js/releases/download/v${PDFJS_VERSION}/pdfjs-${PDFJS_VERSION}-dist.zip`;
const KEEP_LOCALES = ["en-US", "zh-CN", "zh-TW"];

const WORK = join(REPO_ROOT, "_pdfjs_build_tmp");

function run(cmd) {
  execSync(cmd, { stdio: "inherit", cwd: REPO_ROOT });
}

function extractZip(zip, dest) {
  // Prefer the `unzip` CLI; fall back to Python (ubiquitous on CI & dev).
  try {
    execSync(`unzip -q -o "${zip}" -d "${dest}"`, { stdio: "pipe" });
  } catch {
    execSync(
      `python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "${zip}" "${dest}"`,
      { stdio: "pipe" }
    );
  }
}

function trimLocale(webDir) {
  const localeDir = join(webDir, "locale");
  if (!existsSync(localeDir)) return;
  const tmp = join(WORK, "locale-keep");
  mkdirSync(tmp, { recursive: true });
  for (const loc of KEEP_LOCALES) {
    const src = join(localeDir, loc);
    if (existsSync(src)) cpSync(src, join(tmp, loc), { recursive: true });
  }
  rmSync(localeDir, { recursive: true, force: true });
  mkdirSync(localeDir, { recursive: true });
  for (const loc of KEEP_LOCALES) {
    const src = join(tmp, loc);
    if (existsSync(src)) cpSync(src, join(localeDir, loc), { recursive: true });
  }
}

/**
 * Apply the cross-origin patch to web/viewer.mjs. The official viewer refuses
 * to load PDFs whose origin differs from the viewer's origin ("file origin
 * does not match viewer's"). We allow raw.githubusercontent.com / jsdelivr.
 *
 * Returns true if the patch was applied (or already present), false if the
 * expected anchor could not be found (upstream changed => manual review).
 */
function applyPatch(viewerMjs) {
  let src = readFileSync(viewerMjs, "utf8");
  const TAG = "[DSP28335-PDF-LIBRARY PATCH";

  if (src.includes(TAG)) {
    console.log("[build-viewer] cross-origin patch already present.");
    return true;
  }

  const anchor =
    'const HOSTED_VIEWER_ORIGINS = new Set(["null", "http://mozilla.github.io", "https://mozilla.github.io"]);';
  if (!src.includes(anchor)) {
    console.warn(
      "[build-viewer] WARNING: HOSTED_VIEWER_ORIGINS anchor not found — PDF.js may have changed. Manual patch review required."
    );
    return false;
  }

  const insert =
    anchor +
    "\n  // [DSP28335-PDF-LIBRARY PATCH BEGIN] allow cross-origin PDF loading from GitHub raw (CORS-enabled).\n  // Re-apply this block when upgrading PDF.js (see viewer/MAINTENANCE.md).\n  const ALLOWED_PDF_ORIGINS = new Set([\"https://raw.githubusercontent.com\", \"https://cdn.jsdelivr.net\"]);\n  // [DSP28335-PDF-LIBRARY PATCH END]";
  src = src.replace(anchor, insert);

  const condOld = "    if (fileOrigin === viewerOrigin) {";
  const condNew =
    '    if (fileOrigin === viewerOrigin || ALLOWED_PDF_ORIGINS.has(fileOrigin)) {';
  if (!src.includes(condOld)) {
    console.warn(
      "[build-viewer] WARNING: fileOrigin condition anchor not found — manual patch review required."
    );
    return false;
  }
  src = src.replace(condOld, condNew);

  writeFileSync(viewerMjs, src);
  console.log("[build-viewer] cross-origin patch applied.");
  return true;
}

// --- main -----------------------------------------------------------------
function main() {
  console.log(`[build-viewer] PDF.js version: ${PDFJS_VERSION}`);

  // 1. download
  rmSync(WORK, { recursive: true, force: true });
  mkdirSync(WORK, { recursive: true });
  const zip = join(WORK, "pdfjs-dist.zip");
  console.log(`[build-viewer] downloading ${DIST_URL}`);
  run(`curl -sL "${DIST_URL}" -o "${zip}"`);

  // 2. extract
  const extracted = join(WORK, "extract");
  mkdirSync(extracted, { recursive: true });
  extractZip(zip, extracted);

  // 3. trim
  const buildDir = join(extracted, "build");
  const webDir = join(extracted, "web");
  for (const f of readdirSync(buildDir)) {
    if (f.endsWith(".map")) rmSync(join(buildDir, f), { force: true });
  }
  for (const f of [...readdirSync(webDir)]) {
    const p = join(webDir, f);
    const isMap = f.endsWith(".map");
    const isDemo = f === "compressed.tracemonkey-pldi-09.pdf";
    const isDebugger = f.startsWith("debugger.");
    if ((isMap || isDemo || isDebugger) && !f.includes("/")) {
      rmSync(p, { force: true });
    }
  }
  trimLocale(webDir);

  // 4. place into viewer/
  mkdirSync(join(VIEWER, "build"), { recursive: true });
  mkdirSync(join(VIEWER, "web"), { recursive: true });
  rmSync(join(VIEWER, "build"), { recursive: true, force: true });
  rmSync(join(VIEWER, "web"), { recursive: true, force: true });
  cpSync(buildDir, join(VIEWER, "build"), { recursive: true });
  cpSync(webDir, join(VIEWER, "web"), { recursive: true });
  // license
  const lic = join(extracted, "LICENSE");
  if (existsSync(lic)) cpSync(lic, join(VIEWER, "LICENSE"));

  // 5. patch
  applyPatch(join(VIEWER, "web", "viewer.mjs"));

  // 6. cleanup
  rmSync(WORK, { recursive: true, force: true });

  console.log("[build-viewer] done. viewer/build + viewer/web ready.");
}

try {
  main();
} catch (e) {
  console.error("[build-viewer] FAILED:", e.message);
  rmSync(WORK, { recursive: true, force: true });
  process.exit(1);
}

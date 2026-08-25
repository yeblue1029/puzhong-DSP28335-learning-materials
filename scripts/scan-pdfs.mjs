#!/usr/bin/env node
/**
 * scan-pdfs.mjs — Recursively scan the repository for PDF files and emit
 * `pdf-index.json`, the single source of truth consumed by the PDF Library
 * page (viewer/index.html) and by cloud AIs / scripts that need raw URLs.
 *
 * Design goals:
 *  - Dependency-free (Node 18+ built-ins only) so it runs in GitHub Actions
 *    and locally with zero install.
 *  - Identifies both `.pdf` and `.PDF` (case-insensitive).
 *  - Skips .git, node_modules, build outputs and the viewer's own asset dirs.
 *  - Correctly handles Chinese filenames, spaces and special characters via
 *    per-segment encodeURIComponent when building raw/viewer URLs.
 *  - Detects Git-LFS tracked files (raw returns the pointer, not the PDF).
 *
 * Configuration via environment variables (all optional, sensible defaults):
 *   REPO_OWNER, REPO_NAME, REPO_BRANCH   — GitHub coordinates for URL building
 *   PAGES_BASE_URL                       — deployed site origin (no trailing slash)
 *   SCAN_ROOT                            — repo root to scan (default: parent of scripts/)
 *   OUTPUT                               — path to write pdf-index.json
 *   GITATTRIBUTES                         — path to .gitattributes (default: SCAN_ROOT/.gitattributes)
 *
 * Usage:
 *   node scripts/scan-pdfs.mjs
 */

import { readdirSync, statSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, relative, dirname, basename, sep, posix } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// --- configuration ---------------------------------------------------------
const REPO_OWNER = process.env.REPO_OWNER || "yeblue1029";
const REPO_NAME = process.env.REPO_NAME || "puzhong-DSP28335-learning-materials";
const REPO_BRANCH = process.env.REPO_BRANCH || "main";
const PAGES_BASE_URL = (
  process.env.PAGES_BASE_URL ||
  `https://${REPO_OWNER}.github.io/${REPO_NAME}`
).replace(/\/+$/, "");
const SCAN_ROOT = process.env.SCAN_ROOT
  ? process.env.SCAN_ROOT.replace(/\/+$/, "")
  : join(__dirname, ".."); // repo root by default
const OUTPUT = process.env.OUTPUT || join(SCAN_ROOT, "viewer", "pdf-index.json");
const GITATTRIBUTES =
  process.env.GITATTRIBUTES || join(SCAN_ROOT, ".gitattributes");

// Top-level / path-based exclusions (never content PDFs live here).
const EXCLUDE_DIRS = new Set([
  ".git",
  "node_modules",
  "_github_worktree",
  "_github_extract_staging",
  "_github_upload_logs",
  ".github_upload_logs",
  "_github_scan",
  ".vscode",
  ".idea",
  ".vs",
  ".trae",
  "AI_REPO_INDEX",
]);
// The viewer itself ships no learning-content PDFs; skip its asset folders.
const EXCLUDE_VIEWER_ASSET_DIRS = new Set(["viewer/build", "viewer/web"]);

// CCS / DSP build-output directory names — never hold source PDFs.
const BUILD_OUTPUT_DIRS = new Set([
  "Debug",
  "Release",
]);

const PDF_EXT = /\.(pdf)$/i;

// --- helpers ---------------------------------------------------------------
function humanSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let v = bytes / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(v >= 100 ? 0 : 1)} ${units[i]}`;
}

/**
 * URL-encode a repo-relative path for use in a raw URL. Each path segment is
 * encoded with encodeURIComponent (handles Chinese, spaces, parentheses),
 * while `/` separators are preserved.
 */
function encodeRepoPath(pathStr) {
  return pathStr
    .split("/")
    .map((seg) => encodeURIComponent(seg))
    .join("/");
}

/** Convert a .gitattributes git pathspec into a RegExp for LFS matching. */
function globToRegExp(pattern) {
  // git pathspecs: ** matches across directories, * matches within a segment
  // (does not cross /), ? matches a single char (not /).
  let re = "";
  let i = 0;
  while (i < pattern.length) {
    const c = pattern[i];
    if (pattern[i] === "*" && pattern[i + 1] === "*") {
      i += 2;
      if (pattern[i] === "/") {
        i++;
      }
      re += ".*";
    } else if (c === "*") {
      re += "[^/]*";
      i++;
    } else if (c === "?") {
      re += "[^/]";
      i++;
    } else if (".+^$(){}|[]\\".includes(c)) {
      re += "\\" + c;
      i++;
    } else {
      re += c;
      i++;
    }
  }
  return new RegExp("^" + re + "$");
}

/** Parse .gitattributes and return RegExp matchers for LFS-tracked paths. */
function loadLfsMatchers() {
  const matchers = [];
  if (!existsSync(GITATTRIBUTES)) return matchers;
  const lines = readFileSync(GITATTRIBUTES, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const m = line.match(/^\s*(\S+)\s+.*filter=lfs\b/);
    if (m) {
      const pattern = m[1].replace(/^\//, ""); // leading slash = repo root
      try {
        matchers.push(globToRegExp(pattern));
      } catch {
        /* ignore unparseable pattern */
      }
    }
  }
  return matchers;
}

/** Normalise a path to forward slashes (POSIX) for stable cross-platform keys. */
function toPosix(p) {
  return p.split(sep).join("/");
}

function isExcludedDir(relDir) {
  const posixDir = toPosix(relDir);
  const parts = posixDir.split("/");
  // any excluded top-level/internal dir on the path
  if (parts.some((p) => EXCLUDE_DIRS.has(p))) return true;
  // viewer asset directories
  if (EXCLUDE_VIEWER_ASSET_DIRS.has(posixDir)) return true;
  if (posixDir.startsWith("viewer/build") || posixDir.startsWith("viewer/web"))
    return true;
  // CCS build output directories (Debug / Release at any level)
  if (parts.some((seg) => BUILD_OUTPUT_DIRS.has(seg))) return true;
  return false;
}

/**
 * Recursive directory walk. Uses readdirSync({recursive:true}) when available
 * (Node 20+) for speed, with a manual fallback for older runtimes.
 */
function walk(root) {
  const out = [];
  let entries;
  try {
    entries = readdirSync(root, { recursive: true, withFileTypes: true });
  } catch {
    entries = [];
  }
  for (const ent of entries) {
    if (!ent.isFile()) continue;
    const full = ent.parentPath
      ? join(ent.parentPath, ent.name)
      : join(root, ent.name);
    const rel = relative(root, full);
    if (!PDF_EXT.test(ent.name)) continue;
    const relDir = dirname(rel);
    if (relDir !== "." && isExcludedDir(relDir)) continue;
    out.push({ full, rel: toPosix(rel) });
  }
  return out;
}

// --- main ------------------------------------------------------------------
function main() {
  const lfsMatchers = loadLfsMatchers();
  const found = walk(SCAN_ROOT);
  found.sort((a, b) => a.rel.localeCompare(b.rel, "zh"));

  const files = found.map(({ full, rel }) => {
    const isLfs = lfsMatchers.some((re) => re.test(rel));
    const st = statSync(full);
    let realSize = st.size;
    // In a checkout without Git-LFS smudge (e.g. GitHub Actions default), an
    // LFS file is a tiny pointer text (~130 B). Parse the real object size from
    // the pointer's `size N` line so the index stays accurate without fetching
    // the (large) LFS objects.
    if (isLfs && realSize < 1024) {
      try {
        const txt = readFileSync(full, "utf8");
        const m = txt.match(/^size\s+(\d+)\s*$/m);
        if (m) realSize = Number(m[1]);
      } catch {
        /* fall back to stat size */
      }
    }
    const encoded = encodeRepoPath(rel);
    const rawUrl = `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${REPO_BRANCH}/${encoded}`;
    const viewerUrl = `${PAGES_BASE_URL}/web/viewer.html?file=${encodeURIComponent(rawUrl)}`;
    const githubUrl = `https://github.com/${REPO_OWNER}/${REPO_NAME}/blob/${REPO_BRANCH}/${encoded}`;
    return {
      name: basename(rel),
      path: rel,
      dir: dirname(rel) === "." ? "" : dirname(rel),
      size: realSize,
      size_human: humanSize(realSize),
      lfs: isLfs,
      raw_url: rawUrl,
      viewer_url: viewerUrl,
      github_url: githubUrl,
    };
  });

  const totalSize = files.reduce((s, f) => s + f.size, 0);
  const lfsCount = files.filter((f) => f.lfs).length;

  const index = {
    generated_at: new Date().toISOString(),
    generator: "scripts/scan-pdfs.mjs",
    pdfjs_version: "6.2.108",
    repo: `${REPO_OWNER}/${REPO_NAME}`,
    branch: REPO_BRANCH,
    pages_base_url: PAGES_BASE_URL,
    raw_base_url: `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${REPO_BRANCH}`,
    pdf_count: files.length,
    lfs_count: lfsCount,
    total_size: totalSize,
    total_size_human: humanSize(totalSize),
    note:
      "raw_url points at raw.githubusercontent.com. For non-LFS PDFs this returns the real PDF binary (CORS enabled, HTTP Range supported). For LFS-tracked PDFs raw returns a Git-LFS pointer, not the PDF — see viewer/MAINTENANCE.md.",
    files,
  };

  writeFileSync(OUTPUT, JSON.stringify(index, null, 2));

  // console summary
  console.log(`[scan-pdfs] scanned: ${SCAN_ROOT}`);
  console.log(`[scan-pdfs] PDFs found: ${files.length}`);
  console.log(`[scan-pdfs] LFS-tracked: ${lfsCount}`);
  console.log(`[scan-pdfs] total size: ${humanSize(totalSize)}`);
  console.log(`[scan-pdfs] wrote: ${OUTPUT}`);
  if (lfsCount) {
    console.log("[scan-pdfs] LFS files (raw returns pointer, not PDF):");
    for (const f of files.filter((x) => x.lfs)) console.log(`   - ${f.path}`);
  }
}

main();

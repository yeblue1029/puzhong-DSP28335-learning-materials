# PDF 在线文档系统 · 维护说明

本文件说明仓库内 PDF 在线阅读系统的架构、升级方式与已知限制。
面向未来的维护者（包括人与 AI），请在修改 `viewer/`、`scripts/`、`.github/workflows/` 前先读完本文件。

---

## 一、架构总览

```
GitHub Repository (main 分支)
  └─ 原始 PDF（唯一一份，不复制、不移动）
        │
        ├─► raw.githubusercontent.com  ─► 云端 AI / curl / 脚本
        │     （CORS * + HTTP Range，返回真实 PDF 二进制）
        │
GitHub Pages（站点极小，~8 MB）
  ├─ index.html          PDF 文档中心（读取 pdf-index.json 渲染列表）
  ├─ pdf-index.json      由 scripts/scan-pdfs.mjs 自动生成的清单
  ├─ web/                Mozilla PDF.js 官方预构建 viewer（精简版）
  └─ build/              pdf.mjs / pdf.worker.mjs / pdf.sandbox.mjs
        │
        ▼
  浏览器：index.html → 在线阅读链接 → web/viewer.html?file=<raw URL>
          PDF.js 通过 fetch 跨域读取 raw（CORS 已开启）→ canvas 渲染
```

**关键设计决策**

- **PDF 原文件只存一份**：仓库 ~445 MB，PDF 本体不复制进 Pages。
  Pages 只发布极小的 viewer + index（~8 MB），PDF 经 `raw.githubusercontent.com` 读取。
- **同时满足"人"与"AI"**：同一个 `raw_url` 既是 viewer 的数据源，也是 AI / 脚本的原始 PDF 入口。
- **零后端、零数据库、零登录**：纯静态站点，托管在 GitHub Pages。

---

## 二、目录结构

提交到仓库的文件（精小、全文本）：

```
viewer/
  index.html          PDF 文档中心（入口页，运行时 fetch pdf-index.json）
  MAINTENANCE.md      本文件
scripts/
  scan-pdfs.mjs       递归扫描 PDF、生成 pdf-index.json（无依赖，Node 18+）
  build-viewer.mjs    下载官方 PDF.js 预构建包、精简、打跨域补丁（无依赖，Node 18+）
.github/workflows/
  pdf-site.yml        构建 viewer → 扫描 → 发布 GitHub Pages
```

由构建脚本生成的文件（**不提交**，见 `.gitignore`，CI 与本地各自动生成）：

```
viewer/build/         PDF.js 核心库（pdf.mjs / pdf.worker.mjs / pdf.sandbox.mjs）
viewer/web/           PDF.js 官方 viewer（viewer.html / viewer.mjs[含补丁] / viewer.css
                      + images/ locale/ cmaps/ iccs/ standard_fonts/ wasm/）
viewer/LICENSE        PDF.js 的 Apache-2.0 许可
viewer/pdf-index.json 由 scan-pdfs.mjs 生成的 PDF 清单
```

> 因此仓库**不包含**任何 PDF.js 二进制——克隆后运行 `node scripts/build-viewer.mjs`
> 即可复现与线上完全一致的 viewer。

---

## 三、viewer 跨域补丁（升级 PDF.js 时务必重应用）

GitHub Pages（`yeblue1029.github.io`）与 `raw.githubusercontent.com` 不同源。
官方 PDF.js viewer（`web/viewer.mjs`）出于安全考虑，**默认拒绝加载跨源 PDF**
（抛错 `file origin does not match viewer's`）。这不是 CORS 问题——raw 已开启
`Access-Control-Allow-Origin: *`——而是 viewer 自带的来源校验。

为此在 `web/viewer.mjs` 中应用了一处**最小补丁**：放行 `raw.githubusercontent.com`
（以及 `cdn.jsdelivr.net`）作为允许的跨源 PDF 来源。补丁带有标记：

```
// [DSP28335-PDF-LIBRARY PATCH BEGIN] allow cross-origin PDF loading from GitHub raw (CORS-enabled).
// Re-apply this block when upgrading PDF.js (see viewer/MAINTENANCE.md).
const ALLOWED_PDF_ORIGINS = new Set(["https://raw.githubusercontent.com", "https://cdn.jsdelivr.net"]);
// [DSP28335-PDF-LIBRARY PATCH END]
```

并把 `validateFileURL` 中的判断改为：

```js
if (fileOrigin === viewerOrigin || ALLOWED_PDF_ORIGINS.has(fileOrigin)) { return; }
```

**补丁由 `scripts/build-viewer.mjs` 自动应用**：该脚本下载官方包后，按上述两处锚点
（`HOSTED_VIEWER_ORIGINS` 常量行 与 `if (fileOrigin === viewerOrigin) {`）插入补丁。
正常升级时无需手工操作。仅当上游修改了这两个锚点（脚本会打印 WARNING）时，才需人工
参照本节手动适配，并在 `build-viewer.mjs` 的 `applyPatch` 中更新锚点字符串。

---

## 四、升级 PDF.js 的完整步骤

1. 到 https://github.com/mozilla/pdf.js/releases 查看最新稳定版（当前 v6.2.108）。
2. 修改 `scripts/build-viewer.mjs` 顶部的 `PDFJS_VERSION = "6.2.108"` 为新版本号。
3. 同步修改 `scripts/scan-pdfs.mjs` 中的 `pdfjs_version: "6.2.108"` 字段。
4. 本地运行 `node scripts/build-viewer.mjs` 重新生成 viewer（下载、精简、自动打补丁）。
   - 若脚本打印 `WARNING: … anchor not found`，说明上游改动了补丁锚点——按第三节人工适配 `applyPatch` 的锚点字符串后重跑。
5. 本地起服务验证：`python3 -m http.server -d viewer`，打开
   `http://127.0.0.1:8000/web/viewer.html?file=<某个 raw PDF URL>`，确认渲染且无 origin 报错。
6. `git add` → `commit` → `push`，Actions 自动用新版本重新发布。

> 精简规则（删 source map、演示 PDF、debugger；locale 只留 en-US/zh-CN/zh-TW）已固化在
> `build-viewer.mjs`，无需手工处理。`cmaps/`、`iccs/`、`standard_fonts/`、`wasm/` 全部保留——
> cmaps 对中文 PDF 渲染必需，wasm 用于 JBIG2 / JPEG2000 / 色彩管理。

---

## 五、自动扫描脚本 `scripts/scan-pdfs.mjs`

- 无第三方依赖，仅用 Node 18+ 内置模块，本地与 Actions 均可直接运行。
- 递归识别 `.pdf` 与 `.PDF`，排除 `.git`、`node_modules`、`viewer/build`、`viewer/web`、
  CCS 构建输出目录（`Debug`/`Release`）等。
- 正确处理中文文件名、空格、特殊字符：`raw_url` 对路径逐段 `encodeURIComponent`，
  `viewer_url` 再整体 `encodeURIComponent`（双层编码）。
- 通过解析 `.gitattributes` 的 `filter=lfs` 规则检测 Git-LFS 文件，置 `lfs: true`。
- 输出 `viewer/pdf-index.json`，字段：`name` / `path` / `dir` / `size` / `size_human` /
  `lfs` / `raw_url` / `viewer_url` / `github_url`。
- 可用环境变量覆盖：`REPO_OWNER` / `REPO_NAME` / `REPO_BRANCH` / `PAGES_BASE_URL` /
  `SCAN_ROOT` / `OUTPUT`。

本地手动重生（调试用）：

```bash
node scripts/scan-pdfs.mjs
```

---

## 六、GitHub Actions 自动化

`.github/workflows/pdf-site.yml`：push 到 `main`（涉及 PDF / README / viewer / scripts / workflow 时）
自动：检出 → 安装 Node → 运行扫描脚本生成 `pdf-index.json` → 用 `actions/upload-pages-artifact`
打包 `viewer/` → `actions/deploy-pages` 发布到 GitHub Pages。

日常只需 `git add` → `git commit` → `git push`，在线文档中心即自动更新。

> Pages 部署源需在仓库 Settings → Pages 设为 **"GitHub Actions"**（首次推送后到设置页确认一次）。

---

## 七、已知限制

1. **Git-LFS 文件**：本仓库无 Git-LFS 跟踪文件，所有 PDF 均可通过 raw 正常获取。

2. **GitHub Pages 限制**：站点已限缩到 ~8 MB，无容量问题；但 Pages 带宽软上限 100 GB/月，
   若被大量抓取可能触发限流。PDF 本体不在 Pages，不受 Pages 容量限制。

3. **raw.githubusercontent.com 限制**：单文件 <100 MB 的非 LFS PDF 可正常获取；
   `accept-ranges: bytes` 支持，但较大 PDF（>50 MB）首次加载较慢，依赖浏览器分段缓存。
   本仓库最大 PDF 约 85 MB，在 100 MB 限制内。

4. **CORS**：raw 已发送 `Access-Control-Allow-Origin: *`，跨域读取正常；
   viewer 自带 CSP 为 `connect-src *`，不阻塞。

5. **AI 抓取可能受限**：raw.githubusercontent.com 与 GitHub API 均有匿名速率限制，
   大批量并发抓取可能被限流（HTTP 429）。建议加间隔与重试。

6. **浏览器兼容**：PDF.js v6 需要较新浏览器（近 2 年的 Chrome / Edge / Firefox / Safari）。
   老旧浏览器可改用 `pdfjs-<ver>-legacy-dist.zip` 替换 `build/` 与 `web/`。

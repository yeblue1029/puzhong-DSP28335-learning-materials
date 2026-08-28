# PDF 在线文档系统 · 维护说明

本文件说明仓库内 PDF 在线阅读系统的架构、升级方式与已知限制。
面向未来的维护者（包括人与 AI），请在修改 `viewer/`、`scripts/`、`.github/workflows/` 前先读完本文件。

---

## 一、架构总览

```
GitHub Repository (main 分支)
  └─ 原始 PDF（唯一一份，不复制、不移动、不重编码）
        │
        ├─► raw.githubusercontent.com  ─► Agent / 脚本 / curl
        │     （CORS * + HTTP Range，返回真实 PDF 二进制）
        │
        ├─► AI Extraction Pipeline（scripts/build-ai-docs.py，CI 内运行）
        │     每页：PyMuPDF embedded text → 稀疏判定 → 不足才 OCR 兜底
        │     ─► viewer/ai/  TXT / HTML / page TXT / block JSON / metadata
        │
GitHub Pages（viewer/ 整目录发布）
  ├─ index.html          PDF 文档中心（读取 pdf-index.json 渲染列表）
  ├─ pdf-index.json      由 scripts/scan-pdfs.mjs 自动生成的清单
  ├─ web/                Mozilla PDF.js 官方预构建 viewer（精简版）
  ├─ build/              pdf.mjs / pdf.worker.mjs / pdf.sandbox.mjs
  └─ ai/                 AI Reading Path（build-ai-docs.py 生成的派生文本）
        ├─ index.html    无 JS 依赖的静态文档列表（Web Chat AI 首选入口）
        ├─ index.json    机器入口（Agent / Script 用）
        ├─ AI_USAGE.txt  纯文本使用说明
        └─ docs/<doc_id>/ index.html（landing page）+ manifest.json
                          + full.txt + full.html
                          + pages/index.html + pages/0001.txt …
                          + blocks/index.html + blocks/0001.json …
        │
        ▼
  浏览器：index.html → 在线阅读链接 → web/viewer.html?file=<raw URL>
          PDF.js 通过 fetch 跨域读取 raw（CORS 已开启）→ canvas 渲染
  网页聊天 AI（ChatGPT/Gemini/DeepSeek）：README → AI_ACCESS.md
          → /ai/（静态 HTML）→ 文档 landing page → full.txt / pages / blocks
          （沿真实 <a href> 逐页点击，不要求自行拼接 URL）
```

**三种访问路径（务必区分）**

| 路径 | 入口 | 说明 |
| --- | --- | --- |
| Human | `viewer/index.html` → PDF.js | 人工阅读，体验不变 |
| Web Chat AI | README → `AI_ACCESS.md` → `/ai/`（静态 HTML）→ 文档 landing page → full.txt / pages / blocks | 网页聊天 AI 无法可靠读 raw PDF / 执行 PDF.js，也可能无法从 JSON 构造 URL 并 fetch，因此走「真实 HTML hyperlink 导航 + 派生文本层」 |
| Agent / Script | `/ai/index.json`（机器接口）或 `raw.githubusercontent.com` 原始 PDF | 有任意 HTTP fetch / 二进制下载 + 本地 PDF parser 的环境直接解析源头 |

**关键设计决策**

- **PDF 原文件只存一份**：仓库 ~445 MB，PDF 本体不复制进 Pages，
  也不为 AI 再提交一套 PDF 副本。
- **Pages 只发布 viewer + index + ai 派生文本**：PDF 经 `raw.githubusercontent.com` 读取；
  AI 派生文本由 CI 每次部署时从原始 PDF 重建（`viewer/ai/` 不进 Git history）。
- **原始 PDF 是唯一 Source of Truth**：所有派生文本可经
  `manifest.source_sha256` 追溯到对应原始 PDF；构建脚本对 PDF 只读。
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
  build-ai-docs.py    AI Reading Path：从原始 PDF 生成派生 TXT/HTML/JSON
                      （PyMuPDF + 本地 Tesseract；原生文字优先，OCR 仅兜底）
  verify-ai-docs.py   验证 viewer/ai 输出（JSON/链接/页数/UTF-8/LFS 防护）
AI_ACCESS.md          仓库级 AI 访问契约（Web Chat AI 发现路径的锚点）
.github/workflows/
  pdf-site.yml        构建 viewer → 扫描 → 构建 AI 文档 → 验证 → 发布 Pages
```

由构建脚本生成的文件（**不提交**，见 `.gitignore`，CI 与本地各自动生成）：

```
viewer/build/         PDF.js 核心库（pdf.mjs / pdf.worker.mjs / pdf.sandbox.mjs）
viewer/web/           PDF.js 官方 viewer（viewer.html / viewer.mjs[含补丁] / viewer.css
                      + images/ locale/ cmaps/ iccs/ standard_fonts/ wasm/）
viewer/LICENSE        PDF.js 的 Apache-2.0 许可
viewer/pdf-index.json 由 scan-pdfs.mjs 生成的 PDF 清单
viewer/ai/            AI Reading Path 全部派生产物（index.json / index.html /
                      AI_USAGE.txt / build-report.json / docs/<doc_id>/…）
.ai-cache/            本地/CI 的每文档 OCR 缓存（不入库）
```

> 因此仓库**不包含**任何 PDF.js 二进制，也不包含 AI 派生文本——克隆后运行
> `node scripts/build-viewer.mjs` 与 `python3 scripts/build-ai-docs.py`
> 即可复现与线上完全一致的站点。

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

## 五点五、AI Reading Path（`scripts/build-ai-docs.py`）

网页聊天 AI（ChatGPT / Gemini / DeepSeek 等）能打开 GitHub、读 HTML/TXT，
但可能无法可靠读取 raw PDF 二进制，无法执行 PDF.js 取得正文，也**可能无法
从 JSON 字符串自行构造 URL 并发起 fetch**（Web Chat 工具对机器接口 URL 有
safe-to-open / Internal Error 类限制）。因此本仓库提供一套**派生文本层 +
静态 HTML hyperlink 导航**：CI 从原始 PDF 自动生成网页聊天 AI 容易读取的
TXT / HTML / page TXT / block JSON / metadata，并把全部入口组织成真实
`<a href>` 链接链。

**发现链路（Web Chat AI，HTML-first hyperlink 导航）**：

```text
GitHub repository → README.md（🤖 Agent / LLM 章节）
→ AI_ACCESS.md（仓库根目录，AI 访问契约）
→ /ai/（静态 HTML 文档列表，入口 URL 为真实 Markdown hyperlink）
→ 点击文档标题 → docs/<doc_id>/index.html（landing page）
→ full.txt / full.html / pages/index.html / blocks/index.html
→ 点击目标页链接 → pages/NNNN.txt / blocks/NNNN.json
（每一跳的 URL 都来自上一页真实 <a href>，不要求自行拼接）
```

**Agent / Script 链路（机器接口）**：`/ai/index.json`（含每文档全部绝对 URL）
或 `raw.githubusercontent.com` 原始 PDF，适用于支持任意 HTTP fetch /
二进制下载 / 本地 PDF parser 的环境。

**每页提取策略（Native Text First + OCR Fallback）**：

```text
PDF page → PyMuPDF embedded text → 稀疏判定（有意义字符 < 24，阈值可调）
  ├── 足够      → TEXT_SOURCE: embedded（PDF 内文字对象直接提取）
  └── 不足/无文字 → 渲染 300 DPI PNG → 本地 Tesseract（chi_sim+eng）
        ├── OCR 更优 → TEXT_SOURCE: ocr
        └── 未更优   → TEXT_SOURCE: mixed（保留内嵌文字）
两种来源均无文字 → TEXT_SOURCE: none；异常 → error
```

- **绝不无条件对全部页面 OCR**：只有稀疏页才渲染并 OCR；
  300 DPI 临时 PNG 用后即删，绝不发布（避免 Pages artifact 膨胀）。
- OCR 完全在 CI runner 内本地完成（`tesseract-ocr` + `tesseract-ocr-chi-sim`
  + `tesseract-ocr-eng`），**不调用云 OCR / 付费 API / 第三方上传服务**。
- **OCR 数据的证据等级**：embedded text 是从 PDF 内文字对象提取（可靠性最高）；
  OCR text 是从扫描图像机器识别得到，**不是"原文等价物"**。涉及芯片型号、引脚、
  寄存器、bit 位、地址、数字、公式、表格、原理图、程序代码的关键结论，
  当 `TEXT_SOURCE = ocr` 时应回原始 PDF 页面核验（`viewer_url` + 物理页码）。
  该警示同时写入 `AI_ACCESS.md` 与部署后的 `viewer/ai/AI_USAGE.txt`。
- **OCR blocks 坐标**：Tesseract TSV 行级块，从 300 DPI 像素坐标换算回
  PDF 点（原点左上角，与 PyMuPDF 一致），带 `block_source: "ocr"`，
  不伪造 embedded 坐标。
- **doc_id** = `SHA256(仓库相对 PDF 路径)[:16]`，稳定 URL safe；
  manifest 保留原中文文件名 / `source_path` / `source_sha256`。
- **页码**：所有 `PDF_PAGE` / `pages/NNNN.txt` 均为 PDF 物理页（1-based，
  即 PDF.js Viewer 页码），不是书籍页脚印刷页码。
- **Git-LFS 防护**：打开前校验文件存在、大小合理、`%PDF-` magic；
  内容是 LFS pointer 时标记 `lfs_not_materialized`，绝不把 pointer 当正文。
- **稀疏阈值**：`MIN_EMBEDDED_CHARS = 24`（脚本顶部常量，带注释可调）。
  取舍说明：封面 / 整页插图 / 目录装饰页不会被无脑 OCR 后假装正文可靠；
  例如《普中DSP28335开发攻略》16 个仅含页眉的插图页（~30 字符）保留 embedded。
- **缓存**（性能优化，非正确性前提）：key = 源 PDF SHA256 + extractor 版本 +
  OCR 配置；CI 用 `actions/cache`（`.ai-cache/`），restore 后未变更的文档直接
  复用上次产物。缓存 miss 时完整构建依然正确。

**输出结构**：

```
viewer/ai/
├── index.html            静态文档列表（HTML 源码即含核心信息，无 JS 依赖；
│                         每文档标题链接 → docs/<doc_id>/index.html landing）
├── index.json            机器入口（schema_version=1 / documents[] / 绝对 URL）
├── AI_USAGE.txt          纯文本使用说明（HTML-first 导航 + TEXT_SOURCE 语义）
├── build-report.json     构建真实统计（PDF 数 / 页数 / OCR 耗时 / 体积 / 缓存命中）
└── docs/<doc_id>/
    ├── index.html        landing page（标题 / doc_id / 页数 / 状态 / SHA256
    │                     + 全部入口真实链接：full / pages / blocks / manifest /
    │                     GitHub / raw / Viewer，无 JS）
    ├── manifest.json     元数据（SHA256 / 页数 / 来源统计 / 引擎版本 / 状态）
    ├── full.txt          全文（PDF_PAGE 分隔 + TEXT_SOURCE 标记）
    ├── full.html         静态 HTML 全文（anchor: #pdf-page-NNNN，无 JS；
    │                     每页页头附 Page TXT / Blocks JSON 真实链接）
    ├── pages/index.html  页目录：0001.txt … NNNN.txt 全部为真实链接
    ├── pages/0001.txt    每物理页一个 TXT（页级读取：当前/前/后页）
    ├── blocks/index.html 块目录：0001.json … NNNN.json 全部为真实链接
    └── blocks/0001.json  每页版面块（bbox + 文本 + block_source）
```

**HTML 导航文件的缓存语义**：`landing / pages 目录 / blocks 目录 / full.html`
由 `regenerate_nav_files()` 在**每次构建**时重新生成（缓存命中时从已落盘的
`pages/*.txt` 解析重建），因此更新 HTML 模板**不需要**递增
`EXTRACTOR_VERSION`、不会使 OCR 缓存失效（纯导航模板变化 ≠ 提取行为变化）。

**验证**：`python3 scripts/verify-ai-docs.py` 检查 JSON 语法、链接、页数一致、
必需文件、UTF-8、SHA256、`%PDF-`、LFS pointer、extraction status 一致性、
URL 卫生（不引用本地路径）、index.html 静态源码完整性，以及**导航图验证
（12 A–H）**：README / AI_ACCESS / viewer 首页入口链接为真实静态 hyperlink、
每文档 landing / pages / blocks 目录页链接齐全且目标存在、full.html 页级
链接齐全。失败即退出码 1，CI 会阻断部署。

**链接链验收**：`python3 scripts/test-ai-linkchain.py`（CI 部署后自动运行，
也可本地运行）模拟 Web Chat AI 导航：从 `/ai/` 出发，每一跳 URL 均从上一页
真实 `<a href>` 解析，禁止自行拼接 doc_id / 页号；默认对三本 DSP 专项书做
全链验收（普中开发攻略第14章检索 / 手把手 page 0148 / C和指针 doc_id 实查）。

本地手动重建（调试用，需要 `pip install pymupdf` 与本地 tesseract）：

```bash
python3 scripts/build-ai-docs.py       # 全仓库
AI_LIMIT=5 python3 scripts/build-ai-docs.py            # 只处理前 5 个（测性能）
AI_DOCS_ONLY="手把手教你学DSP：基于TMS320F28335.pdf" python3 scripts/build-ai-docs.py
python3 scripts/verify-ai-docs.py      # 验证
```



## 六、GitHub Actions 自动化

`.github/workflows/pdf-site.yml`：push 到 `main`（涉及 PDF / README / AI_ACCESS / viewer / scripts / workflow 时）
自动：检出 → 安装 Node → 运行扫描脚本生成 `pdf-index.json`
→ 恢复 `.ai-cache` → 安装 Python + PyMuPDF + Tesseract（chi_sim + eng）
→ `scripts/build-ai-docs.py` 生成 `viewer/ai/` → `scripts/verify-ai-docs.py` 验证
→ 用 `actions/upload-pages-artifact` 打包 `viewer/`（含 `ai/`）
→ `actions/deploy-pages` 发布到 GitHub Pages
→ `scripts/test-ai-linkchain.py` 对刚部署的站点做真实 hyperlink 链验收
（每一跳 URL 均从上一页 `<a href>` 解析，三本 DSP 专项书全链）。

日常只需 `git add` → `git commit` → `git push`，在线文档中心即自动更新。

> Pages 部署源需在仓库 Settings → Pages 设为 **"GitHub Actions"**（首次推送后到设置页确认一次）。

---

## 七、已知限制

1. **Git-LFS 文件**：本仓库无 Git-LFS 跟踪文件，所有 PDF 均可通过 raw 正常获取。

2. **GitHub Pages 限制**：PDF.js viewer 部分已限缩到 ~8 MB；新增 `viewer/ai/`
   派生文本后站点总体积约数十 MB（远低于 Pages 1 GB artifact 上限），
   但 Pages 带宽软上限 100 GB/月，若被大量抓取可能触发限流。
   PDF 本体不在 Pages，不受 Pages 容量限制。

3. **raw.githubusercontent.com 限制**：单文件 <100 MB 的非 LFS PDF 可正常获取；
   `accept-ranges: bytes` 支持，但较大 PDF（>50 MB）首次加载较慢，依赖浏览器分段缓存。
   本仓库最大 PDF 约 85 MB，在 100 MB 限制内。

4. **CORS**：raw 已发送 `Access-Control-Allow-Origin: *`，跨域读取正常；
   viewer 自带 CSP 为 `connect-src *`，不阻塞。

5. **AI 抓取可能受限**：raw.githubusercontent.com 与 GitHub API 均有匿名速率限制，
   大批量并发抓取可能被限流（HTTP 429）。建议加间隔与重试。

6. **浏览器兼容**：PDF.js v6 需要较新浏览器（近 2 年的 Chrome / Edge / Firefox / Safari）。
   老旧浏览器可改用 `pdfjs-<ver>-legacy-dist.zip` 替换 `build/` 与 `web/`。

7. **AI 派生文本的证据等级**：`TEXT_SOURCE: embedded` 等同 PDF 原生文字；
   `TEXT_SOURCE: ocr` 为 Tesseract 机器识别扫描图像，**不是"原文等价物"**，
   可能存在识别误差（尤其中文标点、相似字形、表格线、公式、原理图中的文字）。
   涉及芯片型号 / 引脚 / 寄存器 / bit 位 / 地址 / 数字 / 公式 / 表格 / 原理图 /
   程序代码的关键结论，应回原始 PDF 页面核验。

8. **OCR 构建耗时**：首次全仓库构建需对约 2000+ 扫描/稀疏页做本地 OCR
   （约 1~2 小时量级，视 runner 而定），之后命中 `.ai-cache` 的文档秒级复用；
   Actions 单 job 上限 6 小时，当前余量充足。若未来 PDF 数量大幅增长，
   需重新测量并考虑分片并行，而不是悄悄删功能。

9. **稀疏阈值取舍**：`MIN_EMBEDDED_CHARS = 24` 意味着"只有页眉/页码的插图页"
   （如《普中开发攻略》16 个 ~30 字符页）保留 embedded 而不 OCR——
   有意为之，避免把图片页 OCR 后假装正文可靠；页面真实字符数在
   blocks JSON（`embedded_char_count`）与 manifest 中可见。

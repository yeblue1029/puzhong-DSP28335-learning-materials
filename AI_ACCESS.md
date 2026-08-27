# AI_ACCESS.md — 本仓库 AI / LLM 文档读取契约

> 本文件面向首先访问本 GitHub 仓库的网页聊天 AI（ChatGPT / Gemini / DeepSeek 等）
> 与自动化脚本，说明读取本仓库 PDF 内容的正确路径。
> 人工阅读方式不受影响，见 README.md。

## 一句话规则

**Web Chat AI 读取本仓库 PDF 时，不要默认优先访问 `raw.githubusercontent.com`，
先读取机器入口 `index.json`：**

```
https://yeblue1029.github.io/puzhong-DSP28335-learning-materials/ai/index.json
```

它是无需 JavaScript 即可直接 HTTP GET 的纯 JSON，包含全部 PDF 的
派生文本 URL 与元数据。

## 三种访问方式

| 访问者 | 推荐路径 | 说明 |
| --- | --- | --- |
| **Human（人工）** | PDF.js 在线阅读器<br>`https://yeblue1029.github.io/puzhong-DSP28335-learning-materials/` | 翻页 / 缩放 / 搜索 / 缩略图，体验不变 |
| **Web Chat AI**<br>（ChatGPT / Gemini / DeepSeek 等） | `/ai/index.json` → 派生 TXT / HTML / JSON | 普通网页聊天 AI 可能无法可靠读取 raw PDF 二进制或执行 PDF.js，因此提供纯文本派生层 |
| **Agent / Script** | 原始 PDF：`raw.githubusercontent.com`<br>（见 index.json 的 `original_raw_url`） | 环境真实支持下载二进制 + 本地文件系统 + PDF parser 时，直接解析原始 PDF |

## Web Chat AI 推荐流程

1. 读取 `index.json`（上述机器入口）。
2. 根据用户提到的书名，用 `title` / `display_title` / `filename` /
   `source_path` / `match_key` 定位文档。
   用户可能只说「手把手教你学 DSP：基于 TMS320F28335」这类不完全一致的名称；
   `match_key` 已做 NFKC 归一 + casefold + 去空白，可直接匹配。
   不要用生成式 AI 自行创造别名。
3. 读取整本：`ai_full_text_url`（full.txt，带 PDF_PAGE 分隔与 TEXT_SOURCE 标记）。
   文档很大时改用页级读取：`ai_pages_base_url` + 4 位补零页号
   （如 `0148.txt`）。命中目标后通常只需读 当前页 / 前一页 / 后一页。
4. 精确页查询：`ai_pages_base_url`（每 PDF 物理页一个 TXT）。
5. 版面位置查询：`ai_blocks_base_url`（每页 block/bbox JSON；
   坐标为 PDF 点、原点页面左上角；OCR 块带 `block_source: "ocr"`，
   不与 embedded 坐标混淆）。
6. 需要原始证据 / 人工核验时，再查看 `manifest_url`（含 `source_sha256`）、
   `original_github_url`、`original_raw_url`、`viewer_url`。

页码约定：所有 `PDF_PAGE` / `pages/0001.txt` 均为 **PDF 物理页（1-based）**，
即 PDF.js Viewer 显示的页码；不是书籍页脚印刷页码。

## 文本来源等级（重要）

每个页文件与 blocks JSON 都带有 `TEXT_SOURCE` 标记：

| TEXT_SOURCE | 含义 | 可靠性 |
| --- | --- | --- |
| `embedded` | 从 PDF 内文字对象直接提取 | 最高，等同 PDF 原生文字 |
| `ocr` | 页面无足够内嵌文字，由本地 Tesseract（chi_sim+eng，300 DPI）识别扫描图像所得 | ⚠️ 机器识别文本，**不是"原文等价物"**，可能有识别误差 |
| `mixed` | 内嵌文字稀疏且 OCR 未更优，保留内嵌文字 | 同 embedded，但文字量少 |
| `none` | 内嵌与 OCR 均无文字（纯图片页/空白页） | 无文本 |
| `error` | 提取异常 | 无文本，见 manifest 的 error_pages |

**OCR 证据等级警示**：当 `TEXT_SOURCE = ocr` 时，涉及
芯片型号、引脚、寄存器、bit 位、地址、数字、公式、表格、原理图、程序代码
的关键结论，应回原始 PDF 页面核验（用 `viewer_url` 打开对应物理页），
不要把 OCR 结果无条件当作精确 transcription。

文档级 `extraction_status`：`ok` / `partial` / `text_sparse` /
`invalid_pdf` / `lfs_not_materialized` / `ocr_failed` / `error`。

## 失败规则（必须遵守）

如果出现以下情况，**必须明确、如实报告**，不得用互联网同名资料、
外部 PDF 或 AI 摘要冒充本仓库 PDF 原文：

- AI 派生文本不存在（404）；
- `extraction_status` 异常（`invalid_pdf` / `lfs_not_materialized` / `error` 等）；
- OCR 失败或文本为空；
- 文件不是有效 PDF（缺少 `%PDF-` 头）；
- 文件是 Git-LFS pointer（`version https://git-lfs.github.com/spec/v1`，
  此时 raw 返回的不是 PDF 正文）。

## Agent / Script 说明

如果你的运行环境真实支持：下载二进制文件、本地文件系统、PDF parser
（如 PyMuPDF / pdfplumber），则可以直接解析原始 PDF
（index.json 中每个文档的 `original_raw_url`，非 LFS 文件返回真实 PDF 二进制，
CORS 已开启、支持 Range 请求）。这比派生文本更接近源头。

## 派生层的生成与维护

- 派生文本由 `scripts/build-ai-docs.py` 在 GitHub Actions 中自动生成，
  部署于 `viewer/ai/`，随现有 GitHub Pages 一起发布（不新增第二套网站）。
- 原始 PDF 是唯一 Source of Truth：构建脚本只读原始 PDF，
  不修改、不移动、不重编码、不上传副本。
- `doc_id = SHA256(仓库相对 PDF 路径)[:16]`，稳定且 URL safe；
  manifest 中保留原中文文件名、`source_path` 与 `source_sha256`。
- 缓存 key = `source PDF SHA256 + extractor 版本 + OCR 配置`；
  缓存未命中时完整构建依然正确（缓存只是性能优化，不是正确性前提）。
- 使用与验证说明见 `viewer/ai/AI_USAGE.txt`（部署后）与
  `viewer/MAINTENANCE.md`（维护文档）。

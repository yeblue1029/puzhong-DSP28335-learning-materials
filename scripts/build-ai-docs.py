#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build-ai-docs.py — 从仓库原始 PDF 生成"网页聊天 AI 可直接读取"的派生文本表示。

核心原则：
  - 原始 PDF 是唯一 Source of Truth：本脚本不修改、不移动、不重编码任何 PDF，
    只生成 TXT / HTML / page TXT / block JSON / metadata 派生文件。
  - Native Text First + OCR Fallback：每页先提取 PDF 内嵌文字（embedded text），
    仅当内嵌文字"稀疏"（见下方阈值）时才渲染该页并交给本地 Tesseract OCR。
    绝不对全部页面无条件 OCR。
  - 每页文本来源必须标记（embedded / ocr / mixed / none / error），
    OCR 文本不是"原文等价物"，关键结论需回原始 PDF 核验。

输出目录（全部为构建产物，不提交进 main Git history，见 .gitignore）：
  viewer/ai/
    index.html          无 JS 依赖的静态文档列表（HTML 源码即含核心信息）
    index.json          机器入口：schema_version / repository / documents[...]
    AI_USAGE.txt        纯文本使用说明（给网页聊天 AI）
    build-report.json   本次构建的真实统计（PDF 数、页数、OCR 耗时、体积）
    docs/<doc_id>/
      manifest.json     文档级提取元数据（SHA256、页数、来源统计、引擎版本）
      full.txt          全文（含 PDF_PAGE 分隔与 TEXT_SOURCE 标记）
      full.html         静态 HTML 全文（anchor: #pdf-page-NNNN）
      pages/0001.txt    每物理页一个 TXT（1-based，PDF Viewer 实际页码）
      blocks/0001.json  每页版面块（bbox + 文本，block_source 标记来源）

doc_id 规则：SHA256(仓库相对路径的 POSIX 规范形式) 的前 16 个十六进制字符，
URL safe 且稳定 —— 同一 PDF 路径重复构建必然得到相同 doc_id（不用随机 UUID）。

运行（本地或 GitHub Actions，无必需参数）：
  python3 scripts/build-ai-docs.py

可选环境变量：
  REPO_OWNER / REPO_NAME / REPO_BRANCH   — 生成绝对 URL 用（默认 yeblue1029 / puzhong-DSP28335-learning-materials / main）
  PAGES_BASE_URL                         — Pages 站点根（默认 https://<owner>.github.io/<name>）
  GIT_COMMIT                             — 提交 SHA（CI 传 GITHUB_SHA；本地默认读 git rev-parse）
  AI_OCR_DPI            (默认 300)       — OCR 渲染 DPI
  AI_OCR_LANG           (默认 chi_sim+eng)
  AI_MIN_EMBEDDED_CHARS (默认 24)        — 稀疏页判定阈值（见下）
  AI_WORKERS            (默认 min(4, cpu)) — 并行 worker 数
  AI_LIMIT              (默认 0=全部)    — 只处理前 N 个 PDF（性能测量用）
  AI_DOCS_ONLY          (默认 空)        — 逗号分隔的 source_path 白名单（测试用）
  AI_CACHE_DIR          (默认 关闭)      — 每文档缓存目录（key = source SHA256 + extractor 版本 + OCR 配置）
  AI_ROOT               (默认 脚本上级目录) — 仓库根
  AI_OUT_DIR            (默认 <root>/viewer/ai) — 输出目录
"""

import hashlib
import html as html_mod
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.parse
from concurrent.futures import ProcessPoolExecutor

# ---------------------------------------------------------------- 配置常量 --
# 稀疏页启发式阈值（可调整，务必保留注释）：
#   一页的 embedded text 中"有意义的字符"（Unicode 字母/数字/CJK，非空白、非纯标点）
#   少于 AI_MIN_EMBEDDED_CHARS 个，即判定内嵌文字不足，触发 OCR fallback。
#   阈值取 24 的理由：
#     - 覆盖"完全无文字"的扫描页（0 字符）；
#     - 覆盖"只有页眉/页码/水印"的图片页（典型 10~45 字符，例如
#       《普中DSP28335开发攻略》的整页插图页约 30 字符页眉）；
#     - 同时避免把正常的封面、目录装饰页、图表页无脑 OCR 之后
#       假装正文非常可靠（spec §11 明确禁止）。
#   注意：本仓库实测《普中开发攻略》有 16 个仅含页眉的插图页（~30 字符），
#   它们 > 24 阈值，被保留为 embedded（不 OCR）——这是有意的取舍，
#   页面真实字符数在 blocks/manifest 中可见，AI 可自行判断可信度。
MIN_EMBEDDED_CHARS = int(os.environ.get("AI_MIN_EMBEDDED_CHARS", "24"))

OCR_DPI = int(os.environ.get("AI_OCR_DPI", "300"))
OCR_LANG = os.environ.get("AI_OCR_LANG", "chi_sim+eng")
OCR_TIMEOUT = int(os.environ.get("AI_OCR_TIMEOUT", "180"))  # 单页 OCR 秒数
OCR_MAX_EDGE_PX = int(os.environ.get("AI_OCR_MAX_EDGE_PX", "2600"))  # OCR 渲染长边像素上限
WORKERS = int(os.environ.get("AI_WORKERS", "0")) or min(4, os.cpu_count() or 1)
DOC_ID_LEN = 16          # SHA256 路径哈希前缀长度（URL safe hex）
PAGE_NUM_WIDTH = 4       # pages/0001.txt 补零宽度（固定 4 位，URL 稳定）
EXTRACTOR_VERSION = "1.1.0"   # 缓存 key 的一部分；行为变更时必须递增
# 1.1.0：OCR 改为单次 TSV 调用重建文本（行为变更，缓存需失效）；
#        新增 OCR_MAX_EDGE_PX 自适应像素上限；OMP_THREAD_LIMIT=1。

REPO_ROOT = os.environ.get("AI_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.environ.get("AI_OUT_DIR") or os.path.join(REPO_ROOT, "viewer", "ai")
CACHE_DIR = os.environ.get("AI_CACHE_DIR") or ""

REPO_OWNER = os.environ.get("REPO_OWNER", "yeblue1029")
REPO_NAME = os.environ.get("REPO_NAME", "puzhong-DSP28335-learning-materials")
REPO_BRANCH = os.environ.get("REPO_BRANCH", "main")
PAGES_BASE_URL = (os.environ.get("PAGES_BASE_URL")
                  or f"https://{REPO_OWNER}.github.io/{REPO_NAME}").rstrip("/")

# 与 scripts/scan-pdfs.mjs 保持一致的目录排除规则
EXCLUDE_DIRS = {".git", "node_modules", "_github_worktree",
                "_github_extract_staging", "_github_upload_logs",
                ".github_upload_logs", "_github_scan", ".vscode", ".idea",
                ".vs", ".trae", "AI_REPO_INDEX", ".ai-cache"}
EXCLUDE_VIEWER_ASSET_PREFIXES = ("viewer/build", "viewer/web", "viewer/ai")
BUILD_OUTPUT_DIRS = {"Debug", "Release"}

try:
    import pymupdf  # PyMuPDF >= 1.24 推荐的新导入名
    PYMUPDF_VERSION = getattr(pymupdf, "__version__", "unknown")
except ImportError:  # 兼容旧版本的 fitz 导入名
    import fitz as pymupdf
    PYMUPDF_VERSION = getattr(pymupdf, "__version__",
                              getattr(pymupdf, "VersionBind", "unknown"))

# ---------------------------------------------------------------- 小工具 --

def to_posix(path: str) -> str:
    return path.replace(os.sep, "/")


def meaningful_chars(text: str) -> int:
    """统计"有意义的字符"：Unicode 字母 / 数字（含 CJK）。
    排除空白与纯标点，避免 '......' 或页码装饰被误判为正文。"""
    n = 0
    for ch in text:
        cat = unicodedata.category(ch)
        if cat[0] in ("L", "N"):
            n += 1
    return n


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_doc_id(source_path: str) -> str:
    """stable doc_id = SHA256(POSIX 规范化仓库相对路径)[:16]。同一 PDF 路径
    重复构建必然得到相同 id（不依赖文件内容 / 随机数）。"""
    norm = to_posix(source_path).lstrip("/")
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:DOC_ID_LEN]


def page_name(pno1: int) -> str:
    return f"{pno1:0{PAGE_NUM_WIDTH}d}"


def encode_repo_path(path: str) -> str:
    return "/".join(urllib.parse.quote(seg, safe="") if seg else ""
                    for seg in path.split("/"))


def normalize_match_key(stem: str) -> str:
    """标题匹配键：NFKC 归一 + casefold + 去掉全部空白。
    用于"用户只说《手把手教你学 DSP：基于 TMS320F28335》"这类不完全一致输入。"""
    s = unicodedata.normalize("NFKC", stem).casefold()
    return re.sub(r"\s+", "", s)


def git_commit() -> str:
    for env in ("GIT_COMMIT", "GITHUB_SHA"):
        if os.environ.get(env):
            return os.environ[env]
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "unknown"


def tesseract_version() -> str:
    try:
        out = subprocess.run(["tesseract", "--version"], capture_output=True,
                             text=True, timeout=15)
        for line in (out.stdout + out.stderr).splitlines():
            if line.lower().startswith("tesseract"):
                return line.split()[-1]
    except Exception:
        pass
    return "unavailable"


# ------------------------------------------------------- 页级提取（worker）--
# ProcessPoolExecutor 的每个 worker 进程内部缓存"当前打开的 PDF"，
# 避免每页重复打开大文件（85 MB 的书打开一次即可）。
_worker_doc = {"path": None, "doc": None}


def _get_doc(path: str):
    if _worker_doc["path"] != path:
        if _worker_doc["doc"] is not None:
            try:
                _worker_doc["doc"].close()
            except Exception:
                pass
        _worker_doc["doc"] = pymupdf.open(path)
        _worker_doc["path"] = path
    return _worker_doc["doc"]


def _ocr_page_image(page, dpi: int):
    """渲染 PDF 页为临时 PNG 并返回 (路径, 实际 zoom)。

    自适应像素上限：长边超过 OCR_MAX_EDGE_PX（默认 2600px，约 A4@218DPI）
    的超大页面会按比例缩小。本仓库存在 1663×2229pt 的超大扫描页，
    按 300 DPI 渲染达 6930×9290px ≈ 6400 万像素，tesseract 单页耗时
    超过 5 分钟且极易 OOM；缩到长边 2600px 后单页 OCR 约 15~30 秒，
    识别质量对正文级文本无可感知差异。返回实际 zoom 供 bbox 换算。"""
    zoom = dpi / 72.0
    w = page.rect.width * zoom
    h = page.rect.height * zoom
    longest = max(w, h)
    if longest > OCR_MAX_EDGE_PX:
        zoom = zoom * (OCR_MAX_EDGE_PX / longest)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    fd, png = tempfile.mkstemp(suffix=".png", prefix="aiocr_")
    os.close(fd)
    pix.save(png)
    return png, zoom


def _tesseract_env():
    """tesseract 4.x 默认用 OpenMP 多线程，实测单页 13.4s；限制为单线程后
    单页仅 4.8s（本机 3 核实测，CI 4 核同理）。因为脚本按页并行调用多个
    tesseract 进程，每个进程单线程反而整体吞吐最高。"""
    env = dict(os.environ)
    env.setdefault("OMP_THREAD_LIMIT", "1")
    return env


def _tesseract_plain(png: str, lang: str) -> str:
    r = subprocess.run(["tesseract", png, "stdout", "-l", lang, "--psm", "3"],
                       capture_output=True, text=True, timeout=OCR_TIMEOUT,
                       env=_tesseract_env())
    if r.returncode != 0:
        raise RuntimeError(f"tesseract rc={r.returncode}: {r.stderr[:200]}")
    return r.stdout


def _tesseract_tsv(png: str, lang: str) -> str:
    r = subprocess.run(["tesseract", png, "stdout", "-l", lang, "--psm", "3",
                        "tsv"], capture_output=True, text=True,
                       timeout=OCR_TIMEOUT, env=_tesseract_env())
    if r.returncode != 0:
        raise RuntimeError(f"tesseract tsv rc={r.returncode}: {r.stderr[:200]}")
    return r.stdout


def extract_page(pdf_path: str, pno0: int):
    """提取单页。返回 dict：
    {pno0, text, source, embedded_chars, ocr_chars, ocr_seconds,
     blocks, page_w, page_h, ocr_attempted, ocr_error}
    source ∈ embedded / ocr / mixed / none / error（语义见 AI_USAGE.txt）。"""
    out = {"pno0": pno0, "text": "", "source": "error", "embedded_chars": 0,
           "ocr_chars": 0, "ocr_seconds": 0.0, "blocks": [], "page_w": 0.0,
           "page_h": 0.0, "ocr_attempted": False, "ocr_error": None}
    png = None
    try:
        doc = _get_doc(pdf_path)
        page = doc[pno0]
        out["page_w"] = round(float(page.rect.width), 2)
        out["page_h"] = round(float(page.rect.height), 2)

        # ---- 1) native embedded text ----
        raw = page.get_text("text")
        emb_n = meaningful_chars(raw)
        out["embedded_chars"] = emb_n

        if emb_n >= MIN_EMBEDDED_CHARS:
            out["source"] = "embedded"
            out["text"] = raw.strip()
            for b in page.get_text("blocks"):
                if b[6] == 0 and b[4].strip():  # 仅文字块
                    out["blocks"].append({
                        "bbox": [round(float(b[0]), 2), round(float(b[1]), 2),
                                 round(float(b[2]), 2), round(float(b[3]), 2)],
                        "text": b[4].rstrip("\n"),
                        "block_source": "embedded",
                    })
            return out

        # ---- 2) sparse → OCR fallback ----
        # 只调用一次 tesseract（TSV 输出），同时得到纯文本与版面块：
        # 相比"plain + tsv 各跑一次"省一半 OCR 时间（全仓 2933 个稀疏页时
        # 节省约 1 小时以上），文本与 plain 输出同源同引擎，字符数实测一致。
        out["ocr_attempted"] = True
        png, actual_zoom = _ocr_page_image(page, OCR_DPI)
        t0 = time.time()
        tsv = _tesseract_tsv(png, OCR_LANG)
        out["ocr_seconds"] = round(time.time() - t0, 2)
        ocr_text, ocr_blocks = _tsv_to_text_and_blocks(tsv, actual_zoom)
        ocr_n = meaningful_chars(ocr_text)
        out["ocr_chars"] = ocr_n

        if ocr_n > emb_n:
            out["source"] = "ocr"
            out["text"] = ocr_text.strip()
            # OCR blocks：行级块；bbox 从渲染像素坐标换算回 PDF 点坐标
            # （除以实际 zoom，超大页面会被 OCR_MAX_EDGE_PX 缩小），
            # 明确标记 block_source=ocr，不伪装成 embedded 坐标。
            out["blocks"] = ocr_blocks
        elif emb_n > 0:
            # OCR 没有比 embedded 更好（如装饰页），保留 native 文字，标记 mixed
            out["source"] = "mixed"
            out["text"] = raw.strip()
            for b in page.get_text("blocks"):
                if b[6] == 0 and b[4].strip():
                    out["blocks"].append({
                        "bbox": [round(float(b[0]), 2), round(float(b[1]), 2),
                                 round(float(b[2]), 2), round(float(b[3]), 2)],
                        "text": b[4].rstrip("\n"),
                        "block_source": "embedded",
                    })
        else:
            out["source"] = "none"   # 两种来源都没有文字（如纯图片/空白页）
        return out

    except Exception as e:
        out["source"] = "error"
        out["ocr_error"] = str(e)[:300]
        return out
    finally:
        if png and os.path.exists(png):
            try:
                os.unlink(png)   # 临时 OCR 图片绝不发布（spec §26）
            except Exception:
                pass


def _tsv_to_text_and_blocks(tsv: str, zoom: float):
    """把 tesseract TSV 解析为 (页面纯文本, 行级 blocks)。

    - blocks：按 TSV 的 (block, par, line) 聚合为行级块；
      bbox 像素坐标 → PDF 点坐标（除以实际 zoom），block_source=ocr。
    - 文本：按行拼接（行内按 x 排序；词间距 > 行高 1/4 时补一个空格，
      CJK 相邻不加空格），块之间空一行——与 tesseract plain 输出同源同引擎，
      仅空白约定略有差异（实测字符数一致）。
    """
    from collections import defaultdict
    groups = defaultdict(list)
    for line in tsv.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 12 or parts[0] != "5":
            continue
        try:
            conf = float(parts[10])
        except ValueError:
            conf = -1.0
        if conf < 0:      # tesseract 对无置信度词条输出 -1，跳过
            continue
        key = (int(parts[2]), int(parts[3]), int(parts[4]))  # block/par/line
        groups[key].append({
            "x": int(parts[6]), "y": int(parts[7]),
            "w": int(parts[8]), "h": int(parts[9]),
            "text": parts[11], "conf": conf,
        })
    blocks = []
    text_lines = []
    last_block = None
    cjk_re = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\u3040-\u30ff]")
    for key in sorted(groups):
        words = groups[key]
        words = [w for w in words if w["text"].strip()]
        if not words:
            continue
        words.sort(key=lambda w: w["x"])
        texts = [w["text"] for w in words]
        # ---- 行内拼接（gap 感知空格）----
        line_h = max(w["h"] for w in words) or 1
        joined = texts[0]
        for i in range(1, len(words)):
            prev, cur = words[i - 1], words[i]
            gap = cur["x"] - (prev["x"] + prev["w"])
            if gap > line_h * 0.25 and not (
                    cjk_re.search(joined[-1] or " ") or
                    cjk_re.search(cur["text"][0] or " ")):
                joined += " "
            joined += cur["text"]
        # ---- 文本行序列：换 block 时补一个空行 ----
        if last_block is not None and key[0] != last_block:
            text_lines.append("")
        text_lines.append(joined)
        last_block = key[0]
        # ---- 行级 block ----
        x0 = min(w["x"] for w in words)
        y0 = min(w["y"] for w in words)
        x1 = max(w["x"] + w["w"] for w in words)
        y1 = max(w["y"] + w["h"] for w in words)
        conf = round(sum(w["conf"] for w in words) / len(words), 1)
        blocks.append({
            "bbox": [round(x0 / zoom, 2), round(y0 / zoom, 2),
                     round(x1 / zoom, 2), round(y1 / zoom, 2)],
            "text": joined,
            "block_source": "ocr",
            "confidence": conf,
        })
    return "\n".join(text_lines), blocks


# ---------------------------------------------------------------- 文档发现 --

def discover_pdfs():
    found = []
    for root, dirs, files in os.walk(REPO_ROOT):
        rel_root = to_posix(os.path.relpath(root, REPO_ROOT))
        parts = [] if rel_root == "." else rel_root.split("/")
        if any(p in EXCLUDE_DIRS for p in parts):
            dirs[:] = []
            continue
        if rel_root != ".":
            if any(rel_root == p or rel_root.startswith(p + "/")
                   for p in EXCLUDE_VIEWER_ASSET_PREFIXES):
                dirs[:] = []
                continue
            if any(p in BUILD_OUTPUT_DIRS for p in parts):
                dirs[:] = []
                continue
        dirs.sort()
        for fn in sorted(files):
            if fn.lower().endswith(".pdf"):
                rel = to_posix(os.path.relpath(os.path.join(root, fn), REPO_ROOT))
                found.append(rel)
    found.sort()
    return found


def validate_pdf(abs_path: str):
    """spec §20 LFS 防护：文件存在 / 大小合理 / %PDF- magic / 非 LFS pointer。"""
    if not os.path.isfile(abs_path):
        return "missing", 0
    size = os.path.getsize(abs_path)
    if size == 0:
        return "invalid_pdf", 0
    if size > 2 * 1024 ** 3:
        return "invalid_pdf", size
    with open(abs_path, "rb") as f:
        head = f.read(1024)
    if head.startswith(b"version https://git-lfs.github.com/spec/v1"):
        return "lfs_not_materialized", size   # 绝不把 pointer 当 PDF 正文
    if b"%PDF-" not in head:
        return "invalid_pdf", size
    return "ok", size


# ---------------------------------------------------------------- 输出生成 --

def page_txt_content(meta, pno1: int, text: str, source: str) -> str:
    lines = [
        f"DOCUMENT_TITLE: {meta['title']}",
        f"SOURCE_PATH: {meta['source_path']}",
        f"PDF_PAGE: {pno1}",
        f"PDF_PAGE_COUNT: {meta['pdf_page_count']}",
        f"SOURCE_SHA256: {meta['source_sha256']}",
        f"TEXT_SOURCE: {source}",
    ]
    if source == "ocr":
        lines.append(f"OCR_ENGINE: tesseract")
        lines.append(f"OCR_LANGUAGE: {OCR_LANG}")
        lines.append(f"OCR_DPI: {OCR_DPI}")
    if source == "mixed":
        lines.append("NOTE: embedded text kept; OCR attempted but did not improve")
    lines.append("")
    lines.append("========== PAGE_TEXT ==========")
    lines.append("")
    return "\n".join(lines) + text.strip() + "\n"


def full_txt_content(meta, pages) -> str:
    head = [
        f"DOCUMENT_TITLE: {meta['title']}",
        f"SOURCE_PATH: {meta['source_path']}",
        f"PDF_PAGE_COUNT: {meta['pdf_page_count']}",
        f"SOURCE_SHA256: {meta['source_sha256']}",
        f"REPOSITORY: {REPO_OWNER}/{REPO_NAME}",
        "",
    ]
    body = []
    for pg in pages:
        pno1 = pg["pno0"] + 1
        seg = [f"========== PDF_PAGE {page_name(pno1)} ==========",
               f"TEXT_SOURCE: {pg['source']}"]
        if pg["source"] == "ocr":
            seg.append(f"OCR_ENGINE: tesseract")
            seg.append(f"OCR_LANGUAGE: {OCR_LANG}")
        seg.append("")
        seg.append(pg["text"])
        seg.append("")
        body.append("\n".join(seg))
    return "\n".join(head) + "\n" + "\n".join(body)


FULL_HTML_CSS = """
body{font-family:"Noto Sans CJK SC","WenQuanYi Micro Hei",sans-serif;margin:0;background:#f6f7f9;color:#1a1a1a}
header{background:#0f2557;color:#fff;padding:18px 24px}
header h1{margin:0 0 6px;font-size:20px}
header p{margin:2px 0;font-size:13px;opacity:.85}
nav{background:#fff;border-bottom:1px solid #e3e6ea;padding:10px 24px;font-size:13px}
nav a{color:#0b57d0;margin-right:16px;text-decoration:none}
.page{background:#fff;margin:14px auto;max-width:900px;padding:14px 20px;border:1px solid #e3e6ea;border-radius:6px}
.page-head{font-size:12px;color:#666;border-bottom:1px dashed #ddd;padding-bottom:6px;margin-bottom:8px;font-family:monospace}
.page-head a.pl{color:#0b57d0;text-decoration:none;font-family:sans-serif;font-weight:600}
.page-head a.pl:hover{text-decoration:underline}
.ts-embedded{color:#0a7d32}.ts-ocr{color:#b06000}.ts-mixed{color:#8a6d00}.ts-none{color:#888}.ts-error{color:#c62828}
pre{white-space:pre-wrap;word-wrap:break-word;font-family:inherit;font-size:14.5px;line-height:1.75;margin:0}
footer{max-width:900px;margin:18px auto 40px;font-size:12px;color:#777;padding:0 20px}
"""


def full_html_content(meta, pages, urls) -> str:
    """构建时生成正文的静态 HTML（不依赖 JS 再 fetch TXT，spec §22）。
    每页页头旁附该页 TXT / blocks JSON 的真实相对链接（spec §10），
    Web Chat AI 无需自行拼 URL 即可从 full.html 跳到精确页。"""
    esc = html_mod.escape
    out = []
    out.append(
        '<!DOCTYPE html>\n<html lang="zh">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{esc(meta["title"])} (AI 全文)</title>\n<style>{FULL_HTML_CSS}</style>\n'
        '</head>\n<body>\n<header>\n'
        f'<h1>{esc(meta["title"])}</h1>\n'
        f'<p>SOURCE_PATH: {esc(meta["source_path"])}</p>\n'
        f'<p>PDF_PAGE_COUNT: {meta["pdf_page_count"]}'
        f' · SOURCE_SHA256: {esc(meta["source_sha256"][:16])}&#8230;'
        f' · extraction_status: {esc(meta.get("extraction_status", ""))}</p>\n'
        '</header>\n<nav>\n'
        '<a href="index.html">文档首页 (landing)</a>\n'
        '<a href="full.txt">full.txt</a>\n'
        '<a href="manifest.json">manifest.json</a>\n'
        '<a href="pages/index.html">Pages 目录</a>\n'
        '<a href="blocks/index.html">Blocks 目录</a>\n'
        '<a href="../../index.html">文档列表</a>\n'
        f'<a href="{esc(urls["viewer"])}">PDF.js 在线阅读</a>\n'
        f'<a href="{esc(urls["original"])}">原始 PDF (GitHub)</a>\n'
        '</nav>\n')
    for pg in pages:
        pno1 = pg["pno0"] + 1
        ts = pg["source"]
        ocr_note = f' · OCR(tesseract, {esc(OCR_LANG)})' if ts == "ocr" else ""
        out.append(
            f'<div class="page" id="pdf-page-{page_name(pno1)}">\n'
            f'<div class="page-head">PDF_PAGE {page_name(pno1)} · '
            f'<span class="ts-{ts}">TEXT_SOURCE: {ts}</span>{ocr_note} · '
            f'<a class="pl" href="pages/{page_name(pno1)}.txt">Page TXT</a> · '
            f'<a class="pl" href="blocks/{page_name(pno1)}.json">Blocks JSON</a>'
            f'</div>\n<pre>{esc(pg["text"])}</pre>\n</div>\n')
    out.append(
        '<footer>派生文本由 scripts/build-ai-docs.py 自动生成，原始 PDF 为唯一 '
        'Source of Truth（SHA256 见 manifest.json）。<br>\n'
        'TEXT_SOURCE=ocr 的页面为机器识别文本，可能存在识别误差；涉及芯片型号/引脚/'
        '寄存器/bit 位/地址/数字/公式/表格/原理图/程序代码的关键结论，请回原始 PDF '
        '页面核验。页码为 PDF 物理页（1-based）。</footer>\n</body>\n</html>\n')
    return "".join(out)


# ---------------------------------------------------------------- HTML 导航 --
# Web Chat AI 的导航模型是"真实 <a href> → 打开 → 下一个真实 <a href>"。
# 以下三类页面全部为构建时生成的静态 HTML：核心内容不依赖 JavaScript，
# 每一跳的 URL 都来自上一页中实际存在的 href，AI 无需自行拼 URL。

DOC_NAV_CSS = """
body{font-family:"Noto Sans CJK SC","WenQuanYi Micro Hei",sans-serif;margin:0;background:#f6f7f9;color:#1a1a1a}
header{background:#0f2557;color:#fff;padding:18px 24px}
header h1{margin:0 0 6px;font-size:21px}
header p{margin:2px 0;font-size:13px;opacity:.85;word-break:break-all}
nav{background:#fff;border-bottom:1px solid #e3e6ea;padding:10px 24px;font-size:13px}
nav a{color:#0b57d0;margin-right:14px;text-decoration:none}
nav a:hover{text-decoration:underline}
main{max-width:980px;margin:0 auto;padding:18px 20px 60px}
.meta{background:#fff;border:1px solid #e3e6ea;border-radius:8px;padding:4px 18px;margin-bottom:18px;font-size:13.5px}
.meta table{border-collapse:collapse;width:100%}
.meta td{padding:7px 8px;border-bottom:1px solid #eef1f5;vertical-align:top}
.meta td:first-child{color:#666;white-space:nowrap;width:170px}
.meta tr:last-child td{border-bottom:none}
.card{background:#fff;border:1px solid #e3e6ea;border-radius:8px;padding:16px 18px;margin-bottom:18px}
.card h2{margin:0 0 10px;font-size:16px}
.card ul{margin:0;padding-left:22px;line-height:2}
.card a{color:#0b57d0;text-decoration:none;font-weight:600}
.card a:hover{text-decoration:underline}
.warn{background:#fff8e6;border:1px solid #f0e0b0;border-radius:8px;padding:12px 16px;font-size:12.5px;line-height:1.7;color:#5a4a00}
.plist{list-style:none;margin:0;padding:0;columns:3 260px;column-gap:28px}
.plist li{break-inside:avoid;padding:3px 0;font-size:13.5px}
.plist a{color:#0b57d0;text-decoration:none;font-family:monospace}
.plist a:hover{text-decoration:underline}
.ts{font-size:11px;padding:1px 6px;border-radius:999px;margin-left:6px;vertical-align:middle}
.ts-embedded{background:#e6f4ea;color:#0a7d32}.ts-ocr{background:#fdeede;color:#b06000}
.ts-mixed{background:#faf3d9;color:#8a6d00}.ts-none{background:#eee;color:#888}.ts-error{background:#fdecea;color:#c62828}
footer{max-width:980px;margin:0 auto;padding:0 20px 40px;font-size:12px;color:#777}
"""


def _ts_badge(source: str) -> str:
    esc = html_mod.escape
    return (f'<span class="ts ts-{esc(source)}">{esc(source)}</span>'
            if source else "")


def landing_html_content(m, urls) -> str:
    """文档 landing page（docs/<doc_id>/index.html）：Web Chat AI 从文档列表
    点进来的第一跳，全部关键入口都是真实 <a href>。"""
    esc = html_mod.escape
    n = m.get("pdf_page_count", 0)
    status = m.get("extraction_status", "error")
    rows = [
        ("标题 (title)", esc(m.get("title", ""))),
        ("显示标题 (display_title)", esc(m.get("display_title",
                                                m.get("title", "")))),
        ("SOURCE_PATH", esc(m.get("source_path", ""))),
        ("doc_id", esc(m.get("doc_id", ""))),
        ("PDF 物理页数 (pdf_page_count)", str(n)),
        ("extraction_status",
         f'<span class="ts ts-{esc(status)}">{esc(status)}</span>'),
        ("embedded 页数", str(m.get("embedded_page_count", 0))),
        ("OCR 页数", str(m.get("ocr_page_count", 0))),
        ("mixed / none / error 页数",
         f'{m.get("mixed_page_count", 0)} / {m.get("empty_page_count", 0)}'
         f' / {m.get("error_page_count", 0)}'),
        ("SOURCE_SHA256", esc(m.get("source_sha256", ""))),
        ("repository / branch", esc(f"{m.get('repository', '')} · "
                                    f"{m.get('branch', '')}")),
    ]
    meta_rows = "\n".join(f"<tr><td>{k}</td><td>{v}</td></tr>"
                          for k, v in rows)
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(m.get("title", ""))} — AI Reading Path 文档页面</title>
<style>{DOC_NAV_CSS}</style>
</head>
<body>
<header>
<h1>{esc(m.get("display_title", m.get("title", "")))}</h1>
<p>AI Reading Path 文档页面（landing page）— 沿下方真实链接导航，无需自行拼接 URL</p>
</header>
<nav>
<a href="../../index.html">← 文档列表</a>
<a href="full.txt">full.txt</a>
<a href="full.html">full.html</a>
<a href="manifest.json">manifest.json</a>
<a href="pages/index.html">Pages 目录</a>
<a href="blocks/index.html">Blocks 目录</a>
<a href="{esc(urls["viewer"])}">PDF.js 在线阅读（人工）</a>
</nav>
<main>
<div class="meta"><table>
{meta_rows}
</table></div>
<div class="card">
<h2>📖 AI 派生文本（真实链接，Web Chat AI 沿此导航）</h2>
<ul>
<li><a href="full.txt">Full TXT</a> — 整本全文（PDF_PAGE 分隔 + TEXT_SOURCE 标记）</li>
<li><a href="full.html">Full HTML</a> — 全文 HTML（页锚点 #pdf-page-NNNN，页头旁附单页链接）</li>
<li><a href="manifest.json">Manifest</a> — 提取元数据（SHA256 / 页数 / 来源统计 / 引擎版本）</li>
<li><a href="pages/index.html">Pages</a> — 目录页：每一物理页一个 TXT 的完整链接清单（共 {n} 页）</li>
<li><a href="blocks/index.html">Blocks</a> — 目录页：每页版面块 JSON 的完整链接清单</li>
</ul>
</div>
<div class="card">
<h2>📄 原始 PDF（Source of Truth）</h2>
<ul>
<li><a href="{esc(urls["original"])}">GitHub 原始 PDF</a> — 仓库文件页</li>
<li><a href="{esc(urls["raw"])}">raw PDF</a> — raw.githubusercontent.com 二进制（Agent/脚本可解析）</li>
<li><a href="{esc(urls["viewer"])}">PDF.js Viewer</a> — 人工在线阅读（需浏览器 JavaScript，AI 不要当文本源）</li>
</ul>
</div>
<div class="warn">⚠️ TEXT_SOURCE = <b>ocr</b> 的页为 Tesseract 机器识别文本（非 PDF 内嵌原生文字），
可能存在识别误差。涉及芯片型号 / 引脚 / 寄存器 / bit 位 / 地址 / 数字 / 公式 / 表格 /
原理图 / 程序代码的关键结论，请回原始 PDF 核验。页码均为 PDF 物理页（1-based）。</div>
</main>
<footer>派生文本由 scripts/build-ai-docs.py 自动生成；原始 PDF 为唯一 Source of Truth。
本页为静态 HTML，核心内容不依赖 JavaScript。</footer>
</body>
</html>
"""


def _dir_index_html(m, kind: str) -> str:
    """pages/index.html 与 blocks/index.html：逐页真实链接清单。
    kind = "pages"（NNNN.txt）或 "blocks"（NNNN.json）。"""
    esc = html_mod.escape
    n = m.get("pdf_page_count", 0)
    page_sources = m.get("page_sources", {})
    ext = "txt" if kind == "pages" else "json"
    items = []
    for p in range(1, n + 1):
        ts = page_sources.get(str(p), "")
        items.append(
            f'<li><a href="{page_name(p)}.{ext}">{page_name(p)}.{ext}</a>'
            f'{_ts_badge(ts)}</li>')
    item_html = "\n".join(items) if items else "<li>（无页）</li>"
    other = "blocks" if kind == "pages" else "pages"
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(m.get("title", ""))} — {kind} 目录</title>
<style>{DOC_NAV_CSS}</style>
</head>
<body>
<header>
<h1>{esc(m.get("display_title", m.get("title", "")))} — {kind} 目录</h1>
<p>共 {n} 个文件 · 每一项都是真实链接，直接点击读取对应 PDF 物理页</p>
</header>
<nav>
<a href="../index.html">← 文档首页</a>
<a href="../full.txt">full.txt</a>
<a href="../full.html">full.html</a>
<a href="../manifest.json">manifest.json</a>
<a href="../{other}/index.html">{other} 目录</a>
</nav>
<main>
<ul class="plist">
{item_html}
</ul>
<div class="warn" style="margin-top:18px">⚠️ 徽标为该页 TEXT_SOURCE（embedded / ocr / mixed / none / error）。
ocr 页为机器识别文本，非"原文等价物"，关键结论请回原始 PDF 核验。
文件名即 PDF 物理页号（1-based，4 位补零）。</div>
</main>
<footer>派生文本由 scripts/build-ai-docs.py 自动生成；本页为静态 HTML，
核心内容不依赖 JavaScript。</footer>
</body>
</html>
"""


def parse_page_txt(path: str):
    """从 pages/NNNN.txt 解析 (pno1, text_source, text)。
    用于缓存命中后从既有页文件重建 full.html（无需重新提取/OCR）。"""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    marker = "========== PAGE_TEXT =========="
    idx = content.find(marker)
    if idx < 0:
        return None
    header = content[:idx]
    body = content[idx + len(marker):].strip("\n")
    pno1, source = 0, "none"
    for line in header.splitlines():
        if line.startswith("PDF_PAGE:"):
            try:
                pno1 = int(line.split(":", 1)[1])
            except ValueError:
                pass
        elif line.startswith("TEXT_SOURCE:"):
            source = line.split(":", 1)[1].strip()
    if pno1 <= 0:
        return None
    return pno1, source, body


def regenerate_nav_files(out_doc_dir: str, m, pages_data=None):
    """（重新）生成一个文档的全部 HTML 导航文件：landing index.html、
    pages/index.html、blocks/index.html、full.html。

    - pages_data 提供（新构建）：直接使用页数据；
    - pages_data 为 None（缓存命中）：从已落盘的 pages/*.txt 解析重建 full.html。
    每次构建都会执行，因此 HTML 模板更新不需要使 OCR 缓存失效
    （EXTRACTOR_VERSION 不因纯导航模板变化而递增）。
    """
    urls = doc_urls(m["doc_id"], m["source_path"])
    os.makedirs(os.path.join(out_doc_dir, "pages"), exist_ok=True)
    os.makedirs(os.path.join(out_doc_dir, "blocks"), exist_ok=True)
    with open(os.path.join(out_doc_dir, "index.html"), "w",
              encoding="utf-8") as f:
        f.write(landing_html_content(m, urls))
    with open(os.path.join(out_doc_dir, "pages", "index.html"), "w",
              encoding="utf-8") as f:
        f.write(_dir_index_html(m, "pages"))
    with open(os.path.join(out_doc_dir, "blocks", "index.html"), "w",
              encoding="utf-8") as f:
        f.write(_dir_index_html(m, "blocks"))
    if pages_data is None:
        pages_data = []
        pages_dir = os.path.join(out_doc_dir, "pages")
        for fn in sorted(os.listdir(pages_dir)):
            if not fn.endswith(".txt"):
                continue  # 跳过 index.html 等非页文件
            parsed = parse_page_txt(os.path.join(pages_dir, fn))
            if parsed:
                pno1, source, body = parsed
                pages_data.append({"pno0": pno1 - 1, "source": source,
                                   "text": body})
        pages_data.sort(key=lambda p: p["pno0"])
    meta = {"title": m["title"], "source_path": m["source_path"],
            "pdf_page_count": m.get("pdf_page_count", 0),
            "source_sha256": m.get("source_sha256", ""),
            "extraction_status": m.get("extraction_status", "")}
    with open(os.path.join(out_doc_dir, "full.html"), "w",
              encoding="utf-8") as f:
        f.write(full_html_content(meta, pages_data, urls))


def doc_urls(doc_id: str, source_path: str):
    """全部输出绝对 HTTPS URL，AI 无需自行猜测路径映射（spec §17）。"""
    encoded = encode_repo_path(source_path)
    raw_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{REPO_BRANCH}/{encoded}"
    base = f"{PAGES_BASE_URL}/ai/docs/{doc_id}"
    return {
        "doc_base": base + "/",
        "doc_index": f"{base}/index.html",
        "full_txt": f"{base}/full.txt",
        "full_html": f"{base}/full.html",
        "pages_base": f"{base}/pages/",
        "pages_index": f"{base}/pages/index.html",
        "blocks_base": f"{base}/blocks/",
        "blocks_index": f"{base}/blocks/index.html",
        "manifest": f"{base}/manifest.json",
        "viewer": f"{PAGES_BASE_URL}/web/viewer.html?file="
                  + urllib.parse.quote(raw_url, safe=""),
        "original": f"https://github.com/{REPO_OWNER}/{REPO_NAME}/blob/{REPO_BRANCH}/{encoded}",
        "raw": raw_url,
    }


def render_index_html(documents) -> str:
    esc = html_mod.escape
    rows = []
    for d in documents:
        status_color = {"ok": "#0a7d32", "partial": "#b06000",
                        "text_sparse": "#8a6d00", "invalid_pdf": "#c62828",
                        "lfs_not_materialized": "#c62828",
                        "ocr_failed": "#c62828", "error": "#c62828"}.get(
                            d["extraction_status"], "#333")
        doc_base = f"{PAGES_BASE_URL}/ai/docs/{d['doc_id']}"
        landing = f"{doc_base}/index.html"
        pages_idx = f"{doc_base}/pages/index.html"
        blocks_idx = f"{doc_base}/blocks/index.html"
        rows.append(f"""<tr>
<td class="t"><a href="{esc(landing)}">{esc(d['title'])}</a><br>
<span class="path">{esc(d['source_path'])}</span></td>
<td class="n">{d['pdf_page_count']}</td>
<td class="n"><span style="color:{status_color}">{esc(d['extraction_status'])}</span></td>
<td class="n">{d['embedded_page_count']}</td>
<td class="n">{d['ocr_page_count']}{f" (+{d['mixed_page_count']} mixed)" if d.get('mixed_page_count') else ""}</td>
<td class="n">{d.get('empty_page_count', 0)}</td>
<td class="l"><a href="{esc(landing)}">文档页面</a> ·
<a href="{esc(d['ai_full_text_url'])}">full.txt</a> ·
<a href="{esc(d['ai_full_html_url'])}">full.html</a> ·
<a href="{esc(d['manifest_url'])}">manifest</a> ·
<a href="{esc(pages_idx)}">pages/</a> ·
<a href="{esc(blocks_idx)}">blocks/</a></td>
<td class="l"><a href="{esc(d['viewer_url'])}">Viewer</a> ·
<a href="{esc(d['original_github_url'])}">GitHub</a> ·
<a href="{esc(d['original_raw_url'])}">raw</a></td>
</tr>""")
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Reading Path — DSP28335 学习资料</title>
<style>
body{{font-family:"Noto Sans CJK SC","WenQuanYi Micro Hei",sans-serif;margin:0;background:#f6f7f9;color:#1a1a1a}}
header{{background:#0f2557;color:#fff;padding:20px 24px}}
header h1{{margin:0 0 6px;font-size:22px}}
header p{{margin:3px 0;font-size:13px;opacity:.85}}
.paths{{background:#fff;border-bottom:1px solid #e3e6ea;padding:12px 24px;font-size:13px;line-height:1.7}}
.paths code{{background:#eef1f5;padding:1px 6px;border-radius:4px}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:13.5px}}
th,td{{padding:8px 10px;border-bottom:1px solid #e3e6ea;text-align:left;vertical-align:top}}
th{{background:#eef1f5;position:sticky;top:0}}
td.n{{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}}
td.t{{min-width:240px}} td.l{{font-size:12.5px;white-space:nowrap}}
.path{{font-size:12px;color:#777}}
a{{color:#0b57d0;text-decoration:none}}
tr:hover{{background:#f3f7ff}}
.note{{padding:10px 24px;background:#fff8e6;font-size:12.5px;line-height:1.6}}
</style>
</head>
<body>
<header>
<h1>🤖 AI Reading Path — 网页聊天 AI 文档读取入口</h1>
<p>本页为静态 HTML，沿文档表格中的真实链接逐页点击即可读取 PDF 派生正文（无需 JavaScript、无需自行拼接 URL）·
机器入口（Agent / Script）：<code>index.json</code> ·
人类阅读请用 <a style="color:#9db8ff" href="../">PDF.js 文档中心</a> ·
使用说明：<a style="color:#9db8ff" href="AI_USAGE.txt">AI_USAGE.txt</a></p>
</header>
<div class="paths">
<b>三种访问方式</b>：<br>
Human → <a href="../">PDF.js Viewer</a>（在线阅读，体验不变）；<br>
Web Chat AI（ChatGPT / Gemini / DeepSeek 等）→ <b>沿真实 HTML 链接导航</b>：
在本页下方文档表格中点击文档标题，进入<b>文档页面（landing page）</b>→
full.txt / full.html / <b>Pages 目录</b> / <b>Blocks 目录</b> → 单页 TXT。
<b>无需先读取 JSON，无需自行拼接 URL —— 每一跳都是页面里真实存在的
&lt;a href&gt; 链接。</b><br>
Agent / Script（可任意 HTTP fetch、二进制下载、本地 PDF parser）→
<code>index.json</code>（机器接口，含每文档全部绝对 URL）或
<code>original_raw_url</code> 原始 PDF。<b>Web Chat AI 不再默认 raw PDF 优先。</b>
</div>
<div class="note">⚠️ TEXT_SOURCE = <b>ocr</b> 的页为 Tesseract 机器识别文本（非 PDF 内嵌原生文字），
可能存在识别误差。涉及芯片型号 / 引脚 / 寄存器 / bit 位 / 地址 / 数字 / 公式 / 表格 /
原理图 / 程序代码的关键结论，请回原始 PDF 核验（页码为 PDF 物理页，1-based）。</div>
<table>
<thead><tr><th>文档</th><th title="PDF 物理页总数">页数</th><th>状态</th>
<th title="embedded text 页数">embedded</th><th title="OCR 页数">ocr</th>
<th title="无文字页数">empty</th><th>AI 派生文本</th><th>原始 / 人工</th></tr></thead>
<tbody>
{"".join(rows)}
</tbody>
</table>
</body>
</html>
"""


AI_USAGE_TXT = """AI USAGE — 网页聊天 AI 读取本仓库 PDF 的推荐路径
=================================================

入口（静态 HTML，直接打开）：
  {base}/ai/

导航方式：上一个网页中的真实 <a href> → 打开 → 下一个网页中的真实
<a href> → 打开。不要求根据 JSON 字符串自行拼接 URL。

推荐流程（HTML 链接导航）：
  1. 打开 /ai/ 文档列表页（index.html）。静态 HTML 源码本身即含全部
     370 个文档的标题 / source_path 与真实链接，无需 JavaScript。
  2. 按 title / display_title / source_path / match_key 定位目标文档
     （用户可能只说书名，不一定完整复制文件名），点击其标题链接进入
     文档 landing page（docs/<doc_id>/index.html）。
  3. landing page 上点击真实链接直达：
     full.txt（整本全文，含 PDF_PAGE 分隔与 TEXT_SOURCE 标记）、
     full.html（全文 HTML）、manifest.json（元数据）、
     Pages 目录（pages/index.html，每一物理页一个真实链接清单）、
     Blocks 目录（blocks/index.html，每页版面块 JSON 链接清单）。
  4. 精确页查询：进入 Pages 目录，点击目标页链接（如 PDF Page 0148）
     读取该页 TXT。常见做法：命中目标后只读 当前页 / 前一页 / 后一页。
     不需要根据页号自己拼 URL。
  5. 需要版面位置（bbox）时：进入 Blocks 目录点击对应页 JSON
     （坐标为 PDF 点，原点页面左上角；OCR 块以 block_source=ocr 标记，
     不与 embedded 坐标混淆）。
  6. 需要原始证据 / 人工核验时：点 landing page 上的 GitHub 原始 PDF /
     raw PDF / PDF.js Viewer 链接。

机器入口（Agent / Script / 支持任意 HTTP fetch 的环境可直接使用）：
  {base}/ai/index.json
  含每文档 ai_full_text_url / ai_pages_base_url / ai_blocks_base_url
  等绝对 URL 与全部元数据。

注意：PDF.js Viewer 的 HTML 页面不是 PDF 正文（需浏览器 JavaScript 渲染），
网页聊天 AI 不要把它当文本源；original / raw PDF 仍是 Source of Truth。

TEXT_SOURCE 语义（每页 TXT / blocks JSON 都带此标记）：
  embedded — PDF 内嵌文字对象直接提取（可靠性最高）
  ocr      — 页面无足够内嵌文字，由本地 Tesseract 识别扫描图像所得。
             ⚠️ OCR 文本不是"原文等价物"，可能有识别误差。涉及芯片型号、
             引脚、寄存器、bit 位、地址、数字、公式、表格、原理图、程序
             代码的关键结论，应回原始 PDF 页面核验。
  mixed    — 内嵌文字稀疏且 OCR 未优于内嵌文字，最终保留内嵌文字
  none     — 内嵌与 OCR 均无文字（如纯图片页 / 空白页）
  error    — 提取异常（详见 manifest.error_pages）

页码约定：所有 PDF_PAGE / pages/NNNN.txt 均为 PDF 物理页（1-based，
即 PDF.js Viewer 显示的页码），不是书籍页脚印刷页码。

extraction_status 语义（文档级）：
  ok（全部页提取成功）/ partial（部分页 error）/ text_sparse（全文过少）/
  invalid_pdf / lfs_not_materialized（Git-LFS pointer，非 PDF 正文）/ ocr_failed / error

失败规则：若派生文本不存在、extraction_status 异常、文本为空、文件不是有效
PDF，必须如实报告，不得用互联网同名资料或 AI 总结冒充 PDF 原文。
"""


# ---------------------------------------------------------------- 主流程 --

def cache_key_valid(cache_doc_dir: str, sha: str) -> bool:
    """缓存命中条件：source SHA256 + extractor 版本 + OCR 配置 全部一致。"""
    mf = os.path.join(cache_doc_dir, "manifest.json")
    if not os.path.isfile(mf):
        return False
    try:
        with open(mf, encoding="utf-8") as f:
            m = json.load(f)
        return (m.get("source_sha256") == sha
                and m.get("extractor_version") == EXTRACTOR_VERSION
                and m.get("ocr_config", {}).get("dpi") == OCR_DPI
                and m.get("ocr_config", {}).get("languages") == OCR_LANG
                and m.get("ocr_config", {}).get("min_embedded_chars") == MIN_EMBEDDED_CHARS
                and m.get("ocr_config", {}).get("max_edge_px") == OCR_MAX_EDGE_PX)
    except Exception:
        return False


def build_document(rel_path: str, commit: str, use_pool):
    """处理单个 PDF，返回 (manifest, pages_data, urls) 或错误状态。"""
    abs_path = os.path.join(REPO_ROOT, rel_path)
    status, size = validate_pdf(abs_path)
    sha = sha256_file(abs_path) if status == "ok" else ""
    doc_id = make_doc_id(rel_path)
    urls = doc_urls(doc_id, rel_path)
    stem = os.path.splitext(os.path.basename(rel_path))[0]

    common = {
        "title": stem,
        "filename": os.path.basename(rel_path),
        "source_path": rel_path,
        "doc_id": doc_id,
        "repository": f"{REPO_OWNER}/{REPO_NAME}",
        "branch": REPO_BRANCH,
        "commit": commit,
    }

    if status != "ok":
        return {"kind": "error", "status": status, "size": size, "sha": sha,
                "urls": urls, **common}, None

    try:
        doc = pymupdf.open(abs_path)
        page_count = doc.page_count
        meta_title = (doc.metadata or {}).get("title", "") or ""
        doc.close()
    except Exception as e:
        return {"kind": "error", "status": "invalid_pdf", "size": size,
                "sha": sha, "urls": urls, "err": str(e)[:200], **common}, None
    if page_count <= 0:
        return {"kind": "error", "status": "invalid_pdf", "size": size,
                "sha": sha, "urls": urls, **common}, None

    # ------- 页级提取（必要时并行） -------
    t0 = time.time()
    if WORKERS > 1 and page_count >= 8:
        futures = [use_pool.submit(extract_page, abs_path, pno)
                   for pno in range(page_count)]
        pages = [f.result() for f in futures]
    else:
        pages = [extract_page(abs_path, pno) for pno in range(page_count)]
    elapsed = round(time.time() - t0, 1)
    pages.sort(key=lambda p: p["pno0"])

    counts = {"embedded": 0, "ocr": 0, "mixed": 0, "none": 0, "error": 0}
    for pg in pages:
        counts[pg["source"]] += 1
    ocr_seconds = round(sum(p["ocr_seconds"] for p in pages), 1)
    text_chars = sum(len(p["text"]) for p in pages)
    sparse_pages = [p["pno0"] + 1 for p in pages if p["ocr_attempted"]]
    error_pages = [p["pno0"] + 1 for p in pages if p["source"] == "error"]
    ocr_failed = any(p["ocr_error"] for p in pages if p["ocr_error"]
                     and "tsv-failed" not in str(p["ocr_error"]))

    # ------- 文档级状态 -------
    if error_pages:
        doc_status = "partial"
    elif ocr_failed:
        doc_status = "ocr_failed"
    elif page_count and text_chars < MIN_EMBEDDED_CHARS * page_count / 8:
        doc_status = "text_sparse"
    else:
        doc_status = "ok"

    display_title = stem
    mt = meta_title.strip()
    # 仅当元数据标题"看起来合理"时才用作 display_title：
    # 排除 URL / 水印型内容（如 "bingdian001.com"），避免误导用户与 AI。
    if 3 < len(mt) < 120 and not re.search(
            r"www\.|https?:|\.com|\.cn|\.net", mt, re.I):
        display_title = mt

    manifest = {
        **common,
        "display_title": display_title,
        "source_sha256": sha,
        "file_size": size,
        "pdf_page_count": page_count,
        "match_key": normalize_match_key(stem),
        "extractor": "scripts/build-ai-docs.py",
        "extractor_version": EXTRACTOR_VERSION,
        "pymupdf_version": PYMUPDF_VERSION,
        "ocr_engine": "tesseract",
        "ocr_engine_version": tesseract_version(),
        "ocr_languages": OCR_LANG,
        "ocr_config": {"dpi": OCR_DPI, "languages": OCR_LANG,
                       "min_embedded_chars": MIN_EMBEDDED_CHARS,
                       "max_edge_px": OCR_MAX_EDGE_PX,
                       "psm": 3},
        "extraction_status": doc_status,
        "embedded_page_count": counts["embedded"],
        "ocr_page_count": counts["ocr"],
        "mixed_page_count": counts["mixed"],
        "empty_page_count": counts["none"],
        "error_page_count": counts["error"],
        "error_pages": error_pages,
        "sparse_pages": sparse_pages,
        "text_char_count": text_chars,
        "ocr_seconds": ocr_seconds,
        "build_seconds": elapsed,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "text_source_semantics": {
            "embedded": "PDF 内嵌文字对象提取（可靠性最高）",
            "ocr": "Tesseract 识别扫描图像所得，可能有误差，关键结论需回原 PDF 核验",
            "mixed": "内嵌文字稀疏且 OCR 未更优，保留内嵌文字",
            "none": "内嵌与 OCR 均无文字",
            "error": "提取异常",
        },
        "urls": {
            "ai_doc_index_url": urls["doc_index"],
            "ai_full_text_url": urls["full_txt"],
            "ai_full_html_url": urls["full_html"],
            "ai_pages_base_url": urls["pages_base"],
            "ai_pages_index_url": urls["pages_index"],
            "ai_blocks_base_url": urls["blocks_base"],
            "ai_blocks_index_url": urls["blocks_index"],
            "manifest_url": urls["manifest"],
            "original_github_url": urls["original"],
            "original_raw_url": urls["raw"],
            "viewer_url": urls["viewer"],
        },
        "page_sources": {str(p["pno0"] + 1): p["source"] for p in pages},
    }
    meta_for_txt = {"title": stem, "source_path": rel_path,
                    "pdf_page_count": page_count, "source_sha256": sha}
    return {"kind": "ok", "manifest": manifest, "pages": pages,
            "meta_for_txt": meta_for_txt, "urls": urls, "sha": sha,
            "doc_id": doc_id}, manifest


def write_doc_outputs(out_doc_dir: str, result):
    """写 pages/ blocks/ full.txt manifest.json。
    全部 HTML（full.html / landing / pages 目录 / blocks 目录）统一由
    regenerate_nav_files() 生成，缓存命中与新构建共用同一模板路径。"""
    os.makedirs(os.path.join(out_doc_dir, "pages"), exist_ok=True)
    os.makedirs(os.path.join(out_doc_dir, "blocks"), exist_ok=True)
    m = result["manifest"]
    meta = result["meta_for_txt"]
    for pg in result["pages"]:
        pno1 = pg["pno0"] + 1
        with open(os.path.join(out_doc_dir, "pages",
                               page_name(pno1) + ".txt"), "w",
                  encoding="utf-8") as f:
            f.write(page_txt_content(meta, pno1, pg["text"], pg["source"]))
        block_json = {
            "doc_id": m["doc_id"],
            "source_path": m["source_path"],
            "pdf_page": pno1,
            "pdf_page_count": m["pdf_page_count"],
            "page_width": pg["page_w"],
            "page_height": pg["page_h"],
            "text_source": pg["source"],
            "embedded_char_count": pg["embedded_chars"],
            "ocr_char_count": pg["ocr_chars"],
            "coordinate_system": ("PDF 点（1/72 英寸），原点页面左上角，"
                                  "与 PyMuPDF 一致；OCR 块由渲染像素坐标换算"),
            "blocks": pg["blocks"],
        }
        with open(os.path.join(out_doc_dir, "blocks",
                               page_name(pno1) + ".json"), "w",
                  encoding="utf-8") as f:
            json.dump(block_json, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out_doc_dir, "full.txt"), "w",
              encoding="utf-8") as f:
        f.write(full_txt_content(meta, result["pages"]))
    # full.html / landing / pages 目录 / blocks 目录 → regenerate_nav_files()
    with open(os.path.join(out_doc_dir, "manifest.json"), "w",
              encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)


def copy_cached_doc(cache_doc_dir: str, out_doc_dir: str):
    if os.path.isdir(cache_doc_dir):
        if os.path.isdir(out_doc_dir):
            shutil.rmtree(out_doc_dir)
        shutil.copytree(cache_doc_dir, out_doc_dir)


def save_to_cache(out_doc_dir: str, cache_doc_dir: str):
    if os.path.isdir(out_doc_dir):
        if os.path.isdir(cache_doc_dir):
            shutil.rmtree(cache_doc_dir)
        os.makedirs(os.path.dirname(cache_doc_dir), exist_ok=True)
        shutil.copytree(out_doc_dir, cache_doc_dir)


def main():
    global WORKERS
    t_start = time.time()
    print(f"[build-ai-docs] repo root: {REPO_ROOT}")
    print(f"[build-ai-docs] out dir : {OUT_DIR}")
    print(f"[build-ai-docs] PyMuPDF {PYMUPDF_VERSION} · tesseract "
          f"{tesseract_version()} · lang={OCR_LANG} · dpi={OCR_DPI} · "
          f"min_embedded_chars={MIN_EMBEDDED_CHARS} · workers={WORKERS}")

    pdfs = discover_pdfs()
    only = [p for p in os.environ.get("AI_DOCS_ONLY", "").split(",") if p]
    if only:
        pdfs = [p for p in pdfs if p in only]
    limit = int(os.environ.get("AI_LIMIT", "0") or 0)
    if limit > 0:
        pdfs = pdfs[:limit]
    print(f"[build-ai-docs] PDFs to process: {len(pdfs)}")

    os.makedirs(os.path.join(OUT_DIR, "docs"), exist_ok=True)
    commit = git_commit()

    pool = ProcessPoolExecutor(max_workers=WORKERS) if WORKERS > 1 else None
    index_docs = []
    report = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                          time.gmtime()),
              "repository": f"{REPO_OWNER}/{REPO_NAME}",
              "branch": REPO_BRANCH, "commit": commit,
              "extractor_version": EXTRACTOR_VERSION,
              "pymupdf_version": PYMUPDF_VERSION,
              "ocr": {"engine": "tesseract",
                      "version": tesseract_version(),
                      "languages": OCR_LANG, "dpi": OCR_DPI,
                      "min_embedded_chars": MIN_EMBEDDED_CHARS},
              "workers": WORKERS, "documents": []}
    totals = {"pdf_total": len(pdfs), "valid": 0, "invalid_pdf": 0,
              "lfs_not_materialized": 0, "embedded_only_docs": 0,
              "ocr_involved_docs": 0, "pages_total": 0,
              "embedded_pages": 0, "ocr_pages": 0, "mixed_pages": 0,
              "empty_pages": 0, "error_pages": 0, "ocr_seconds": 0.0,
              "cache_hits": 0, "cache_misses": 0}

    try:
        for i, rel in enumerate(pdfs):
            doc_id = make_doc_id(rel)
            out_doc_dir = os.path.join(OUT_DIR, "docs", doc_id)
            cache_doc_dir = (os.path.join(CACHE_DIR, "docs", doc_id)
                             if CACHE_DIR else "")
            sha_for_cache = ""
            if CACHE_DIR:
                sha_for_cache = sha256_file(os.path.join(REPO_ROOT, rel))

            # ---- 缓存命中：直接复用上次输出（含 OCR 结果，不重跑）----
            if CACHE_DIR and cache_key_valid(cache_doc_dir, sha_for_cache):
                copy_cached_doc(cache_doc_dir, out_doc_dir)
                with open(os.path.join(out_doc_dir, "manifest.json"),
                          encoding="utf-8") as f:
                    m = json.load(f)
                # HTML 导航文件每次构建都重新生成（模板更新无需失效 OCR 缓存）
                regenerate_nav_files(out_doc_dir, m)
                m["cached"] = True
                with open(os.path.join(out_doc_dir, "manifest.json"), "w",
                          encoding="utf-8") as f:
                    json.dump(m, f, ensure_ascii=False, indent=1)
                if CACHE_DIR:
                    save_to_cache(out_doc_dir, cache_doc_dir)
                totals["cache_hits"] += 1
                totals["valid"] += 1
                totals["pages_total"] += m["pdf_page_count"]
                totals["embedded_pages"] += m["embedded_page_count"]
                totals["ocr_pages"] += m["ocr_page_count"]
                totals["mixed_pages"] += m.get("mixed_page_count", 0)
                totals["empty_pages"] += m.get("empty_page_count", 0)
                totals["error_pages"] += m.get("error_page_count", 0)
                totals["ocr_seconds"] += m.get("ocr_seconds", 0)
                index_docs.append(index_entry(m))
                report["documents"].append(
                    {"source_path": rel, "doc_id": doc_id,
                     "extraction_status": m["extraction_status"],
                     "cached": True})
                print(f"[{i+1}/{len(pdfs)}] CACHE  {rel} "
                      f"({m['pdf_page_count']}p)")
                continue
            if CACHE_DIR:
                totals["cache_misses"] += 1

            result, manifest = build_document(rel, commit, pool)
            if result["kind"] == "error":
                totals[result["status"]] = totals.get(result["status"], 0) + 1
                # 失败文档也写入 manifest（如实报告，不掩盖）
                err_manifest = {
                    "title": result["title"],
                    "display_title": result["title"],
                    "filename": result["filename"],
                    "source_path": result["source_path"],
                    "source_sha256": result.get("sha", ""),
                    "file_size": result.get("size", 0),
                    "pdf_page_count": 0,
                    "doc_id": result["doc_id"],
                    "match_key": normalize_match_key(result["title"]),
                    "repository": result["repository"],
                    "branch": result["branch"],
                    "commit": result["commit"],
                    "extractor": "scripts/build-ai-docs.py",
                    "extractor_version": EXTRACTOR_VERSION,
                    "pymupdf_version": PYMUPDF_VERSION,
                    "ocr_engine": "tesseract",
                    "ocr_engine_version": tesseract_version(),
                    "ocr_languages": OCR_LANG,
                    "extraction_status": result["status"],
                    "error_detail": result.get("err", ""),
                    "urls": {
                        "original_github_url": result["urls"]["original"],
                        "original_raw_url": result["urls"]["raw"],
                        "viewer_url": result["urls"]["viewer"],
                    },
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                  time.gmtime()),
                }
                os.makedirs(out_doc_dir, exist_ok=True)
                with open(os.path.join(out_doc_dir, "manifest.json"), "w",
                          encoding="utf-8") as f:
                    json.dump(err_manifest, f, ensure_ascii=False, indent=1)
                index_docs.append(index_entry(err_manifest))
                report["documents"].append(
                    {"source_path": rel, "doc_id": doc_id,
                     "extraction_status": result["status"]})
                print(f"[{i+1}/{len(pdfs)}] FAIL   {rel} -> {result['status']}")
                continue

            write_doc_outputs(out_doc_dir, result)
            m = manifest
            regenerate_nav_files(out_doc_dir, m, pages_data=result["pages"])
            if CACHE_DIR:
                save_to_cache(out_doc_dir, cache_doc_dir)
            totals["valid"] += 1
            totals["pages_total"] += m["pdf_page_count"]
            totals["embedded_pages"] += m["embedded_page_count"]
            totals["ocr_pages"] += m["ocr_page_count"]
            totals["mixed_pages"] += m["mixed_page_count"]
            totals["empty_pages"] += m["empty_page_count"]
            totals["error_pages"] += m["error_page_count"]
            totals["ocr_seconds"] += m["ocr_seconds"]
            if m["ocr_page_count"] or m["mixed_page_count"]:
                totals["ocr_involved_docs"] += 1
            else:
                totals["embedded_only_docs"] += 1
            index_docs.append(index_entry(m))
            report["documents"].append({
                "source_path": rel, "doc_id": doc_id,
                "extraction_status": m["extraction_status"],
                "pdf_page_count": m["pdf_page_count"],
                "embedded_page_count": m["embedded_page_count"],
                "ocr_page_count": m["ocr_page_count"],
                "mixed_page_count": m["mixed_page_count"],
                "empty_page_count": m["empty_page_count"],
                "text_char_count": m["text_char_count"],
                "ocr_seconds": m["ocr_seconds"],
                "build_seconds": m["build_seconds"]})
            flag = "OCR" if (m["ocr_page_count"] or m["mixed_page_count"]) else "TXT"
            print(f"[{i+1}/{len(pdfs)}] {flag:<6} {rel} "
                  f"({m['pdf_page_count']}p, emb={m['embedded_page_count']}, "
                  f"ocr={m['ocr_page_count']}, mixed={m['mixed_page_count']}, "
                  f"none={m['empty_page_count']}, {m['build_seconds']}s)",
                  flush=True)
    finally:
        if pool:
            pool.shutdown()

    # ---- index.json / index.html / AI_USAGE.txt / build-report.json ----
    index_json = {
        "schema_version": 1,
        "repository": f"{REPO_OWNER}/{REPO_NAME}",
        "branch": REPO_BRANCH,
        "commit": commit,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pages_base_url": PAGES_BASE_URL,
        "machine_entry": f"{PAGES_BASE_URL}/ai/index.json",
        "usage": f"{PAGES_BASE_URL}/ai/AI_USAGE.txt",
        "match_key_rule": ("NFKC 归一 + casefold + 去除全部空白 + 去掉 .pdf 后缀；"
                          "用于用户只说书名时的模糊定位"),
        "document_count": len(index_docs),
        "documents": index_docs,
    }
    with open(os.path.join(OUT_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index_json, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_index_html(index_docs))
    with open(os.path.join(OUT_DIR, "AI_USAGE.txt"), "w", encoding="utf-8") as f:
        f.write(AI_USAGE_TXT.format(base=PAGES_BASE_URL))
    report["totals"] = totals
    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report["total_seconds"] = round(time.time() - t_start, 1)
    with open(os.path.join(OUT_DIR, "build-report.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    # ---- 控制台汇总（真实数字，spec §33） ----
    print("\n[build-ai-docs] ===== 构建汇总 =====")
    for k, v in totals.items():
        print(f"  {k}: {v}")
    total_bytes = 0
    largest = ("", 0)
    for root, _, files in os.walk(OUT_DIR):
        for fn in files:
            p = os.path.join(root, fn)
            sz = os.path.getsize(p)
            total_bytes += sz
            if fn == "full.txt" and sz > largest[1]:
                largest = (p, sz)
    print(f"  viewer/ai total size: {total_bytes/1048576:.1f} MB")
    if largest[0]:
        print(f"  largest full.txt: {largest[1]/1048576:.1f} MB "
              f"({os.path.relpath(largest[0], OUT_DIR)})")
    print(f"  total build time: {report['total_seconds']}s "
          f"(ocr {totals['ocr_seconds']}s)")
    print(f"[build-ai-docs] wrote: {OUT_DIR}/index.json")


def index_entry(m):
    """index.json 单条目。URL 由 doc_id + source_path 现算（确定性映射），
    不依赖 manifest 内可能过期的 urls 快照 —— 缓存命中与全新构建结果一致。"""
    urls = doc_urls(m["doc_id"], m["source_path"])
    return {
        "title": m["title"],
        "display_title": m.get("display_title", m["title"]),
        "filename": m.get("filename", ""),
        "source_path": m["source_path"],
        "match_key": m.get("match_key", ""),
        "doc_id": m["doc_id"],
        "pdf_page_count": m.get("pdf_page_count", 0),
        "source_sha256": m.get("source_sha256", ""),
        "file_size": m.get("file_size", 0),
        "extraction_status": m.get("extraction_status", "error"),
        "embedded_page_count": m.get("embedded_page_count", 0),
        "ocr_page_count": m.get("ocr_page_count", 0),
        "mixed_page_count": m.get("mixed_page_count", 0),
        "empty_page_count": m.get("empty_page_count", 0),
        "error_page_count": m.get("error_page_count", 0),
        "text_char_count": m.get("text_char_count", 0),
        "ai_doc_index_url": urls["doc_index"],
        "ai_full_text_url": urls["full_txt"],
        "ai_full_html_url": urls["full_html"],
        "ai_pages_base_url": urls["pages_base"],
        "ai_pages_index_url": urls["pages_index"],
        "ai_blocks_base_url": urls["blocks_base"],
        "ai_blocks_index_url": urls["blocks_index"],
        "manifest_url": urls["manifest"],
        "original_github_url": urls["original"],
        "original_raw_url": urls["raw"],
        "viewer_url": urls["viewer"],
    }


if __name__ == "__main__":
    main()

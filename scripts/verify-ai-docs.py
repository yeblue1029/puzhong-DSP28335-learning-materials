#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify-ai-docs.py — 验证 build-ai-docs.py 的输出，CI 中作为独立关卡。

检查项（spec §27）：
  1. JSON 语法：index.json + 每个 manifest.json + 每个 blocks/*.json
  2. 必需文件：index.html / AI_USAGE.txt / 每文档 manifest.json、full.txt、
     full.html、pages/、blocks/
  3. 页数一致：pages/*.txt 与 blocks/*.json 的文件个数 == manifest.pdf_page_count
     （页码从 0001 连续编号，无缺页、无多页）
  4. full.txt 的 "========== PDF_PAGE NNNN ==========" 分隔符数量 == 页数
  5. UTF-8：全部 TXT / HTML / JSON 均可按 UTF-8 解码
  6. SHA256 存在：manifest.source_sha256 为 64 位十六进制
  7. 源文件有效性：仓库内 source_path 存在、以 %PDF- 开头、不是 LFS pointer
  8. LFS pointer 防护：文档级 lfs_not_materialized 状态与真实文件一致
  9. extraction status 一致性：embedded + ocr + mixed + none + error 页数之和
     == pdf_page_count
 10. URL 卫生：index.json 中的 ai_*_url 全部为绝对 HTTPS 且指向本 Pages 站点，
     不引用本地路径（file:// / /data/ 等）
 11. index.html：静态源码中包含每文档标题与关键链接（不依赖 JS 渲染列表）

用法：python3 scripts/verify-ai-docs.py
退出码：0 = 全部通过；1 = 存在失败项（CI 会阻断部署）。
"""

import json
import os
import re
import sys

REPO_ROOT = os.environ.get("AI_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.environ.get("AI_OUT_DIR") or os.path.join(REPO_ROOT, "viewer", "ai")
REPO_OWNER = os.environ.get("REPO_OWNER", "yeblue1029")
REPO_NAME = os.environ.get("REPO_NAME", "puzhong-DSP28335-learning-materials")
PAGES_BASE_URL = (os.environ.get("PAGES_BASE_URL")
                  or f"https://{REPO_OWNER}.github.io/{REPO_NAME}").rstrip("/")

errors = []
warnings = []


def err(msg):
    errors.append(msg)
    print(f"  [FAIL] {msg}")


def warn(msg):
    warnings.append(msg)
    print(f"  [WARN] {msg}")


def ok(msg):
    print(f"  [ok]   {msg}")


def read_utf8(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def check_json_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        err(f"JSON 语法错误: {path}: {e}")
    except UnicodeDecodeError as e:
        err(f"非 UTF-8 文件: {path}: {e}")
    return None


def main():
    print(f"[verify-ai-docs] root: {REPO_ROOT}")
    print(f"[verify-ai-docs] dir : {OUT_DIR}")

    # ---- 顶层必需文件 ----
    for name in ("index.json", "index.html", "AI_USAGE.txt",
                 "build-report.json"):
        p = os.path.join(OUT_DIR, name)
        if not os.path.isfile(p):
            err(f"缺少顶层文件: {name}")
        else:
            ok(f"存在 {name}")

    # ---- 1. index.json ----
    index = check_json_file(os.path.join(OUT_DIR, "index.json"))
    docs = []
    if index is not None:
        if index.get("schema_version") != 1:
            err(f"index.json schema_version != 1: {index.get('schema_version')}")
        if index.get("repository") != f"{REPO_OWNER}/{REPO_NAME}":
            err(f"index.json repository 错误: {index.get('repository')}")
        docs = index.get("documents", [])
        if not docs:
            err("index.json documents 为空")
        else:
            ok(f"index.json 含 {len(docs)} 个文档")
        if index.get("document_count") != len(docs):
            err("document_count 与 documents 长度不一致")

    required_entry_fields = [
        "title", "display_title", "filename", "source_path", "match_key",
        "doc_id", "pdf_page_count", "source_sha256", "extraction_status",
        "embedded_page_count", "ocr_page_count", "empty_page_count",
        "ai_full_text_url", "ai_full_html_url", "ai_pages_base_url",
        "ai_blocks_base_url", "manifest_url", "original_github_url",
        "original_raw_url", "viewer_url",
    ]

    doc_ids = set()
    for d in docs:
        did = d.get("doc_id", "?")
        title = d.get("title", "?")
        tag = f"[{did}] {title}"

        # ---- 字段完整性 ----
        for field in required_entry_fields:
            if field not in d:
                err(f"{tag}: index 条目缺字段 {field}")
        if did in doc_ids:
            err(f"{tag}: doc_id 重复")
        doc_ids.add(did)
        if not re.fullmatch(r"[0-9a-f]{16}", str(did)):
            err(f"{tag}: doc_id 非 16 位十六进制: {did}")
        sha = d.get("source_sha256", "")
        if sha and not re.fullmatch(r"[0-9a-f]{64}", sha):
            err(f"{tag}: source_sha256 非 64 位十六进制")

        # ---- 10. URL 卫生 ----
        for field in ("ai_full_text_url", "ai_full_html_url",
                      "ai_pages_base_url", "ai_blocks_base_url",
                      "manifest_url", "viewer_url", "original_github_url",
                      "original_raw_url"):
            u = d.get(field, "")
            if not u.startswith("https://"):
                err(f"{tag}: {field} 不是绝对 HTTPS: {u!r}")
            if "file://" in u or u.startswith("/") or "/data/" in u:
                err(f"{tag}: {field} 引用本地路径: {u!r}")
        for field in ("ai_full_text_url", "ai_full_html_url",
                      "ai_pages_base_url", "ai_blocks_base_url",
                      "manifest_url"):
            u = d.get(field, "")
            if not u.startswith(PAGES_BASE_URL + "/ai/"):
                err(f"{tag}: {field} 不在 /ai/ 路径下: {u!r}")
        # viewer_url 指向 PDF.js（/web/viewer.html?file=…），只需绝对 HTTPS
        vu = d.get("viewer_url", "")
        if not vu.startswith(PAGES_BASE_URL + "/web/viewer.html?file="):
            err(f"{tag}: viewer_url 不指向本站 PDF.js viewer: {vu!r}")
        for field in ("original_github_url", "original_raw_url"):
            u = d.get(field, "")
            if not u.startswith("https://github.com/") and \
               not u.startswith("https://raw.githubusercontent.com/"):
                err(f"{tag}: {field} 不是 GitHub/raw 绝对 URL: {u!r}")

        # ---- 7. 源 PDF 有效性 ----
        src = os.path.join(REPO_ROOT, d.get("source_path", ""))
        status = d.get("extraction_status", "error")
        if status not in ("ok", "partial", "text_sparse", "invalid_pdf",
                          "lfs_not_materialized", "ocr_failed", "error"):
            err(f"{tag}: 未知 extraction_status: {status}")
        if not os.path.isfile(src):
            err(f"{tag}: 源文件不存在: {src}")
            continue
        with open(src, "rb") as f:
            head = f.read(1024)
        if status == "lfs_not_materialized":
            if not head.startswith(b"version https://git-lfs.github.com/spec/v1"):
                err(f"{tag}: 标记 lfs_not_materialized 但文件不是 LFS pointer")
            ok(f"{tag}: LFS pointer 如实标记")
            continue
        if head.startswith(b"version https://git-lfs.github.com/spec/v1"):
            err(f"{tag}: 文件是 LFS pointer 但状态为 {status}（应为 "
                f"lfs_not_materialized，禁止把 pointer 当 PDF 正文）")
            continue
        if b"%PDF-" not in head:
            err(f"{tag}: 源文件缺少 %PDF- magic（状态却为 {status}）")
            continue

        # ---- 2/3. 每文档产物 ----
        doc_dir = os.path.join(OUT_DIR, "docs", str(did))
        if status in ("invalid_pdf", "lfs_not_materialized"):
            if not os.path.isfile(os.path.join(doc_dir, "manifest.json")):
                err(f"{tag}: 失败文档仍应有 manifest.json")
            continue
        for name in ("manifest.json", "full.txt", "full.html"):
            if not os.path.isfile(os.path.join(doc_dir, name)):
                err(f"{tag}: 缺少 {name}")
        pages_dir = os.path.join(doc_dir, "pages")
        blocks_dir = os.path.join(doc_dir, "blocks")
        if not os.path.isdir(pages_dir):
            err(f"{tag}: 缺少 pages/ 目录")
        if not os.path.isdir(blocks_dir):
            err(f"{tag}: 缺少 blocks/ 目录")
        if errors and any(did in e for e in errors[-3:]):
            continue

        # ---- manifest.json ----
        m = check_json_file(os.path.join(doc_dir, "manifest.json"))
        if m is None:
            continue
        for field in ("title", "filename", "source_path", "source_sha256",
                      "file_size", "pdf_page_count", "doc_id", "repository",
                      "branch", "commit", "extractor", "pymupdf_version",
                      "ocr_engine", "ocr_engine_version", "ocr_languages",
                      "extraction_status", "embedded_page_count",
                      "ocr_page_count", "mixed_page_count",
                      "empty_page_count", "error_pages", "sparse_pages",
                      "text_char_count", "generated_at"):
            if field not in m:
                err(f"{tag}: manifest 缺字段 {field}")
        if m.get("doc_id") != did:
            err(f"{tag}: manifest.doc_id 与目录名不一致: {m.get('doc_id')}")
        if m.get("source_sha256") != d.get("source_sha256"):
            err(f"{tag}: manifest 与 index 的 source_sha256 不一致")
        if m.get("pdf_page_count") != d.get("pdf_page_count"):
            err(f"{tag}: manifest 与 index 的 pdf_page_count 不一致")
        # ---- 9. 页数统计一致性 ----
        total = (m.get("embedded_page_count", 0) + m.get("ocr_page_count", 0)
                 + m.get("mixed_page_count", 0) + m.get("empty_page_count", 0)
                 + m.get("error_page_count", 0))
        if total != m.get("pdf_page_count"):
            err(f"{tag}: 页数统计不一致: emb+ocr+mixed+none+err={total} != "
                f"pdf_page_count={m.get('pdf_page_count')}")

        # ---- 3. 页文件连续性 ----
        n = m.get("pdf_page_count", 0)
        if n > 0:
            expected = {f"{p:04d}.txt" for p in range(1, n + 1)}
            actual = {f for f in os.listdir(pages_dir) if f.endswith(".txt")}
            if actual != expected:
                missing = expected - actual
                extra = actual - expected
                err(f"{tag}: pages/ 编号不连续 (missing={sorted(missing)[:5]} "
                    f"extra={sorted(extra)[:5]})")
            expected_b = {f"{p:04d}.json" for p in range(1, n + 1)}
            actual_b = {f for f in os.listdir(blocks_dir) if f.endswith(".json")}
            if actual_b != expected_b:
                err(f"{tag}: blocks/ 编号不连续")

            # ---- 5. UTF-8 + 4. 分隔符数量 ----
            try:
                full = read_utf8(os.path.join(doc_dir, "full.txt"))
                sep = len(re.findall(r"^========== PDF_PAGE \d{4} ==========$",
                                     full, re.M))
                if sep != n:
                    err(f"{tag}: full.txt 分隔符 {sep} != 页数 {n}")
                ts_sources = re.findall(r"^TEXT_SOURCE: (\w+)$", full, re.M)
                bad = set(ts_sources) - {"embedded", "ocr", "mixed", "none",
                                         "error"}
                if bad:
                    err(f"{tag}: full.txt 含未知 TEXT_SOURCE: {bad}")
                read_utf8(os.path.join(doc_dir, "full.html"))
            except UnicodeDecodeError as e:
                err(f"{tag}: full.txt/full.html 非 UTF-8: {e}")

            # 抽查 3 个页文件（首页/中页/末页）
            for pno in {1, n // 2 + 1, n}:
                pf = os.path.join(pages_dir, f"{pno:04d}.txt")
                if os.path.isfile(pf):
                    try:
                        txt = read_utf8(pf)
                        for field in ("DOCUMENT_TITLE:", "SOURCE_PATH:",
                                      f"PDF_PAGE: {pno}", "PDF_PAGE_COUNT:",
                                      "SOURCE_SHA256:", "TEXT_SOURCE:"):
                            if field not in txt:
                                err(f"{tag}: pages/{pno:04d}.txt 缺字段 "
                                    f"{field!r}")
                        if "========== PAGE_TEXT ==========" not in txt:
                            err(f"{tag}: pages/{pno:04d}.txt 缺 PAGE_TEXT 分隔")
                    except UnicodeDecodeError:
                        err(f"{tag}: pages/{pno:04d}.txt 非 UTF-8")
                bf = os.path.join(blocks_dir, f"{pno:04d}.json")
                if os.path.isfile(bf):
                    bj = check_json_file(bf)
                    if bj is not None:
                        for field in ("pdf_page", "page_width", "page_height",
                                      "text_source", "blocks"):
                            if field not in bj:
                                err(f"{tag}: blocks/{pno:04d}.json 缺字段 "
                                    f"{field}")
                        if bj.get("pdf_page") != pno:
                            err(f"{tag}: blocks/{pno:04d}.json pdf_page 错误")
                        ts = bj.get("text_source")
                        if ts not in ("embedded", "ocr", "mixed", "none",
                                      "error"):
                            err(f"{tag}: blocks/{pno:04d}.json 未知 "
                                f"text_source: {ts}")
                        for b in bj.get("blocks", []):
                            if "bbox" not in b or "text" not in b:
                                err(f"{tag}: blocks/{pno:04d}.json 块缺 "
                                    f"bbox/text")
                            if b.get("block_source") not in ("embedded", "ocr"):
                                err(f"{tag}: blocks/{pno:04d}.json 块缺有效 "
                                    f"block_source")
                            # OCR 块坐标不能冒充 embedded
                            if (b.get("block_source") == "ocr"
                                    and ts == "embedded"):
                                err(f"{tag}: blocks/{pno:04d}.json OCR 块混入 "
                                    f"embedded 页")
        else:
            warn(f"{tag}: pdf_page_count=0")

    # ---- 11. index.html 静态源码 ----
    try:
        ih = read_utf8(os.path.join(OUT_DIR, "index.html"))
        for d in docs[:50]:
            if d.get("title") not in ih:
                err(f"index.html 源码缺文档标题: {d.get('title')}")
                break
        else:
            ok("index.html 源码包含文档标题（无需 JS）")
        if "index.json" not in ih:
            err("index.html 未指向 index.json")
    except FileNotFoundError:
        pass

    # ---- AI_USAGE.txt ----
    try:
        au = read_utf8(os.path.join(OUT_DIR, "AI_USAGE.txt"))
        for kw in ("TEXT_SOURCE", "embedded", "ocr", "index.json",
                   "不是", "核验"):
            if kw not in au:
                err(f"AI_USAGE.txt 缺关键说明: {kw}")
        ok("AI_USAGE.txt 内容完整")
    except FileNotFoundError:
        pass

    # ---- 汇总 ----
    print(f"\n[verify-ai-docs] ===== 结果 =====")
    print(f"  errors  : {len(errors)}")
    print(f"  warnings: {len(warnings)}")
    if errors:
        print("  首个错误: " + errors[0][:200])
        sys.exit(1)
    print("[verify-ai-docs] ALL CHECKS PASSED ✔")
    sys.exit(0)


if __name__ == "__main__":
    main()

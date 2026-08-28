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
 12. 导航图验证（Web Chat AI HTML-first hyperlink navigation）：
     A. README.md：/ai/ 是真实 Markdown hyperlink；AI_ACCESS.md 是真实 link；
        Web Chat AI 不再被描述为 raw-first；index.json 不再是 Web Chat AI
        唯一首入口（定位为 Agent / Script 机器入口）
     B. AI_ACCESS.md：/ai/ 是真实 hyperlink；HTML-first 规则存在；
        JSON 定位为机器 / Agent 路径
     C. viewer/index.html：静态源码存在 href="ai/"（不是 JS 动态插入）
     D. /ai/index.html：每个可读文档有 landing page 链接且目标文件存在
     E. 每文档 landing page（docs/<doc_id>/index.html）：
        full.txt / full.html / manifest.json / pages/index.html /
        blocks/index.html 均为真实 href 且目标文件存在；页面全部本站
        href 目标存在；无 <script>（核心内容不依赖 JS）
     F. pages/index.html：NNNN.txt 链接数量 == pdf_page_count，
        0001..N 全部存在，全部为真实静态链接
     G. blocks/index.html：NNNN.json 每页链接存在
     H. full.html：每页 Page TXT / Blocks JSON 链接目标存在

用法：python3 scripts/verify-ai-docs.py
退出码：0 = 全部通过；1 = 存在失败项（CI 会阻断部署）。
"""

import html as html_mod
import json
import os
import re
import sys
from urllib.parse import unquote

REPO_ROOT = os.environ.get("AI_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.environ.get("AI_OUT_DIR") or os.path.join(REPO_ROOT, "viewer", "ai")
SITE_ROOT = os.path.join(REPO_ROOT, "viewer")   # Pages 站点根 ↔ viewer/
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


# ------------------------------------------------ 导航图工具（12 A–H 用）--

def strip_scripts(html_text: str) -> str:
    """移除 <script> 块：静态验证只承认源码中真实存在的链接。"""
    return re.sub(r"<script\b[^>]*>.*?</script>", "", html_text,
                  flags=re.S | re.I)


def extract_static_hrefs(html_text: str):
    """提取静态 HTML 源码（去 script 后）中全部真实 <a href> 值。"""
    hrefs = []
    for m in re.finditer(r'<a\b[^>]*?\bhref\s*=\s*["\']([^"\']+)["\']',
                         strip_scripts(html_text), re.I):
        hrefs.append(html_mod.unescape(m.group(1)))
    return hrefs


def href_to_local_path(href: str, page_dir: str, site_root: str = None):
    """href → 本站本地文件路径。

    - 相对 href：相对 page_dir（当前 HTML 文件所在目录）解析（URL 解码后）；
    - 本站绝对 URL（PAGES_BASE_URL 开头）：剥离站点前缀后相对 site_root
      （默认 SITE_ROOT，即 Pages 站点根 ↔ viewer/）解析；
    - 外站 URL（github.com / raw.githubusercontent.com 等）与纯锚点：
      返回 None（不做本地存在性检查）。
    viewer/web/（PDF.js 资产）由 CI 构建时拉取、不落仓库，调用方应跳过
    其存在性检查（见 12E）。
    """
    if site_root is None:
        site_root = SITE_ROOT
    if not href or href.startswith("#"):
        return None
    h = href.split("#", 1)[0].split("?", 1)[0]
    if not h:
        return None
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", h):
        if h == PAGES_BASE_URL:
            h = ""
        elif h.startswith(PAGES_BASE_URL + "/"):
            h = h[len(PAGES_BASE_URL) + 1:]
        else:
            return None
        base = site_root
    else:
        base = page_dir
    if not h:
        return base
    return os.path.normpath(os.path.join(base, unquote(h)))


def check_repo_nav_docs():
    """12 A/B/C：仓库级导航入口文档（README / AI_ACCESS / viewer 首页）。"""
    print("[verify-ai-docs] ---- 12 A/B/C: 仓库入口文档导航 ----")

    # ---- A. README.md ----
    readme_p = os.path.join(REPO_ROOT, "README.md")
    if not os.path.isfile(readme_p):
        err("A: 缺少 README.md")
        return
    t = read_utf8(readme_p)
    m = re.search(r"\[[^\]]*\]\(\s*(https?://[^\s)]*?/ai/?)\s*\)", t)
    if not m:
        err("A: README.md 中 /ai/ 入口不是真实 Markdown hyperlink")
    else:
        ok(f"A: README.md /ai/ 为真实 Markdown hyperlink → {m.group(1)}")
    if not re.search(r"\[[^\]]*AI_ACCESS[^\]]*\]\(\s*AI_ACCESS\.md\s*\)", t):
        err("A: README.md 中 AI_ACCESS.md 不是真实 Markdown link")
    else:
        ok("A: README.md AI_ACCESS.md 为真实 Markdown link")
    if "Agent / 脚本获取原始 PDF" not in t:
        err("A: README.md 缺『Agent / 脚本获取原始 PDF』定位（raw 入口归属 Agent）")
    if re.search(r"AI\s*/\s*脚本获取原始\s*PDF", t):
        err("A: README.md 仍存在误导性标题『AI / 脚本获取原始 PDF』")
    bad_nav = False
    for line in t.splitlines():
        if "Web Chat AI" in line and "→" in line:
            if "index.json" in line:
                err(f"A: Web Chat AI 访问路径仍指向 index.json: "
                    f"{line.strip()[:90]}")
                bad_nav = True
            if "/ai/" not in line:
                err(f"A: Web Chat AI 访问路径未指向 /ai/ 静态 HTML: "
                    f"{line.strip()[:90]}")
                bad_nav = True
    if not bad_nav:
        ok("A: README.md 三种访问方式中 Web Chat AI 为 /ai/ HTML-first")
    idx_positions = [mm.start() for mm in re.finditer(r"index\.json", t)]
    if not idx_positions:
        err("A: README.md 未提及 index.json 机器入口")
    elif not any("Agent" in t[max(0, p - 300):p + 300]
                 for p in idx_positions):
        err("A: README.md 中 index.json 未定位为 Agent / Script 机器入口")
    else:
        ok("A: README.md index.json 定位为 Agent / Script 机器入口")

    # ---- B. AI_ACCESS.md ----
    acc_p = os.path.join(REPO_ROOT, "AI_ACCESS.md")
    if not os.path.isfile(acc_p):
        err("B: 缺少 AI_ACCESS.md")
    else:
        t = read_utf8(acc_p)
        m = re.search(r"\[[^\]]*\]\(\s*(https?://[^\s)]*?/ai/?)\s*\)", t)
        if not m:
            err("B: AI_ACCESS.md 中 /ai/ 入口不是真实 hyperlink")
        else:
            ok(f"B: AI_ACCESS.md /ai/ 为真实 hyperlink → {m.group(1)}")
        for kw, desc in (
                ("<a href>", "HTML-first 导航规则（真实 <a href>）"),
                ("不要求根据 JSON 字符串自行拼接 URL", "禁止自行拼 URL 声明"),
                ("机器接口", "index.json 机器接口定位"),
                ("Source of Truth", "原始 PDF Source of Truth 声明"),
                ("raw.githubusercontent.com", "raw PDF 非默认入口说明")):
            if kw not in t:
                err(f"B: AI_ACCESS.md 缺{desc}")
        if not re.search(r"Agent\s*/\s*Script", t):
            err("B: AI_ACCESS.md 未把 JSON 入口定位为 Agent / Script 路径")
        else:
            ok("B: AI_ACCESS.md JSON 定位为 Agent / Script 机器路径")

    # ---- C. viewer/index.html ----
    vp = os.path.join(REPO_ROOT, "viewer", "index.html")
    if not os.path.isfile(vp):
        err("C: 缺少 viewer/index.html")
    else:
        t = read_utf8(vp)
        static = strip_scripts(t)
        found = ('href="ai/"' in static) or ("href='ai/'" in static)
        if not found:
            err('C: viewer/index.html 静态源码缺少 <a href="ai/">'
                "（核心内容不能依赖 JS 动态插入）")
        else:
            ok('C: viewer/index.html 静态源码含 <a href="ai/">')


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
        "ai_doc_index_url", "ai_full_text_url", "ai_full_html_url",
        "ai_pages_base_url", "ai_pages_index_url", "ai_blocks_base_url",
        "ai_blocks_index_url", "manifest_url", "original_github_url",
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
        for field in ("ai_doc_index_url", "ai_full_text_url",
                      "ai_full_html_url", "ai_pages_base_url",
                      "ai_pages_index_url", "ai_blocks_base_url",
                      "ai_blocks_index_url", "manifest_url", "viewer_url",
                      "original_github_url", "original_raw_url"):
            u = d.get(field, "")
            if not u.startswith("https://"):
                err(f"{tag}: {field} 不是绝对 HTTPS: {u!r}")
            if "file://" in u or u.startswith("/") or "/data/" in u:
                err(f"{tag}: {field} 引用本地路径: {u!r}")
        for field in ("ai_doc_index_url", "ai_full_text_url",
                      "ai_full_html_url", "ai_pages_base_url",
                      "ai_pages_index_url", "ai_blocks_base_url",
                      "ai_blocks_index_url", "manifest_url"):
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

        # ---- 12E. landing page（docs/<doc_id>/index.html）真实链接 ----
        landing_p = os.path.join(doc_dir, "index.html")
        if not os.path.isfile(landing_p):
            err(f"{tag}: E: 缺 landing page index.html")
        else:
            try:
                lt = read_utf8(landing_p)
                if re.search(r"<script\b", lt, re.I):
                    err(f"{tag}: E: landing page 含 <script>（核心内容须无 JS）")
                lhrefs = extract_static_hrefs(lt)
                lpaths = {href_to_local_path(h, doc_dir) for h in lhrefs}
                for rel in ("full.txt", "full.html", "manifest.json",
                            "pages/index.html", "blocks/index.html"):
                    tp = os.path.normpath(os.path.join(doc_dir, rel))
                    if tp not in lpaths:
                        err(f'{tag}: E: landing 缺真实链接 href="{rel}"')
                for h in lhrefs:
                    lp = href_to_local_path(h, doc_dir)
                    if lp is None:
                        continue
                    try:
                        rel_site = os.path.relpath(lp, SITE_ROOT)
                    except ValueError:
                        rel_site = ""
                    # PDF.js 资产（viewer/web、viewer/build）由 CI 构建时拉取、
                    # 不落仓库，本地不做存在性检查
                    if rel_site.split(os.sep, 1)[0] in ("web", "build"):
                        continue
                    if not os.path.exists(lp):
                        err(f"{tag}: E: landing 链接目标不存在: {h}")
                ext_kinds = sum(
                    1 for h in lhrefs
                    if h.startswith("https://github.com/")
                    or h.startswith("https://raw.githubusercontent.com/"))
                if ext_kinds < 2:
                    err(f"{tag}: E: landing 缺原始 PDF（GitHub / raw）链接")
            except UnicodeDecodeError:
                err(f"{tag}: E: landing page 非 UTF-8")

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

            # ---- 12F/G. pages/ 与 blocks/ 目录页真实链接 ----
            for kind, ext in (("pages", "txt"), ("blocks", "json")):
                ip = os.path.join(doc_dir, kind, "index.html")
                if not os.path.isfile(ip):
                    err(f"{tag}: {kind}/index.html 缺失")
                    continue
                try:
                    it = read_utf8(ip)
                except UnicodeDecodeError:
                    err(f"{tag}: {kind}/index.html 非 UTF-8")
                    continue
                if re.search(r"<script\b", it, re.I):
                    err(f"{tag}: {kind}/index.html 含 <script>")
                pat = re.compile(rf"^(\d{{4}})\.{ext}$")
                nums = set()
                for h in extract_static_hrefs(it):
                    mm = pat.match(h.rsplit("/", 1)[-1])
                    if not mm:
                        continue
                    nums.add(int(mm.group(1)))
                    tgt = os.path.join(doc_dir, kind, h)
                    if not os.path.isfile(tgt):
                        err(f"{tag}: {kind}/index.html 链接目标不存在: {h}")
                expected_nums = set(range(1, n + 1))
                if nums != expected_nums:
                    miss = sorted(expected_nums - nums)[:5]
                    extra_n = sorted(nums - expected_nums)[:5]
                    err(f"{tag}: {kind}/index.html 页链接不全: "
                        f"count={len(nums)}/{n} missing={miss} extra={extra_n}")

            # ---- 12H. full.html 页级真实链接 ----
            fh_p = os.path.join(doc_dir, "full.html")
            if os.path.isfile(fh_p):
                try:
                    ft = strip_scripts(read_utf8(fh_p))
                    for kind, ext in (("pages", "txt"), ("blocks", "json")):
                        nums = set(int(x) for x in re.findall(
                            rf'href="{kind}/(\d{{4}})\.{ext}"', ft))
                        expected_nums = set(range(1, n + 1))
                        if nums != expected_nums:
                            miss = sorted(expected_nums - nums)[:5]
                            err(f"{tag}: H: full.html {kind}/ 链接不全: "
                                f"count={len(nums)}/{n} missing={miss}")
                        for pno in sorted(nums):
                            if not os.path.isfile(os.path.join(
                                    doc_dir, kind, f"{pno:04d}.{ext}")):
                                err(f"{tag}: H: full.html 链接目标不存在: "
                                    f"{kind}/{pno:04d}.{ext}")
                except UnicodeDecodeError:
                    pass  # 已在 5. UTF-8 检查中报告

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

    # ---- 11 + 12D. index.html 静态源码 + 每文档 landing 链接 ----
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
        # 12D：每个可读文档有 landing page 链接且目标存在
        ih_hrefs = extract_static_hrefs(ih)
        resolved = set()
        for h in ih_hrefs:
            lp = href_to_local_path(h, OUT_DIR)
            if lp:
                resolved.add(lp)
        want = {}
        for d in docs:
            if d.get("extraction_status") in ("invalid_pdf",
                                              "lfs_not_materialized"):
                continue
            want[os.path.normpath(
                os.path.join(OUT_DIR, "docs", str(d.get("doc_id")),
                             "index.html"))] = d
        d_ok = 0
        for lp, d in want.items():
            if lp not in resolved:
                err(f"D: index.html 缺 landing 链接: docs/{d.get('doc_id')}"
                    "/index.html")
            elif not os.path.isfile(lp):
                err(f"D: landing 文件不存在: docs/{d.get('doc_id')}"
                    "/index.html")
            else:
                d_ok += 1
        if d_ok == len(want) and want:
            ok(f"D: index.html landing 链接 {d_ok}/{len(want)} 且目标存在")
    except FileNotFoundError:
        err("缺少 viewer/ai/index.html")

    # ---- AI_USAGE.txt ----
    try:
        au = read_utf8(os.path.join(OUT_DIR, "AI_USAGE.txt"))
        for kw in ("TEXT_SOURCE", "embedded", "ocr", "index.json",
                   "不是", "核验", "<a href>",
                   "不要求根据 JSON 字符串自行拼接 URL", "landing page"):
            if kw not in au:
                err(f"AI_USAGE.txt 缺关键说明: {kw}")
        ok("AI_USAGE.txt 内容完整（HTML-first）")
    except FileNotFoundError:
        pass

    # ---- 12 A/B/C. 仓库入口文档导航（README / AI_ACCESS / viewer）----
    check_repo_nav_docs()

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

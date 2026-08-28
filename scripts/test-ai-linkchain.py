#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test-ai-linkchain.py — 真实 hyperlink 链验收（link-graph acceptance test）。

模拟 Web Chat AI 的导航模型：

    上一个网页中的真实 <a href> → GET → 下一个网页中的真实 <a href> → GET …

硬性规则（本脚本自身的实现约束，对应 spec §13）：
  - 除初始入口 URL 外，每一跳的 URL 都必须来自上一页 HTML 源码中
    实际解析出的 <a href>（解析在剥离 <script> 之后进行，只承认静态链接）；
  - 脚本不得用 base + doc_id + 页号自行拼接任何中间 URL；
  - 页号 / 文件名只允许用来「在已解析的 href 列表中选中」目标链接，
    不允许用来构造 URL。

默认对三本 DSP 专项书做全链验收（spec §14）：
  A. 普中DSP28335开发攻略.pdf
     黑盒问题：「第14章 F28335中断系统位于 PDF 物理第几页？」
     —— 答案必须从沿链接取得的 full.txt 实际检索得出。
  B. 手把手教你学DSP：基于TMS320F28335.pdf（464 页全扫描 OCR）
     —— 验证 page 0148 TXT（TEXT_SOURCE=ocr，含 7.1 PWM控制基本原理）
        与 blocks/0148.json。已知 doc_id=693c2ffdde161570 仅作交叉核对，
        链路本身仍由页面真实链接解析。
  C. 8--DSP相关资料/C语言加油站/C和指针.pdf
     —— doc_id 由页面实际查出（不硬编码）。

用法：
  python3 scripts/test-ai-linkchain.py
  python3 scripts/test-ai-linkchain.py --base http://localhost:8123 \
      --map https://yeblue1029.github.io/puzhong-DSP28335-learning-materials=http://localhost:8123

选项：
  --base URL     站点根（默认生产 Pages URL）
  --map A=B      绝对 URL 前缀重写（本地测试映射生产链接，可重复多次）
  --no-sweep     跳过全部文档 landing 链接的 HTTP 图扫描
  --deep-sweep   图扫描扩展到每文档 pages/blocks 目录页（较慢）

退出码：0 = 全部通过；1 = 存在失败项。
"""

import argparse
import html as html_mod
import re
import sys
import time
import urllib.request
from urllib.parse import urljoin

DEFAULT_BASE = "https://yeblue1029.github.io/puzhong-DSP28335-learning-materials"

HREF_RE = re.compile(r'<a\b[^>]*?\bhref\s*=\s*["\']([^"\']+)["\']', re.I)

BOOK_A_PATH = "普中DSP28335开发攻略.pdf"
BOOK_B_PATH = "手把手教你学DSP：基于TMS320F28335.pdf"
BOOK_B_KNOWN_DOC_ID = "693c2ffdde161570"   # 仅交叉核对；导航不依赖它
BOOK_C_PATH = "8--DSP相关资料/C语言加油站/C和指针.pdf"

failures = []
hops = 0


def check(cond, msg):
    if cond:
        print(f"    [ok] {msg}")
    else:
        print(f"    [FAIL] {msg}")
        failures.append(msg)
    return cond


def static_hrefs(html_text):
    """提取静态 HTML 源码（剥离 <script> 后）中的全部真实 <a href>。"""
    stripped = re.sub(r"<script\b[^>]*>.*?</script>", "", html_text,
                      flags=re.S | re.I)
    return [html_mod.unescape(m.group(1))
            for m in HREF_RE.finditer(stripped)]


def strip_scripts(html_text):
    return re.sub(r"<script\b[^>]*>.*?</script>", "", html_text,
                  flags=re.S | re.I)


class Client:
    """最小 Web Chat 模拟器：只做 GET + 从 HTML 解析 href。"""

    def __init__(self, base, maps=None, timeout=90):
        self.base = base.rstrip("/")
        self.maps = [(a.rstrip("/"), b.rstrip("/")) for a, b in (maps or [])]
        self.timeout = timeout

    def rewrite(self, url):
        for prod, local in self.maps:
            if url == prod:
                return local
            if url.startswith(prod + "/"):
                return local + url[len(prod):]
        return url

    def get(self, url, note=""):
        global hops
        target = self.rewrite(url)
        last = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    target,
                    headers={"User-Agent": "ai-linkchain-acceptance/1.0"})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    data = r.read()
                    final_url = r.geturl()
                    status = r.status
                hops += 1
                text = data.decode("utf-8")  # 站点文件均为 UTF-8
                print(f"  GET {url}  [{status}] {len(data)} B   # {note}")
                return text, final_url
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"GET {url} 失败: {last}")


def find_doc_landing_href(index_html, source_path):
    """在 /ai/ 文档列表中按 source_path 定位文档所在 <tr>，
    返回该行第一个真实 <a href>（即 landing page 链接）。"""
    for row in re.split(r"<tr\b", index_html)[1:]:
        if source_path in html_mod.unescape(row):
            m = HREF_RE.search(strip_scripts(row))
            if m:
                return html_mod.unescape(m.group(1))
    return None


def pick_href(hrefs, rel):
    """在已解析的 href 列表中选中与相对路径 rel 匹配的链接。
    这是「选中」而不是「构造」：rel 必须与页面真实 href 完全对应。"""
    for h in hrefs:
        if h == rel or h.endswith("/" + rel):
            return h
    return None


def pick_page_href(hrefs, pno, ext):
    """从已解析 href 列表中选中指定页号的链接（如 0148.txt / 0148.json）。"""
    want = f"{pno:04d}.{ext}"
    for h in hrefs:
        if h.rsplit("/", 1)[-1] == want:
            return h
    return None


def page_split(full_txt):
    """把 full.txt 切成 [(pno, content), ...]。"""
    parts = re.split(r"^========== PDF_PAGE (\d{4}) ==========$",
                     full_txt, flags=re.M)
    return [(int(parts[i]), parts[i + 1])
            for i in range(1, len(parts) - 1, 2)]


def doc_id_from_url(url):
    m = re.search(r"/ai/docs/([0-9a-f]{16})/", url)
    return m.group(1) if m else None


# ------------------------------------------------------------ 三本书专项 --

def test_book_a(cli, index_html, index_url):
    print("\n[A] 普中DSP28335开发攻略.pdf — "
          "黑盒问题：第14章 F28335中断系统位于 PDF 物理第几页？")
    landing = find_doc_landing_href(index_html, BOOK_A_PATH)
    if not check(landing is not None,
                 f"/ai/ 列表解析出《{BOOK_A_PATH}》landing href"):
        return
    lhtml, lurl = cli.get(urljoin(index_url, landing),
                          "HOP: /ai/ 列表行解析的 landing href")
    doc_id = doc_id_from_url(lurl)
    print(f"    landing doc_id = {doc_id}")
    lhrefs = static_hrefs(lhtml)

    # landing → full.txt（真实链接）
    full_href = pick_href(lhrefs, "full.txt")
    if not check(full_href is not None, "landing 页解析出 full.txt href"):
        return
    full_txt, _ = cli.get(urljoin(lurl, full_href),
                          "HOP: landing 页解析的 full.txt href")

    # 从实际取得的全文检索第14章（排除目录页点线行）
    target_pno, heading = None, None
    for pno, content in page_split(full_txt):
        for line in content.splitlines():
            if ("第14" in line and "中断系统" in line
                    and "....." not in line):
                target_pno, heading = pno, line.strip()
                break
        if target_pno:
            break
    if not check(target_pno is not None, "full.txt 检索到第14章正文标题"):
        return
    print(f"    >> 实际检索结果：第14章 F28335中断系统 → PDF 物理第 "
          f"{target_pno:04d} 页（标题行：{heading[:40]}）")

    # landing → pages/index.html → 指定页 TXT（全链真实链接）
    pidx_href = pick_href(lhrefs, "pages/index.html")
    if not check(pidx_href is not None, "landing 页解析出 pages/index.html"):
        return
    phtml, purl = cli.get(urljoin(lurl, pidx_href),
                          "HOP: landing 页解析的 pages/index.html href")
    phrefs = static_hrefs(phtml)
    page_href = pick_page_href(phrefs, target_pno, "txt")
    if not check(page_href is not None,
                 f"pages/index.html 解析出第 {target_pno:04d} 页 TXT href"):
        return
    ptxt, _ = cli.get(urljoin(purl, page_href),
                      f"HOP: pages/index.html 解析的 {target_pno:04d}.txt href")
    check(f"PDF_PAGE: {target_pno}" in ptxt,
          f"pages/{target_pno:04d}.txt 页号标记一致")
    check("TEXT_SOURCE: embedded" in ptxt,
          f"pages/{target_pno:04d}.txt TEXT_SOURCE=embedded（本书无 OCR 页）")

    # landing → blocks/index.html → 对应页 JSON
    bidx_href = pick_href(lhrefs, "blocks/index.html")
    if check(bidx_href is not None, "landing 页解析出 blocks/index.html"):
        bhtml, burl = cli.get(urljoin(lurl, bidx_href),
                              "HOP: landing 页解析的 blocks/index.html href")
        bhref = pick_page_href(static_hrefs(bhtml), target_pno, "json")
        if check(bhref is not None,
                 f"blocks/index.html 解析出 {target_pno:04d}.json href"):
            bj, _ = cli.get(urljoin(burl, bhref),
                            f"HOP: blocks/index.html 解析的 "
                            f"{target_pno:04d}.json href")
            check(f'"pdf_page": {target_pno}' in bj,
                  f"blocks/{target_pno:04d}.json pdf_page 一致")


def test_book_b(cli, index_html, index_url):
    print("\n[B] 手把手教你学DSP：基于TMS320F28335.pdf — "
          "464 页全扫描 OCR，验证 page 0148（7.1 PWM控制基本原理）")
    landing = find_doc_landing_href(index_html, BOOK_B_PATH)
    if not check(landing is not None,
                 f"/ai/ 列表解析出《{BOOK_B_PATH}》landing href"):
        return
    check(BOOK_B_KNOWN_DOC_ID in landing,
          f"landing href 含已知 doc_id {BOOK_B_KNOWN_DOC_ID}（交叉核对）")
    lhtml, lurl = cli.get(urljoin(index_url, landing),
                          "HOP: /ai/ 列表行解析的 landing href")
    lhrefs = static_hrefs(lhtml)

    # landing → full.txt
    full_href = pick_href(lhrefs, "full.txt")
    if check(full_href is not None, "landing 页解析出 full.txt href"):
        full_txt, _ = cli.get(urljoin(lurl, full_href),
                              "HOP: landing 页解析的 full.txt href")
        check("手把手教你学DSP：基于TMS320F28335" in full_txt,
              "full.txt 文档标题一致")
        pages = page_split(full_txt)
        check(len(pages) == 464, f"full.txt 含 464 页分隔符（实际 {len(pages)}）")

    # landing → pages/index.html → 0148.txt
    pidx_href = pick_href(lhrefs, "pages/index.html")
    if not check(pidx_href is not None, "landing 页解析出 pages/index.html"):
        return
    phtml, purl = cli.get(urljoin(lurl, pidx_href),
                          "HOP: landing 页解析的 pages/index.html href")
    phrefs = static_hrefs(phtml)
    check(len([h for h in phrefs
               if re.fullmatch(r"\d{4}\.txt", h.rsplit("/", 1)[-1])]) == 464,
          "pages/index.html 含 464 个真实页链接")
    page_href = pick_page_href(phrefs, 148, "txt")
    if not check(page_href is not None,
                 "pages/index.html 解析出 0148.txt href"):
        return
    ptxt, _ = cli.get(urljoin(purl, page_href),
                      "HOP: pages/index.html 解析的 0148.txt href")
    check("PDF_PAGE: 148" in ptxt, "0148.txt 页号标记一致")
    check("TEXT_SOURCE: ocr" in ptxt, "0148.txt TEXT_SOURCE=ocr")
    check("7.1 PWM控制基本原理" in ptxt, "0148.txt 含「7.1 PWM控制基本原理」")

    # landing → blocks/index.html → 0148.json
    bidx_href = pick_href(lhrefs, "blocks/index.html")
    if check(bidx_href is not None, "landing 页解析出 blocks/index.html"):
        bhtml, burl = cli.get(urljoin(lurl, bidx_href),
                              "HOP: landing 页解析的 blocks/index.html href")
        bhref = pick_page_href(static_hrefs(bhtml), 148, "json")
        if check(bhref is not None, "blocks/index.html 解析出 0148.json href"):
            bj, _ = cli.get(urljoin(burl, bhref),
                            "HOP: blocks/index.html 解析的 0148.json href")
            check('"pdf_page": 148' in bj, "0148.json pdf_page=148")
            check('"text_source": "ocr"' in bj, "0148.json text_source=ocr")

    # landing → full.html（页级链接）
    fh_href = pick_href(lhrefs, "full.html")
    if check(fh_href is not None, "landing 页解析出 full.html href"):
        fhtml, _ = cli.get(urljoin(lurl, fh_href),
                           "HOP: landing 页解析的 full.html href")
        check('href="pages/0148.txt"' in fhtml,
              "full.html 含 0148.txt 真实链接")
        check('href="blocks/0148.json"' in fhtml,
              "full.html 含 0148.json 真实链接")
        check('id="pdf-page-0148"' in fhtml, "full.html 含 0148 页锚点")


def test_book_c(cli, index_html, index_url):
    print("\n[C] 8--DSP相关资料/C语言加油站/C和指针.pdf — doc_id 由页面实际查出")
    landing = find_doc_landing_href(index_html, BOOK_C_PATH)
    if not check(landing is not None, f"/ai/ 列表解析出《C和指针.pdf》landing href"):
        return
    lhtml, lurl = cli.get(urljoin(index_url, landing),
                          "HOP: /ai/ 列表行解析的 landing href")
    doc_id = doc_id_from_url(lurl)
    print(f"    >> 实际查得 doc_id = {doc_id}（未硬编码）")
    lhrefs = static_hrefs(lhtml)

    full_href = pick_href(lhrefs, "full.txt")
    if check(full_href is not None, "landing 页解析出 full.txt href"):
        full_txt, _ = cli.get(urljoin(lurl, full_href),
                              "HOP: landing 页解析的 full.txt href")
        check(BOOK_C_PATH in full_txt, "full.txt SOURCE_PATH 一致")

    pidx_href = pick_href(lhrefs, "pages/index.html")
    if check(pidx_href is not None, "landing 页解析出 pages/index.html"):
        phtml, purl = cli.get(urljoin(lurl, pidx_href),
                              "HOP: landing 页解析的 pages/index.html href")
        phrefs = static_hrefs(phtml)
        for pno in (1, 471):  # 首页 + 末页
            page_href = pick_page_href(phrefs, pno, "txt")
            if check(page_href is not None,
                     f"pages/index.html 解析出 {pno:04d}.txt href"):
                ptxt, _ = cli.get(urljoin(purl, page_href),
                                  f"HOP: pages/index.html 解析的 "
                                  f"{pno:04d}.txt href")
                check(f"PDF_PAGE: {pno}" in ptxt,
                      f"pages/{pno:04d}.txt 页号标记一致")

    bidx_href = pick_href(lhrefs, "blocks/index.html")
    if check(bidx_href is not None, "landing 页解析出 blocks/index.html"):
        bhtml, burl = cli.get(urljoin(lurl, bidx_href),
                              "HOP: landing 页解析的 blocks/index.html href")
        bhref = pick_page_href(static_hrefs(bhtml), 1, "json")
        if check(bhref is not None, "blocks/index.html 解析出 0001.json href"):
            bj, _ = cli.get(urljoin(burl, bhref),
                            "HOP: blocks/index.html 解析的 0001.json href")
            check('"pdf_page": 1' in bj, "0001.json pdf_page=1")


# ------------------------------------------------------------ 图扫描 ------

def sweep(cli, index_html, index_url, deep=False):
    print(f"\n[sweep] 扫描 /ai/ 列表中全部文档 landing 链接"
          f"{'（含 pages/blocks 目录页）' if deep else ''}")
    landings = []
    for row in re.split(r"<tr\b", index_html)[1:]:
        m = HREF_RE.search(strip_scripts(row))
        if m:
            h = html_mod.unescape(m.group(1))
            if h not in landings:
                landings.append(h)
    print(f"  文档 landing 链接总数：{len(landings)}")
    if not check(len(landings) >= 370, "landing 链接数 >= 370"):
        return

    bad = 0
    required = ("full.txt", "full.html", "manifest.json",
                "pages/index.html", "blocks/index.html")
    for i, landing in enumerate(landings, 1):
        try:
            lhtml, lurl = cli.get(urljoin(index_url, landing),
                                  f"sweep {i}/{len(landings)} landing")
        except RuntimeError as e:
            print(f"    [FAIL] {e}")
            failures.append(str(e))
            bad += 1
            continue
        lhrefs = static_hrefs(lhtml)
        missing = [rel for rel in required
                   if pick_href(lhrefs, rel) is None]
        if missing:
            failures.append(f"landing {landing} 缺链接: {missing}")
            bad += 1
        elif deep:
            for rel in ("pages/index.html", "blocks/index.html"):
                ih = pick_href(lhrefs, rel)
                if not ih:
                    continue
                dhtml, _ = cli.get(urljoin(lurl, ih),
                                   f"sweep {i} {rel}")
                n = len([h for h in static_hrefs(dhtml)
                         if re.fullmatch(r"\d{4}\.(?:txt|json)",
                                         h.rsplit("/", 1)[-1])])
                if n == 0:
                    failures.append(f"{landing} {rel} 无页链接")
                    bad += 1
    check(bad == 0, f"全部 landing 链接可达且含 5 个必需 href（异常 {bad}）")


# ---------------------------------------------------------------- 主流程 --

def main():
    ap = argparse.ArgumentParser(description="AI Reading Path link-chain test")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--map", action="append", default=[],
                    help="PROD_PREFIX=LOCAL_PREFIX（可重复）")
    ap.add_argument("--no-sweep", action="store_true")
    ap.add_argument("--deep-sweep", action="store_true")
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

    maps = []
    for m in args.map:
        if "=" not in m:
            sys.exit(f"--map 需要 A=B 形式: {m!r}")
        a, b = m.split("=", 1)
        maps.append((a, b))
    cli = Client(args.base, maps, args.timeout)
    base = cli.base

    print(f"[linkchain] base: {base}")
    print(f"[linkchain] 规则：每一跳 URL 均来自上一页真实 <a href>（禁止自行拼接）")

    # ---- HOP 0：Pages 根 → 静态 ai/ 链接（README → 根站 → AI Reading Path）----
    print("\n[0] Pages 根站点：验证静态 ai/ 入口链接")
    try:
        rhtml, _ = cli.get(base + "/", "入口：README 指向的 Pages 根")
        check('href="ai/"' in strip_scripts(rhtml),
              "根站静态源码含 <a href=\"ai/\">（非 JS 插入）")
    except RuntimeError as e:
        print(f"    [WARN] {e}（根站检查跳过）")

    # ---- HOP 1：/ai/ 文档列表 ----
    print("\n[1] AI Reading Path 文档列表")
    index_html, index_url = cli.get(base + "/ai/",
                                    "入口：AI_ACCESS.md 指向的 /ai/")
    check("AI Reading Path" in index_html, "/ai/ 为 AI Reading Path 文档列表")
    landing_count = len([r for r in re.split(r"<tr\b", index_html)[1:]])
    check(landing_count >= 370, f"文档列表含 {landing_count} 行（>= 370）")

    # ---- 三本书全链验收 ----
    test_book_a(cli, index_html, index_url)
    test_book_b(cli, index_html, index_url)
    test_book_c(cli, index_html, index_url)

    # ---- 全站 landing 图扫描 ----
    if not args.no_sweep:
        sweep(cli, index_html, index_url, deep=args.deep_sweep)

    # ---- 汇总 ----
    print(f"\n[linkchain] ===== 结果 =====")
    print(f"  HTTP GET 总跳数: {hops}")
    print(f"  failures: {len(failures)}")
    if failures:
        for f in failures[:10]:
            print(f"    - {f[:160]}")
        sys.exit(1)
    print("[linkchain] LINK-CHAIN ACCEPTANCE PASSED ✔ "
          "（全部 URL 来自真实 hyperlink，未自行拼接）")
    sys.exit(0)


if __name__ == "__main__":
    main()

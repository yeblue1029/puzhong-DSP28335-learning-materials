# Puzhong DSP28335 Learning Materials

本仓库整理了普中 DSP28335 开发板相关的学习资料、实验程序、
教学课件、原理图和芯片文档。

## 仓库主要内容

- `1--用户必看`：开发板使用说明和注意事项
- `2--开发板原理图`：DSP28335 开发板硬件原理图
- `3--手把手开发讲解视频`：配套教学 PPT 和课件资料
- `4--实验程序`：Code Composer Studio 实验工程和源代码
- `5--开发工具`：实验所需辅助工具的名称和获取说明
- `6--芯片资料`：TMS320F28335 芯片数据手册和相关资料
- `7--SD卡根目录文件`：实验所需的 SD 卡文件
- `8--DSP相关资料`：DSP、C 语言及控制算法参考资料
- `普中DSP28335开发攻略.pdf`：开发板配套学习手册
-  `手把手教你学DSP：基于TMS320F28335.pdf`：研旭开发板配套学习手册

## 📚 DSP28335 PDF 在线文档中心

仓库内全部 PDF 都可以在浏览器中直接在线阅读（翻页 / 缩放 / 文本搜索 / 缩略图 / 下载 / 打印），同时为每个文档保留可被云端 AI 与脚本直接获取的**原始 PDF 链接**。

**📖 PDF 文档中心**（自动索引全部 PDF，可搜索 / 按目录分类）：

https://yeblue1029.github.io/puzhong-DSP28335-learning-materials/

示例在线阅读（基于 Mozilla PDF.js，跨域读取 GitHub raw，无需登录）：

- 📖 [普中 DSP28335 开发攻略](https://yeblue1029.github.io/puzhong-DSP28335-learning-materials/web/viewer.html?file=https%3A%2F%2Fraw.githubusercontent.com%2Fyeblue1029%2Fpuzhong-DSP28335-learning-materials%2Fmain%2F%25E6%2599%25AE%25E4%25B8%25ADDSP28335%25E5%25BC%2580%25E5%258F%2591%25E6%2594%25BB%25E7%2595%25A5.pdf)
- 📖 [手把手教你学 DSP：基于 TMS320F28335](https://yeblue1029.github.io/puzhong-DSP28335-learning-materials/web/viewer.html?file=https%3A%2F%2Fraw.githubusercontent.com%2Fyeblue1029%2Fpuzhong-DSP28335-learning-materials%2Fmain%2F%25E6%2589%258B%25E6%258A%258A%25E6%2589%258B%25E6%2595%2599%25E4%25BD%25A0%25E5%25AD%25A6DSP%25EF%25BC%259A%25E5%259F%25BA%25E4%25BA%258ETMS320F28335.pdf)
- 📖 [TMS320F28335 数据手册（中文版）](https://yeblue1029.github.io/puzhong-DSP28335-learning-materials/web/viewer.html?file=https%3A%2F%2Fraw.githubusercontent.com%2Fyeblue1029%2Fpuzhong-DSP28335-learning-materials%2Fmain%2F6--%25E8%258A%25AF%25E7%2589%2587%25E8%25B5%2584%25E6%2596%2599%2F%25E5%25BC%2580%25E5%258F%2591%25E6%259D%25BF%25E8%258A%25AF%25E7%2589%2587%25E6%2595%25B0%25E6%258D%25AE%25E6%2589%258B%25E5%2586%258C%2Ftms320f28335%28%25E4%25B8%25AD%25E6%2596%2587%25E7%2589%2588%29.pdf)

**🤖 AI / 脚本获取原始 PDF**：每个 PDF 的原始文件托管在 `raw.githubusercontent.com`，无需 JavaScript 即可经 HTTP 获取，返回真实 PDF 二进制（已开启 CORS、支持 Range 分段请求）：

```bash
curl -L "https://raw.githubusercontent.com/yeblue1029/puzhong-DSP28335-learning-materials/main/%E6%99%AE%E4%B8%ADDSP28335%E5%BC%80%E5%8F%91%E6%94%BB%E7%95%A5.pdf" -o manual.pdf
file manual.pdf   # -> PDF document
```

完整清单见 [`viewer/pdf-index.json`](viewer/pdf-index.json)，包含每个 PDF 的 `viewer_url` / `raw_url` / `github_url`。架构与维护说明见 [`viewer/MAINTENANCE.md`](viewer/MAINTENANCE.md)。

## 🤖 AI / LLM 文档读取（Web Chat AI 专用入口）

ChatGPT / Gemini / DeepSeek 等网页聊天 AI 可能无法可靠读取 raw PDF 二进制，或无法执行 PDF.js。
为此本仓库提供一套**AI Reading Path**：由 CI 从原始 PDF 自动派生的纯文本层
（原生文字优先 + 扫描页 OCR 兜底，每页标记 `TEXT_SOURCE`）。

**机器入口（纯 JSON，无需 JavaScript）**：

```
https://yeblue1029.github.io/puzhong-DSP28335-learning-materials/ai/index.json
```

**人类可读入口**：`https://yeblue1029.github.io/puzhong-DSP28335-learning-materials/ai/`

三种访问方式：

```text
Human        → PDF.js Viewer（在线阅读，体验不变）
Web Chat AI  → /ai/index.json → ai_full_text_url / ai_pages_base_url / ai_blocks_base_url
Agent/Script → original_raw_url（raw.githubusercontent.com 原始 PDF）
```

⚠️ **Web Chat AI 不再默认 raw PDF 优先**：请先读 [`AI_ACCESS.md`](AI_ACCESS.md)
（仓库根目录，AI 访问契约：文本来源等级 / OCR 警示 / 失败规则），
再进入 `/ai/`。OCR 页（`TEXT_SOURCE: ocr`）为机器识别文本，不是"原文等价物"，
关键结论应回原始 PDF 核验。

## 开发环境

- Target device: TMS320F28335
- IDE: Code Composer Studio
- Languages: C / Assembly

## 文件说明

为了控制仓库体积并遵守软件版权要求，本仓库未上传：

- 第三方可执行程序
- DLL 和安装程序
- 破解软件
- 压缩文件
- 实际视频文件
- CCS 编译输出
- 超过 GitHub 普通文件限制的大型文件

教学 PPT、实验源码、原理图、芯片文档和学习资料会正常上传。

## 版权说明

部分文档、课件和示例资料来自芯片厂商、开发板厂商或相关作者，
版权归各自权利人所有。

本仓库仅用于个人学习、技术研究和资料整理。

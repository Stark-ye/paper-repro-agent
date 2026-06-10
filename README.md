# Paper Repro Agent

轻量化论文调研与复现 Agent。它把 `paper-repro-orchestrator` 的中文论文复现流程做成一个可运行 CLI：按阶段读取 skill 参考模块，生成阶段产物、状态文件、记忆文件和人工审查包。

第一版默认使用脚手架模式，不依赖 API key；需要更强的论文精读和工具调用能力时，可以通过 `--llm` 启用 LangChain + OpenAI 兼容模型。

## 安装

开发安装：

```bash
pip install -e .[dev,pdf]
```

只作为工具使用：

```bash
pip install -e .[pdf]
```

Windows PowerShell 如果不安装为命令，也可以用：

```powershell
$env:PYTHONPATH="src"
python -m paper_repro_agent.cli --help
```

## 基本调用

每次只执行一个阶段，阶段完成后生成审查包并停止。确认结果后，再运行下一阶段。

```bash
paper-repro run --paper "<PDF|URL|论文标题>" --stage literature
paper-repro run --stage reading
paper-repro run --stage baseline
paper-repro run --stage core
paper-repro run --stage figures
paper-repro run --stage validation
```

推荐为每篇论文设置独立运行目录，避免不同论文的产物混在一起：

```bash
paper-repro run --paper "tests/2025 - Nadav Cohen - Adaptive Kalman-Informed Transformer.pdf" --stage literature --run-dir tests/akit_pdf_smoke
paper-repro run --stage reading --run-dir tests/akit_pdf_smoke
paper-repro run --stage baseline --run-dir tests/akit_pdf_smoke
paper-repro run --stage figures --run-dir tests/akit_pdf_smoke
paper-repro run --stage validation --run-dir tests/akit_pdf_smoke
```

查看状态：

```bash
paper-repro state --run-dir tests/akit_pdf_smoke
```

## 产物目录

如果不指定 `--run-dir`，默认写入项目根目录下的 `outputs/` 和 `reproduction/`。

如果指定 `--run-dir tests/akit_pdf_smoke`，产物会写入：

- `tests/akit_pdf_smoke/outputs/state.json`
- `tests/akit_pdf_smoke/outputs/memory.md`
- `tests/akit_pdf_smoke/outputs/stage_notes.md`
- `tests/akit_pdf_smoke/outputs/literature_sources.md`
- `tests/akit_pdf_smoke/outputs/reproduction_spec.md`
- `tests/akit_pdf_smoke/outputs/report.md`
- `tests/akit_pdf_smoke/reproduction/run_reproduction.py`

`memory.md` 使用增量摘要记忆、反思式压缩和结构化槽位更新，记录用户偏好、阶段决策和后续约束。

## LLM 模式

脚手架模式能验证流程和产物结构，但不会伪造论文结论。若要让 Agent 基于论文内容生成更完整的分析，可配置 OpenAI 兼容模型并加 `--llm`：

```powershell
$env:PAPER_REPRO_API_KEY="your_api_key"
$env:PAPER_REPRO_MODEL="gpt-4.1-mini"
$env:PAPER_REPRO_BASE_URL="https://api.openai.com/v1"
paper-repro run --paper "tests/2025 - Nadav Cohen - Adaptive Kalman-Informed Transformer.pdf" --stage literature --run-dir tests/akit_pdf_smoke --llm
```

也可使用通用 OpenAI 环境变量：

```bash
OPENAI_API_KEY=your_api_key OPENAI_BASE_URL=https://api.openai.com/v1 paper-repro run --paper "<paper>" --stage literature --llm
```

## AKIT PDF 冒烟测试

仓库内包含测试论文：

```text
tests/2025 - Nadav Cohen - Adaptive Kalman-Informed Transformer.pdf
```

已验证脚手架模式可在 `tests/akit_pdf_smoke/` 下生成完整阶段产物。重新运行测试：

```powershell
$env:PYTHONPATH="src"
python -m paper_repro_agent.cli run --paper "tests/2025 - Nadav Cohen - Adaptive Kalman-Informed Transformer.pdf" --stage literature --run-dir tests/akit_pdf_smoke
python -m paper_repro_agent.cli run --stage reading --run-dir tests/akit_pdf_smoke
python -m paper_repro_agent.cli run --stage baseline --run-dir tests/akit_pdf_smoke
python tests/akit_pdf_smoke/reproduction/run_reproduction.py --stage baseline --outputs tests/akit_pdf_smoke/outputs
python -m paper_repro_agent.cli run --stage figures --run-dir tests/akit_pdf_smoke
python -m paper_repro_agent.cli run --stage validation --run-dir tests/akit_pdf_smoke
```

## 测试

```bash
python -m pytest -q
```

当前基础测试覆盖 CLI 参数解析、状态读写、reference 加载、审查包生成和 `--run-dir` 阶段产物写入。

## 上传到 GitHub

第一次发布到 GitHub：

```bash
git add .
git commit -m "Build lightweight paper reproduction agent"
git branch -M main
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```

如果已经配置过远程仓库：

```bash
git add .
git commit -m "Build lightweight paper reproduction agent"
git push
```

发布前检查：

```bash
python -m pytest -q
git status --short
```

## 他人安装

从 GitHub 直接安装：

```bash
pip install "paper-repro-agent[pdf] @ git+https://github.com/<user>/<repo>.git"
```

安装开发依赖：

```bash
pip install "paper-repro-agent[dev,pdf] @ git+https://github.com/<user>/<repo>.git"
```

安装后调用：

```bash
paper-repro run --paper "<PDF|URL|论文标题>" --stage literature --run-dir runs/demo
paper-repro run --stage reading --run-dir runs/demo
```

## 发布文件

- `.gitignore`：排除缓存、虚拟环境、本地密钥和默认运行产物。
- `LICENSE`：MIT License。
- `.github/workflows/tests.yml`：GitHub Actions 中运行 `python -m pytest -q`。

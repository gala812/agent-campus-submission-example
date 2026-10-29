# 企业知识问答 Agent

**小影校招 AI Agent 考核 · 第 3 题**

员工提问后，模型检索制度或产品资料、读取原文，再根据结果补查、追问或给出带引用的答案。遇到相互冲突的制度时列出双方证据；资料不足时明确说明缺口。

所有材料均为合成数据；“星剪”是虚构产品，不代表小影的真实产品功能。提供真实 DeepSeek 工具调用入口及完全离线的 Mock 入口。**Mock 的固定规则只用于流程验证，不证明模型的 ReAct 决策效果。**

## 评审入口

1. [真实模型验收汇总](examples/live/summary.md)：查看实际运行结果。
2. 比较 [正常问答 Trace](examples/live/normal/trace.md)、[冲突补查 Trace](examples/live/conflict/trace.md) 和 [工具失败恢复 Trace](examples/live/tool_failure_recovery/trace.md)。
3. 查看 [自动化测试结果](examples/test-results/summary.json)、[评估与失败分析](docs/03-evaluation.md)。
4. 按下方命令运行离线入口；配置密钥后可独立复现真实模型流程。
5. 查看 [候选人实际操作实验](examples/personal/README.md)：冲突、资料修改前后对照、一次失败注入。
6. 查看 [AI 使用记录](docs/04-ai-usage.md) 与 [提交信息](SUBMISSION.md)。

## 环境与安装

- Python 3.8+；新环境建议 Python 3.11+。
- 仅依赖 Python 标准库，不需要模型框架、向量数据库或第三方包。
- 本地验证的具体版本及测试时间记录于 `examples/test-results/summary.json`。
- 首次代码提交已通过 Python 3.8 / 3.11 / 3.13 的 GitHub 离线 CI，见 [实测记录](examples/github-ci.json)；后续提交以对应工作流结果为准。

在项目根目录执行：

```bash
python --version
python -m pip install -r requirements.txt
python run.py ask --mode mock --question "星剪支持自动生成字幕吗？" --out runs/demo
```

依赖文件为空是有意的；第二条命令无需下载运行库，可以省略。命令默认将 `input.json`、`output.json`、完整 `trace.json` 和可读 `trace.md` 保存到 `--out`。`ask` 会覆盖该输出目录中的同名文件，保留多次记录时使用不同目录。`runs/` 默认不入 Git；交付材料放在 `examples/`。

## 真实模型运行：DeepSeek

将 `.env.example` 复制为 `.env`，在本机编辑：

```dotenv
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-flash
LLM_API_KEY=在本机填写密钥
LLM_TIMEOUT_SECONDS=45
```

模型名可改为账号可用的支持工具调用的模型。配置中的模型与接口参考 [DeepSeek 官方快速开始](https://api-docs.deepseek.com/) 和 [工具调用文档](https://api-docs.deepseek.com/guides/tool_calls/)（查阅日期：2026-10-29）。代码对 DeepSeek 官方域名显式关闭 thinking，使用非思考模式；不保存内部推理文本。切换其他兼容服务时需验证其工具调用协议，不保证所有服务即插即用。

`.env` 已被 Git 忽略，环境变量优先于 `.env`。`check-config` 仅检查本地配置，不输出密钥，也不验证余额或网络连通性。真实运行会消耗模型 API 额度。

```bash
python run.py check-config
python run.py ask --mode live --question "报销期限是多久？" --out runs/live-conflict
python run.py evaluate --mode live --out runs/live-review
```

真实模式失败时返回 `model_error`，**不会自动切换成 Mock**。HTTP 状态如 `model_http_401`、`model_http_402`、`model_http_429` 会被记录，但上游响应正文和认证头不会写入日志。网络或超时错误返回 `model_network_error_or_timeout`。

## 输入、输出与历史

```json
{
  "question": "那它能导出什么格式？",
  "history": [
    {"role": "user", "content": "星剪支持字幕吗？"},
    {"role": "assistant", "content": "支持自动生成中文字幕。"}
  ]
}
```

```bash
python run.py ask --mode mock --input examples/mock/followup/input.json --out runs/followup
```

历史用于理解指代；历史答案不能代替本轮原文证据。CLI不自动持久化聊天会话，调用方负责传入history。

输出包含 `status`、`answer`、`citations`（文档 ID、版本日期、逐字原文）、`gaps`、`conflicts`。引用出现在回答中的 `[D01]` 等标记用于对应来源。完整 Trace 另含运行模式、模型、知识库与提示词 SHA256、模型调用次数、工具次数、步骤参数、观察结果、简要动作依据及下一动作。

| 状态 | 含义 |
|---|---|
| `answered` | 有已读取的证据，未报告未解决缺口或冲突 |
| `needs_clarification` | 问题缺少对象或制度冲突，需要用户确认 |
| `insufficient_evidence` | 无资料或资料不足以回答全部问题 |
| `tool_error` | 模型观察到业务工具错误后明确停止 |
| `model_error` | 模型接口失败或连续两次输出无效协议 |
| `incomplete_limit` | 达到决策步数或工具调用上限，任务未完成 |

`ask` 退出码：0=已回答；2=已执行但需要澄清、证据不足、失败或达到上限；1=配置、输入或文件错误。评估命令按“预期行为是否满足”返回0/1，所以正确拒答的用例可以通过。

## 测试与复现

```bash
python scripts/run_tests.py
python run.py evaluate --mode mock --out runs/mock-review
python run.py retrieval-eval --out runs/retrieval-review.json
```

也可以直接运行 `python -m unittest discover -s tests -v`。带持久化结果的测试入口会更新 `examples/test-results/`。

仅复现部分真实模型用例：

```bash
python run.py evaluate --mode live --case normal,conflict,tool_failure_recovery --out runs/live-short
```

覆盖原有评估目录需显式加 `--overwrite`；建议为新测评使用新目录，保留原始记录。

改变工具结果或触发边界：

```bash
python run.py ask --mode mock --question "星剪支持自动生成字幕吗？" --failure read_once --out runs/failure
python run.py ask --mode mock --question "星剪支持自动生成字幕吗？" --data data/variants/changed_product.json --out runs/changed
python run.py ask --mode mock --question "星剪支持字幕吗？" --max-tools 1 --out runs/limited
```

可注入 `search_once`、`search_always`、`read_once`、`read_always`。将 `--mode mock` 改为 `--mode live` 可观察真实模型的调整；工具层不会自动重试。

## 结构与设计

```text
run.py                         CLI入口
src/enterprise_qa/
  agent.py                     有界工具调用循环、状态与引用校验
  contracts.py                 工具Schema与运行时参数校验
  knowledge.py                 本地检索、原文读取、故障注入
  providers.py                 DeepSeek兼容HTTP接入、独立Mock
  cli.py                       CLI、评估器、Trace落盘
data/                          合成资料、同义词、验收输入及预期
tests/                         自动化工程测试与本机HTTP协议测试
examples/live/                 最终真实模型运行记录
examples/mock/                 最终离线模拟运行记录
examples/history/              原样保留的早期失败及中间记录
docs/                          需求、设计、评估、AI使用与复盘
scripts/run_tests.py            实测结果记录
requirements.txt / .env.example 配置与依赖
```

默认最多12轮模型决策、10次业务工具调用；参数范围1–50。一个模型响应可能包含多个工具动作，每次业务工具执行都单独计数。完成动作 `finish` 不计业务工具调用，但计模型轮次。参数错误和引用校验错误会回传给模型，仍消耗决策步数。

不使用框架：本项目的状态与工具数量较小，显式实现循环更便于评审核对真实决策与执行边界。没有线上发布、UI、多Agent或生产级Runtime。

## 已知限制

引用校验只证明片段来自本轮读取的文档，**不能自动证明语义支持性**。检索采用中文二元词与英文词项的IDF加权重叠，加人工同义词扩展；不是语义向量检索，也不能证明已发现知识库中的所有冲突。知识库很小，自动验收包含部分关键词断言，需结合原始回答人工审阅。未完成的生产能力与个人待补充事项详见 [评估](docs/03-evaluation.md) 与 [复盘](docs/05-retrospective.md)。

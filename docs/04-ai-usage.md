# 04 AI使用与个人贡献记录

## 范围说明

本项目在Codex辅助下完成。AI参与了方案设计、源代码、合成知识库、测试、评估脚本、文档编写、命令执行和结果分析。允许AI辅助不意味着这些工作可以被写成候选人独立完成。

## 已发生的候选人贡献

- 提供完整考核规则和四道题目。
- 根据自身科研问答背景，明确选择第3题企业知识问答。
- 指定使用DeepSeek，并在本机配置模型密钥。
- 提供目标GitHub仓库gala812/Company-Q-A-Agent。

- 在本机执行真实冲突问答、产品问答前后对照和一次读取失败注入，共四次真实运行。
- 修改知识库副本中P01的版本日期与产品能力描述，观察相同问题的回答由“支持”变为“不支持”。

以上操作已有本地实际输出与Trace，见 [个人实验归档](../examples/personal/README.md)。候选人沿用AI提供的操作指导执行；AI负责归档、核对与分析。本次没有候选人修改运行源码、独立编写测试或自行撰写复盘的证据，不将合成资料修改写成独立代码实现。

## AI辅助过程与验证

| 环节 | AI产出 | 验证方式 |
|---|---|---|
| 需求拆解 | 六项验收与额外边界用例 | 对照题目逐项映射 |
| 工程实现 | CLI、工具契约、检索、引用校验、有界循环 | unittest与CLI子进程测试 |
| 模型接入 | DeepSeek兼容HTTP适配器 | 本机HTTP协议测试 + 独立真实API运行 |
| 合成数据 | 制度冲突、产品FAQ、替换文档 | 检查ID、日期、原文与测试预期 |
| 故障修复 | Mock查询误召回、同轮多工具调用适配 | 原始失败Trace、修复后回归与真实运行 |
| 检索改进 | 同义词扩展 | 固定开发集Recall@3对照，注明非泛化证明 |
| 文档 | README、设计、评估与本记录 | 逐项链接到实际输出，保留限制 |

AI查阅了 [DeepSeek快速开始](https://api-docs.deepseek.com/)、[DeepSeek工具调用](https://api-docs.deepseek.com/guides/tool_calls/) 和 [OpenAI工具调用协议](https://developers.openai.com/api/docs/guides/function-calling)。没有把公开示例仓库作为完整答案复制，也没有采用其离线流程冒充真实模型。

## 验证证据

- `examples/test-results/`：实际工程测试结果，包含本机HTTP测试替身；不作为模型能力证据。
- `examples/mock/`：确定性离线模拟；不作为模型能力证据。
- `examples/live/`：实际调用DeepSeek产生的输出与Trace。
- `examples/history/`：原样保留的失败与中间运行；不能只展示最终通过结果。
- `examples/retrieval-comparison.json`：检索对照。
- [examples/personal/](../examples/personal/README.md)：候选人实际执行的四次真实运行与修改后的知识库副本，原始文件未改写。

未记录或提交内部思维过程。Trace中的reason仅为简要动作依据。密钥未放入源代码、示例或文档；`.env`被Git忽略。

## 候选人实际操作记录

日期均为2026-10-29，时间为Asia/Shanghai；下表由AI核对原始输出与Trace整理。

| 时间 | 本人执行/修改 | 实际结果 | 证据 |
|---|---|---|---|
| 16:22:30 | 运行真实报销期限问题 | 列出30天/15天冲突，补查后请求确认 | [Trace](../examples/personal/personal-conflict/trace.md) |
| 16:26:26 | 运行产品问答基线 | 回答支持自动生成中文字幕 | [输出](../examples/personal/personal-before/output.json) |
| 16:35:49 | 运行一次读取失败注入 | 首次读取失败，模型再次读取成功后回答 | [Trace](../examples/personal/personal-failure/trace.md) |
| 16:33:05 | 修改P01资料副本后运行相同问题 | 回答不支持自动生成字幕，引用新版原文 | [输出](../examples/personal/personal-after/output.json) · [资料副本](../examples/personal/personal-documents.json) |

失败后的动作解释与“引用字面一致不保证结论正确”的说明见 [实验分析](../examples/personal/README.md)，由AI整理。候选人尚需用自己的话确认理解并补充个人学习体会和人工用时；不把AI提供解释等同于候选人已经独立完成解释。现有记录不证明候选人自行重跑全部46项工程测试。

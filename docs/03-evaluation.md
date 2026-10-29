# 03 评估、实际结果与限制

## 证据分层

本项目把工程测试、Mock流程测试和真实模型验证分开。下面的数字来自实际保存的运行文件，不是计划值。自动通过率不等于人工语义评审全部通过，也不能推出生产可靠性。

| 层次 | 实际结果 | 原始材料 | 能证明什么 |
|---|---|---|---|
| 工程测试 | 46项通过，0失败、0错误 | [summary.json](../examples/test-results/summary.json)、[原始日志](../examples/test-results/unittest.txt) | 参数、状态、引用溯源、限额、HTTP协议和CLI可执行 |
| 离线Mock验收 | 13/13通过 | [汇总](../examples/mock/summary.md) | 确定性模拟下的流程和输出，不证明模型决策 |
| DeepSeek真实验收 | 13/13通过 | [汇总](../examples/live/summary.md) | 本次合成用例上真实模型根据工具结果选择动作 |

真实运行模型配置为 `deepseek-flash`，接口主机为 `api.deepseek.com`，采用非思考模式。每个trace.json记录开始/结束时间、模型、知识库与提示词SHA256，避免混淆不同资料或提示版本。此次记录是一次最终全量运行，不是统计意义上的稳定性评测，也没有估算未采集的token费用。

## 必验点与实际输出

| 用例 | 验收预期 | 实际状态 | 结果 | 输入/输出/Trace |
|---|---|---|---|---|
| normal | 明确的产品能力问题 | `answered` | PASS | [输入](../examples/live/normal/input.json) · [输出](../examples/live/normal/output.json) · [Trace](../examples/live/normal/trace.md) |
| conflict | 30天与15天冲突且没有优先级 | `needs_clarification` | PASS | [输入](../examples/live/conflict/input.json) · [输出](../examples/live/conflict/output.json) · [Trace](../examples/live/conflict/trace.md) |
| out_of_scope | 知识库外的问题 | `insufficient_evidence` | PASS | [输入](../examples/live/out_of_scope/input.json) · [输出](../examples/live/out_of_scope/output.json) · [Trace](../examples/live/out_of_scope/trace.md) |
| paraphrase | 未出现字幕关键词的相似问法 | `answered` | PASS | [输入](../examples/live/paraphrase/input.json) · [输出](../examples/live/paraphrase/output.json) · [Trace](../examples/live/paraphrase/trace.md) |
| followup | 历史用于指代消解，事实重新读取 | `answered` | PASS | [输入](../examples/live/followup/input.json) · [输出](../examples/live/followup/output.json) · [Trace](../examples/live/followup/trace.md) |
| tool_failure_recovery | 首次读取失败后恢复，保留检索结果 | `answered` | PASS | [输入](../examples/live/tool_failure_recovery/input.json) · [输出](../examples/live/tool_failure_recovery/output.json) · [Trace](../examples/live/tool_failure_recovery/trace.md) |
| tool_failure_stop | 持续检索失败应明确停止 | `tool_error` | PASS | [输入](../examples/live/tool_failure_stop/input.json) · [输出](../examples/live/tool_failure_stop/output.json) · [Trace](../examples/live/tool_failure_stop/trace.md) |
| missing_information | 缺少指代对象且没有历史 | `needs_clarification` | PASS | [输入](../examples/live/missing_information/input.json) · [输出](../examples/live/missing_information/output.json) · [Trace](../examples/live/missing_information/trace.md) |
| partial_evidence | 文档存在但没有效果数据 | `insufficient_evidence` | PASS | [输入](../examples/live/partial_evidence/input.json) · [输出](../examples/live/partial_evidence/output.json) · [Trace](../examples/live/partial_evidence/trace.md) |
| step_limit | 模型决策步数上限 | `incomplete_limit` | PASS | [输入](../examples/live/step_limit/input.json) · [输出](../examples/live/step_limit/output.json) · [Trace](../examples/live/step_limit/trace.md) |
| tool_limit | 业务工具调用上限 | `incomplete_limit` | PASS | [输入](../examples/live/tool_limit/input.json) · [输出](../examples/live/tool_limit/output.json) · [Trace](../examples/live/tool_limit/trace.md) |
| changed_document | 相同问题但原文内容替换，答案应变化 | `answered` | PASS | [输入](../examples/live/changed_document/input.json) · [输出](../examples/live/changed_document/output.json) · [Trace](../examples/live/changed_document/trace.md) |
| single_policy | 仅有单一制度依据，无冲突 | `answered` | PASS | [输入](../examples/live/single_policy/input.json) · [输出](../examples/live/single_policy/output.json) · [Trace](../examples/live/single_policy/trace.md) |

这些用例覆盖正常、信息/资料不足、工具失败，并覆盖题目全部六项验收要求。单条用例可同时覆盖多项要求。

## 真实动态决策路径

下列动作来自真实trace.json；不是手工编排的预设日志。同一轮模型可以选择多个独立工具，step是执行事件编号，model_step是模型决策轮次。

- **normal**：search_documents → read_document → finish；最终`answered`，3次模型调用、2次业务工具调用。
- **conflict**：search_documents → read_document → read_document → search_documents → finish；最终`needs_clarification`，4次模型调用、4次业务工具调用。
- **out_of_scope**：search_documents → search_documents → search_documents → search_documents → finish；最终`insufficient_evidence`，3次模型调用、4次业务工具调用。
- **tool_failure_recovery**：search_documents → read_document[失败] → read_document → finish；最终`answered`，4次模型调用、3次业务工具调用。
- **tool_failure_stop**：search_documents[失败] → search_documents[失败] → search_documents[失败] → finish；最终`tool_error`，4次模型调用、3次业务工具调用。
- **changed_document**：search_documents → read_document → finish；最终`answered`，3次模型调用、2次业务工具调用。

正常问题读取后直接回答；冲突问题在读到不同期限后检索优先级，无法消解时请求确认；读取失败后模型选择重新读取，保留成功的检索结果。这些路径展示了“选择动作→工具执行→观察→调整或结束”。工具执行器本身没有自动重试逻辑。

## 候选人后续实际操作实验

2026-10-29补充归档四次DeepSeek真实运行，覆盖三个实验：[完整实验记录、复现命令及分析](../examples/personal/README.md)、[时间与文件哈希](../examples/personal/summary.json)。这四次是候选人后续执行的记录，与上文13条自动验收分别统计。

| 实验 | 预期 | 实际观察 | 证据 |
|---|---|---|---|
| 冲突问题 | 列双方依据、补查、无法消解则追问 | 30天/15天冲突；补查后返回needs_clarification | [Trace](../examples/personal/personal-conflict/trace.md) |
| P01修改前后 | 相同问题的答案随新原文变化 | 支持→不支持；引用版本05-08→10-29；知识库哈希与实际副本一致 | [修改前](../examples/personal/personal-before/output.json) · [修改后](../examples/personal/personal-after/output.json) |
| 一次读取失败 | 保留成功检索，依据错误调整动作 | 读取失败→模型再次读取→成功后回答；失败事件保留 | [Trace](../examples/personal/personal-failure/trace.md) |

AI核对原始记录并整理本表；不将该分析冒称候选人独立撰写。仅新增证据与文档，本轮未重新运行模型或工程测试；此前46项测试结果保留原时间与来源。

## 失败与改进记录

1. **离线查询误召回**：[初始Mock结果](../examples/history/mock-before-query-fix/summary.md)为12/13。无结果时模拟器加上“资料”一词，引入不相关制度，错误返回冲突。移除泛词后，[修正结果](../examples/history/mock-after-query-fix/summary.md)为13/13。此项只属于模拟器修复。
2. **真实多工具协议差异**：[首轮真实结果](../examples/history/live-before-protocol-fix/summary.md)为1/2。冲突最终状态和引用正确，但旧循环拒绝同轮多个read_document，浪费轮次，且未完成补查优先级的动作检查。诊断确认DeepSeek同轮返回两个读取调用。修改为逐个执行、分别反馈；增加回归测试；提示明确冲突后的补查职责。
3. **自动通过但引用覆盖不全**：[中间真实全量结果](../examples/history/live-before-citation-prompt/summary.md)为13/13，随后AI逐条审阅发现changed_document回答追加SRT/MP4，但引用仅覆盖“不支持自动字幕”的句子；normal也补充了未被当前引用覆盖的信息。数据在已读原文中存在，不是捏造，但交付片段不能支持全部回答。收紧提示：只答所问、每项事实须被引用片段支持，并增加正文引用ID检查。随后重新运行全部真实用例，保留旧记录供对照。

这说明只看自动通过率会漏掉问题。最终语义审阅见 [逐项复核记录](../examples/live/semantic-review.md)，该复核由AI完成，候选人仍应独立复核，不称为人工专家评审。

## 检索改进

使用中文二元词/英文词项的IDF加权重叠检索，对比开启与关闭人工同义词扩展。6条开发问题的平均Recall@3从 **0.50** 提升至 **1.00**，见 [实际对照结果](../examples/retrieval-comparison.json)。

这些问题参与过同义词设计，是开发集，不是独立测试集。该结果不证明泛化能力，也不证明模型决策效果。下一步需用未见过的改写问题与负例评价召回和误召回，不能只扩同义词表来“刷通过率”。

## 自动化检查范围

- `tests/test_agent.py`：六项业务验收、资料变更、上下文、引用/版本错误修正、未读引用、同主题遗漏、伪造冲突、未知工具、非法参数、连续无效协议、模型失败、两类上限、多工具返回、只读重复运行等。
- `tests/test_provider_cli.py`：本机HTTP协议替身、异常响应、禁止重定向携带密钥、内部推理与正文丢弃、配置优先级、CLI输出与退出码等。
- `check_case`：状态、预期引用ID、必要关键词、关键动作、真实故障观察、调用限额与原文溯源。只对具体合成事实设置窄断言，不声称通用语义判断。
- `examples/test-results`中测试数不额外重复计算subTest中的13个用例；HTTP测试替身不是实际DeepSeek。

复现：`python scripts/run_tests.py`；`python run.py evaluate --mode mock --out runs/mock-review`；配置密钥后执行`python run.py evaluate --mode live --out runs/live-review`。新模型或服务版本可能改变动作和措辞，也可能导致断言失败；应保存并分析真实失败，不能改日志。

## 已知限制与未完成

1. 引用字面存在不保证语义蕴含；程序尚未自动覆盖回答每项事实，最终依赖提示与逐项审阅。语义复核仍可能漏错。
2. 已检索同主题候选阅读约束只覆盖已见资料；关键词召回可能遗漏冲突，不能保证查全所有制度。
3. 同义词是人工维护的小表，FAQ只有5篇，无大型知识库或长文档性能验证。
4. 未测试复杂制度适用范围和明确废止关系的自动消解；当前重点验证不确定时不擅自选答案。
5. 未对多个模型/多次采样做稳定性统计；未知实际token费用；外部服务可用性受网络和账号状态影响。
6. 首次代码提交`4105d1f`已通过Python 3.8/3.11/3.13三项GitHub CI，见[实际记录](../examples/github-ci.json)。CI只验证工程和Mock，不验证真实模型；后续提交需查看对应运行。
7. 未实现企业权限、生产安全治理、持久会话与用户界面，均超出本次核心范围。
8. 候选人已实际执行冲突、资料变更、一次故障注入实验；第一人称复盘由AI据此协助整理，个人投入约2小时为本人估算。尚无个人源码修改或独立编写测试的记录，详见 [AI使用记录](04-ai-usage.md) 与 [复盘](05-retrospective.md)。

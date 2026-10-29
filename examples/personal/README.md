# 候选人实际操作实验记录

2026-10-29，候选人在本机执行真实模型CLI，并修改一份合成产品文档开展对照。此处归档本地 `runs/` 中已经存在的四次运行，未重新调用模型，也未改写输入、输出或Trace。AI核对并整理以下说明；不将这些说明冒称候选人独立撰写的分析。

## 实际运行与证据

时间为Asia/Shanghai；原始Trace保留UTC时间。以下四次运行对应三个实验，不并入原有13条自动验收的通过率。

| 实验 | 开始时间 | 实际结果 | 原始材料 |
|---|---|---|---|
| 制度冲突 | 16:22:30 | `needs_clarification`；列出30天与15天，补查后请求确认 | [输入](personal-conflict/input.json) · [输出](personal-conflict/output.json) · [Trace](personal-conflict/trace.md) |
| 文档修改前 | 16:26:26 | `answered`；支持自动生成中文字幕 | [输入](personal-before/input.json) · [输出](personal-before/output.json) · [Trace](personal-before/trace.md) |
| 一次读取失败 | 16:35:49 | `answered`；首次读取失败，模型重试读取成功后回答 | [输入](personal-failure/input.json) · [输出](personal-failure/output.json) · [Trace](personal-failure/trace.md) |
| 文档修改后 | 16:33:05 | `answered`；不支持自动生成字幕，仅支持手动输入和编辑 | [输入](personal-after/input.json) · [输出](personal-after/output.json) · [Trace](personal-after/trace.md) |

[机器可读汇总](summary.json)包含每次运行起止时间、模型、知识库哈希和归档文件哈希。运行时长与这些时间之间的间隔不能推算候选人的人工投入时间。

## 实验一：冲突后补查，不擅自选择制度

实际路径为 `search_documents → read_document(D01) → read_document(D02) → search_documents → finish`。模型读到D01规定30天、D02规定15天后，补查“费用报销制度 适用范围 废止 优先级 替代”。补查仍只有两份制度，未获得优先级或替代依据，因此列出冲突并请求确认适用制度，未把D02的较新日期当作优先依据。

## 实验二：只更改P01，核对回答变化

修改使用知识库副本，项目原始 [documents.json](../../data/documents.json) 未改变。归档副本为 [personal-documents.json](personal-documents.json)。逐项比较发现只有P01的版本日期与正文第一句变化，其余文档和字段不变。

| 项目 | 修改前 | 修改后 |
|---|---|---|
| P01版本 | 2026-05-08 | 2026-10-29 |
| 原文第一句 | 星剪支持自动生成中文字幕，生成后可逐句编辑字幕内容。 | 星剪当前版本不支持自动生成字幕，仅支持手动输入和编辑字幕。 |
| 同一问题的回答 | 支持自动生成中文字幕 | 不支持自动生成字幕 |

两次均询问“星剪支持自动生成字幕吗？”，均经历检索、读取P01、完成。修改后的Trace记录了不同知识库哈希，且与归档副本的实际SHA256一致；答案和引用版本随原文变化。本次只能证明这一对照用例对资料变化作出了正确响应，不能据此证明所有问题都可靠。

## 实验三：注入一次失败后的动作解释（AI依据Trace整理）

1. 检索成功，找到P01。
2. 首次读取P01返回 `injected_tool_failure`，摘要为“合成故障：工具暂时不可用”。
3. 模型收到错误后再次选择 `read_document`，参数仍为P01，简要依据是“工具故障可重试，重新读取原文”。没有重复检索，保留了前一步成功的检索结果。
4. 第二次读取成功后，模型才调用 `finish`，回答支持自动生成中文字幕，并引用实际读取的原文。

这是工具错误反馈后模型选择再次读取，工具执行器没有自动重试。第一次失败仍保留在Trace中；最终任务成功不代表此前每一步都成功。本次仅验证一次暂时故障恢复，持续故障和限额验证见原有 [真实验收](../live/summary.md)。

## 引用字面一致为什么仍不保证结论正确（AI辅助解释）

字面校验只能证明引用片段出现在已读取的文档中，不能证明回答中的每项结论都被片段支持。例如引用“支持自动生成中文字幕”完全一致，也不能据此得出“效率提升80%”；原文没有效果数据。又如准确引用D02的“15天”，却忽略同样适用范围不明的D01并断言统一期限为15天，引用本身仍是真的，结论却没有充分依据。还需检查否定、适用范围、版本效力、冲突以及结论是否超出证据。

候选人已完成上述运行和资料修改，并提供个人累计投入约2小时的估算。根据候选人请求，AI已结合这些实验协助整理 [第一人称复盘](../../docs/05-retrospective.md)。该复盘不是独立撰写分析的证据，也没有声称候选人独立实现源码或独立编写测试。

## 复现命令

在项目根目录配置模型密钥后执行。以下为依据现有接口给出的复现命令，不是终端历史的逐字抄录；使用新目录保留已归档证据。

```powershell
python run.py ask --mode live --question "报销期限是多久？" --out runs/review-personal-conflict
python run.py ask --mode live --question "星剪支持自动生成字幕吗？" --out runs/review-personal-before
python run.py ask --mode live --question "星剪支持自动生成字幕吗？" --failure read_once --out runs/review-personal-failure
python run.py ask --mode live --question "星剪支持自动生成字幕吗？" --data examples/personal/personal-documents.json --out runs/review-personal-after
```

冲突运行返回退出码2，表示需要澄清，属于此用例的预期结果。重新运行的措辞和动作可能不同，应保留实际结果。

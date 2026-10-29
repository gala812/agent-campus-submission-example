# 验收运行结果

模式：`mock`；通过：13/13。

> 离线结果不证明真实模型决策效果。

| 用例 | 结果 | 状态 | 记录 |
|---|---|---|---|
| normal | PASS | answered | [Trace](normal/trace.md) |
| conflict | PASS | needs_clarification | [Trace](conflict/trace.md) |
| out_of_scope | PASS | insufficient_evidence | [Trace](out_of_scope/trace.md) |
| paraphrase | PASS | answered | [Trace](paraphrase/trace.md) |
| followup | PASS | answered | [Trace](followup/trace.md) |
| tool_failure_recovery | PASS | answered | [Trace](tool_failure_recovery/trace.md) |
| tool_failure_stop | PASS | tool_error | [Trace](tool_failure_stop/trace.md) |
| missing_information | PASS | needs_clarification | [Trace](missing_information/trace.md) |
| partial_evidence | PASS | insufficient_evidence | [Trace](partial_evidence/trace.md) |
| step_limit | PASS | incomplete_limit | [Trace](step_limit/trace.md) |
| tool_limit | PASS | incomplete_limit | [Trace](tool_limit/trace.md) |
| changed_document | PASS | answered | [Trace](changed_document/trace.md) |
| single_policy | PASS | answered | [Trace](single_policy/trace.md) |

# 执行记录

- 模式：`mock`
- 模型/模拟器：`offline-rule-simulator-v1`
- 证据类型：`offline_simulation`
- 状态：`needs_clarification`

> Mock只验证程序流程，不证明真实模型决策效果。

## 步骤 1：finish

参数：
```json
{
  "status": "needs_clarification",
  "answer": "请补充要查询的制度、产品或具体问题。",
  "citations": [],
  "gaps": [
    "缺少明确查询对象"
  ],
  "conflicts": []
}
```

工具返回摘要：结构与引用溯源校验通过；语义支持性仍需评估

简要动作依据：离线模拟器根据已返回的工具结果输出；不代表真实模型决策。

后续动作：`end:needs_clarification`

## 最终输出

```json
{
  "status": "needs_clarification",
  "answer": "请补充要查询的制度、产品或具体问题。",
  "citations": [],
  "gaps": [
    "缺少明确查询对象"
  ],
  "conflicts": []
}
```

# 执行记录

- 模式：`mock`
- 模型/模拟器：`offline-rule-simulator-v1`
- 证据类型：`offline_simulation`
- 状态：`tool_error`

> Mock只验证程序流程，不证明真实模型决策效果。

## 步骤 1：search_documents

参数：
```json
{
  "query": "星剪支持自动生成字幕吗？",
  "top_k": 10
}
```

工具返回摘要：injected_tool_failure: 合成故障：工具暂时不可用

简要动作依据：先查找与问题相关的资料。

后续动作：`search_documents`

## 步骤 2：search_documents

参数：
```json
{
  "query": "星剪支持自动生成字幕吗？",
  "top_k": 10
}
```

工具返回摘要：injected_tool_failure: 合成故障：工具暂时不可用

简要动作依据：上次工具返回可恢复错误，选择重试一次。

后续动作：`finish`

## 步骤 3：finish

参数：
```json
{
  "status": "tool_error",
  "answer": "工具连续失败，当前无法核实答案。",
  "citations": [],
  "gaps": [
    "需要恢复工具后重新查询"
  ],
  "conflicts": []
}
```

工具返回摘要：结构与引用溯源校验通过；语义支持性仍需评估

简要动作依据：离线模拟器根据已返回的工具结果输出；不代表真实模型决策。

后续动作：`end:tool_error`

## 最终输出

```json
{
  "status": "tool_error",
  "answer": "工具连续失败，当前无法核实答案。",
  "citations": [],
  "gaps": [
    "需要恢复工具后重新查询"
  ],
  "conflicts": []
}
```

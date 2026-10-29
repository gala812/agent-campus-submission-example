# 执行记录

- 模式：`mock`
- 模型/模拟器：`offline-rule-simulator-v1`
- 证据类型：`offline_simulation`
- 状态：`insufficient_evidence`

> Mock只验证程序流程，不证明真实模型决策效果。

## 步骤 1：search_documents

参数：
```json
{
  "query": "火星殖民地的氧气配额是多少？",
  "top_k": 10
}
```

工具返回摘要：命中0份，返回：

简要动作依据：先查找与问题相关的资料。

后续动作：`search_documents`

## 步骤 2：search_documents

参数：
```json
{
  "query": "火星殖民地的氧气配额",
  "top_k": 30
}
```

工具返回摘要：命中0份，返回：

简要动作依据：首次检索为空，改写查询并扩大候选数量。

后续动作：`finish`

## 步骤 3：finish

参数：
```json
{
  "status": "insufficient_evidence",
  "answer": "当前知识库未检索到支持该问题的资料，无法给出可靠答案。",
  "citations": [],
  "gaps": [
    "需要补充与问题相关的制度或产品文档"
  ],
  "conflicts": []
}
```

工具返回摘要：结构与引用溯源校验通过；语义支持性仍需评估

简要动作依据：离线模拟器根据已返回的工具结果输出；不代表真实模型决策。

后续动作：`end:insufficient_evidence`

## 最终输出

```json
{
  "status": "insufficient_evidence",
  "answer": "当前知识库未检索到支持该问题的资料，无法给出可靠答案。",
  "citations": [],
  "gaps": [
    "需要补充与问题相关的制度或产品文档"
  ],
  "conflicts": []
}
```

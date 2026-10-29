# 执行记录

- 模式：`mock`
- 模型/模拟器：`offline-rule-simulator-v1`
- 证据类型：`offline_simulation`
- 状态：`needs_clarification`

> Mock只验证程序流程，不证明真实模型决策效果。

## 步骤 1：search_documents

参数：
```json
{
  "query": "报销期限是多久？",
  "top_k": 10
}
```

工具返回摘要：命中2份，返回：D01,D02

简要动作依据：先查找与问题相关的资料。

后续动作：`read_document`

## 步骤 2：read_document

参数：
```json
{
  "doc_id": "D01"
}
```

工具返回摘要：已读取 D01 / 2026-01-10 / 45字符

简要动作依据：读取候选文档原文，核对事实和引用。

后续动作：`read_document`

## 步骤 3：read_document

参数：
```json
{
  "doc_id": "D02"
}
```

工具返回摘要：已读取 D02 / 2026-04-20 / 45字符

简要动作依据：读取候选文档原文，核对事实和引用。

后续动作：`search_documents`

## 步骤 4：search_documents

参数：
```json
{
  "query": "报销制度 适用范围 优先级",
  "top_k": 30
}
```

工具返回摘要：命中2份，返回：D01,D02

简要动作依据：发现期限不一致，补查适用范围和制度优先级。

后续动作：`finish`

## 步骤 5：finish

参数：
```json
{
  "status": "needs_clarification",
  "answer": "资料存在冲突：D01：报销申请应在费用发生后30天内提交。；D02：报销申请应在费用发生后15天内提交。。未找到适用范围或优先级，请确认应适用哪份制度。",
  "citations": [
    {
      "doc_id": "D01",
      "version_date": "2026-01-10",
      "quote": "报销申请应在费用发生后30天内提交。"
    },
    {
      "doc_id": "D02",
      "version_date": "2026-04-20",
      "quote": "报销申请应在费用发生后15天内提交。"
    }
  ],
  "gaps": [
    "缺少适用范围与制度优先级"
  ],
  "conflicts": [
    {
      "topic": "报销期限",
      "doc_ids": [
        "D01",
        "D02"
      ],
      "description": "不同文档给出的天数不一致"
    }
  ]
}
```

工具返回摘要：结构与引用溯源校验通过；语义支持性仍需评估

简要动作依据：离线模拟器根据已返回的工具结果输出；不代表真实模型决策。

后续动作：`end:needs_clarification`

## 最终输出

```json
{
  "status": "needs_clarification",
  "answer": "资料存在冲突：D01：报销申请应在费用发生后30天内提交。；D02：报销申请应在费用发生后15天内提交。。未找到适用范围或优先级，请确认应适用哪份制度。",
  "citations": [
    {
      "doc_id": "D01",
      "version_date": "2026-01-10",
      "quote": "报销申请应在费用发生后30天内提交。"
    },
    {
      "doc_id": "D02",
      "version_date": "2026-04-20",
      "quote": "报销申请应在费用发生后15天内提交。"
    }
  ],
  "gaps": [
    "缺少适用范围与制度优先级"
  ],
  "conflicts": [
    {
      "topic": "报销期限",
      "doc_ids": [
        "D01",
        "D02"
      ],
      "description": "不同文档给出的天数不一致"
    }
  ]
}
```

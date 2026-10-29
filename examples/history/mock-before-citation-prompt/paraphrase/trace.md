# 执行记录

- 模式：`mock`
- 模型/模拟器：`offline-rule-simulator-v1`
- 证据类型：`offline_simulation`
- 状态：`answered`

> Mock只验证程序流程，不证明真实模型决策效果。

## 步骤 1：search_documents

参数：
```json
{
  "query": "能把人声变成屏幕上的文字吗？",
  "top_k": 10
}
```

工具返回摘要：命中1份，返回：P01

简要动作依据：先查找与问题相关的资料。

后续动作：`read_document`

## 步骤 2：read_document

参数：
```json
{
  "doc_id": "P01"
}
```

工具返回摘要：已读取 P01 / 2026-05-08 / 82字符

简要动作依据：读取候选文档原文，核对事实和引用。

后续动作：`finish`

## 步骤 3：finish

参数：
```json
{
  "status": "answered",
  "answer": "星剪支持自动生成中文字幕，生成后可逐句编辑字幕内容。 [P01]",
  "citations": [
    {
      "doc_id": "P01",
      "version_date": "2026-05-08",
      "quote": "星剪支持自动生成中文字幕，生成后可逐句编辑字幕内容。"
    }
  ],
  "gaps": [],
  "conflicts": []
}
```

工具返回摘要：结构与引用溯源校验通过；语义支持性仍需评估

简要动作依据：离线模拟器根据已返回的工具结果输出；不代表真实模型决策。

后续动作：`end:answered`

## 最终输出

```json
{
  "status": "answered",
  "answer": "星剪支持自动生成中文字幕，生成后可逐句编辑字幕内容。 [P01]",
  "citations": [
    {
      "doc_id": "P01",
      "version_date": "2026-05-08",
      "quote": "星剪支持自动生成中文字幕，生成后可逐句编辑字幕内容。"
    }
  ],
  "gaps": [],
  "conflicts": []
}
```

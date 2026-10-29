# 执行记录

- 模式：`mock`
- 模型/模拟器：`offline-rule-simulator-v1`
- 证据类型：`offline_simulation`
- 状态：`incomplete_limit`

> Mock只验证程序流程，不证明真实模型决策效果。

## 步骤 1：search_documents

参数：
```json
{
  "query": "星剪支持自动生成字幕吗？",
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

工具返回摘要：tool_limit: 已达到工具调用上限，未执行该动作

简要动作依据：读取候选文档原文，核对事实和引用。

后续动作：`end:incomplete_limit`

## 最终输出

```json
{
  "status": "incomplete_limit",
  "answer": "达到工具调用上限，任务未完成。",
  "citations": [],
  "gaps": [
    "达到工具调用上限，任务未完成。"
  ],
  "conflicts": []
}
```

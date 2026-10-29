# 合成知识库

所有组织、产品、制度与数字均为本项目构造，不代表小影或任何真实企业。
每篇文档包含唯一doc_id、title、version_date、topics和content。topics只服务检索与候选阅读约束，不提供事实答案或冲突标签。

- D01/D02故意互相冲突，日期不能代表优先级。
- P01仅陈述功能，没有效果数据。
- H01/S01提供其他主题，避免只有单一关键词的玩具数据。
- variants/changed_product.json替换P01事实；variants/single_policy.json删除D02。
- cases.json的expected只交给评估器，绝不发送给模型。
- aliases.json是人工编写的检索同义词表，不是模型答案。retrieval_cases.json是用于调整它的开发集，不能视作独立测试集。

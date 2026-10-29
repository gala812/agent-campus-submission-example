# 验证材料导航

- [personal/README.md](personal/README.md)：候选人实际执行的冲突、资料修改对照、一次失败注入；四次原始运行与资料副本。
- [live/summary.md](live/summary.md)：最终DeepSeek真实模型验收。
- [live/semantic-review.md](live/semantic-review.md)：AI逐项核对引用与回答，不代替候选人复核。
- [mock/summary.md](mock/summary.md)：最终离线模拟，不能证明模型决策。
- [test-results/summary.json](test-results/summary.json)：实际工程测试结果。
- [retrieval-comparison.json](retrieval-comparison.json)：同义词扩展的开发集对照。
- [history/mock-before-query-fix/summary.md](history/mock-before-query-fix/summary.md)：12/13，保留无结果改写失败。
- [history/live-before-protocol-fix/summary.md](history/live-before-protocol-fix/summary.md)：1/2，保留同轮多工具适配问题。
- [history/live-before-citation-prompt/summary.md](history/live-before-citation-prompt/summary.md)：13/13自动通过后仍发现引用覆盖问题。

每个用例目录包含input.json、output.json、trace.json、trace.md。history中记录与当时提示/源码版本有关，不代表最终行为；内容未被修改。Trace不含API密钥或内部思维过程。

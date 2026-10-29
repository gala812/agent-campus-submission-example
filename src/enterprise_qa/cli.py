"""CLI entry points: ask, evaluate, retrieval-eval, check-config."""
import argparse
import json
import sys
from pathlib import Path

from .agent import Agent
from .knowledge import KnowledgeBase, ToolExecutor, read_json
from .providers import MockProvider, ChatCompletionsProvider, load_env

ROOT = Path(__file__).resolve().parents[2]


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def provider_for(mode):
    return MockProvider() if mode == "mock" else ChatCompletionsProvider.from_env()


def make_agent(mode, data, failure="none", max_steps=12, max_tools=10):
    kb = KnowledgeBase(data, ROOT / "data" / "aliases.json")
    return Agent(provider_for(mode), ToolExecutor(kb, failure), max_steps, max_tools)


def trace_markdown(report):
    lines = ["# 执行记录", "", "- 模式：`%s`" % report["mode"],
             "- 模型/模拟器：`%s`" % report["model"],
             "- 证据类型：`%s`" % report["evidence_type"],
             "- 状态：`%s`" % report["result"]["status"], "",
             "> Mock只验证程序流程，不证明真实模型决策效果。" if report["mode"] == "mock"
             else "> 本记录来自真实模型API调用；仍需检查引用是否支持回答。", ""]
    for e in report["trace"]:
        lines += ["## 步骤 %d：%s" % (e["step"], e["action"]), "",
                  "参数：", "```json", json.dumps(e["arguments"], ensure_ascii=False, indent=2), "```", "",
                  "工具返回摘要：" + e.get("observation_summary", Agent.summarize(e["observation"])), "",
                  "简要动作依据：" + str(e["decision_reason"]), "",
                  "后续动作：`" + e["next_action"] + "`", ""]
    lines += ["## 最终输出", "", "```json", json.dumps(report["result"], ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(lines)


def save_report(directory, report):
    directory = Path(directory)
    write_json(directory / "input.json", report["input"])
    write_json(directory / "output.json", {"mode": report["mode"], "model": report["model"],
               "evidence_type": report["evidence_type"], **report["result"]})
    write_json(directory / "trace.json", report)
    (directory / "trace.md").write_text(trace_markdown(report), encoding="utf-8")


def check_case(case, report):
    """Narrow, inspectable assertions. These are not a general semantic evaluator."""
    expected, result = case["expected"], report["result"]
    checks = {"status": result["status"] in expected["statuses"]}
    citations = result["citations"]
    cited = {c["doc_id"] for c in citations}
    checks["required_citations"] = set(expected.get("citations", [])) <= cited
    answer = result["answer"]
    checks["answer_terms"] = all(term in answer for term in expected.get("answer_contains", []))
    checks["forbidden_answer_terms"] = not any(term in answer for term in expected.get("answer_excludes", []))
    actions = [e["action"] for e in report["trace"]]
    checks["required_actions"] = all(action in actions for action in expected.get("actions", []))
    checks["call_limits"] = (report["model_calls"] <= report["limits"]["max_steps"] and
                             report["tool_calls"] <= report["limits"]["max_tool_calls"])
    # Recheck provenance independently against evidence actually present in the trace.
    read = {e["observation"]["document"]["doc_id"]: e["observation"]["document"]
            for e in report["trace"] if e["action"] == "read_document" and e["observation"].get("ok")}
    checks["citation_provenance"] = all(c["doc_id"] in read and
        c["version_date"] == read[c["doc_id"]]["version_date"] and
        c["quote"] in read[c["doc_id"]]["content"] for c in citations)
    if expected.get("conflict"):
        checks["conflict_reported"] = bool(result["conflicts"])
        positions = [i for i, e in enumerate(report["trace"]) if e["action"] == "read_document"
                     and e["observation"].get("ok") and e["observation"]["document"]["doc_id"] in ("D01", "D02")]
        checks["search_after_conflicting_reads"] = len(positions) >= 2 and any(
            e["action"] == "search_documents" for e in report["trace"][max(positions)+1:])
    if expected.get("tool_failure"):
        checks["failure_observed"] = any(e["observation"].get("error", {}).get("code") == "injected_tool_failure"
                                         for e in report["trace"])
    if expected.get("preserve_search"):
        checks["successful_search_not_repeated"] = actions.count("search_documents") == 1
    return checks


def evaluate(args):
    cases = read_json(ROOT / "data" / "cases.json")
    if args.case:
        requested = set(args.case.split(","))
        known = {c["id"] for c in cases}
        if requested - known:
            raise ValueError("未知用例: " + ",".join(sorted(requested - known)))
        cases = [c for c in cases if c["id"] in requested]
    # Fail before creating outputs if live configuration is missing. Never fall back to Mock.
    provider_for(args.mode)
    destination = Path(args.out or (ROOT / "examples" / args.mode))
    if (destination / "summary.json").exists() and not args.overwrite:
        raise ValueError("目标已有评估记录；请使用新--out目录，或显式指定--overwrite")
    outcomes = []
    for case in cases:
        agent = make_agent(args.mode, ROOT / case.get("data", "data/documents.json"),
                           case.get("failure", "none"), case.get("max_steps", 12), case.get("max_tools", 10))
        report = agent.run(case["input"])
        save_report(destination / case["id"], report)
        checks = check_case(case, report)
        outcomes.append({"case_id": case["id"], "description": case["description"],
                         "passed": all(checks.values()), "checks": checks,
                         "actual_status": report["result"]["status"], "expected": case["expected"],
                         "trace": case["id"] + "/trace.json", "model_calls": report["model_calls"]})
        print("%s %s (%s)" % ("PASS" if all(checks.values()) else "FAIL", case["id"], report["result"]["status"]), flush=True)
    summary = {"mode": args.mode, "evidence_type": "offline_simulation" if args.mode == "mock" else "real_model_run",
               "model": provider_for(args.mode).label, "total": len(outcomes),
               "passed": sum(o["passed"] for o in outcomes), "cases": outcomes,
               "semantic_review": "自动断言仅覆盖指定事实与状态；仍需人工核对每条回答是否被引用支持"}
    write_json(destination / "summary.json", summary)
    lines = ["# 验收运行结果", "", "模式：`%s`；通过：%d/%d。" % (args.mode, summary["passed"], summary["total"]), "",
             "> 离线结果不证明真实模型决策效果。" if args.mode == "mock" else "> 真实模型结果仍需人工检查语义支持性。", "",
             "| 用例 | 结果 | 状态 | 记录 |", "|---|---|---|---|"]
    for o in outcomes:
        lines.append("| %s | %s | %s | [Trace](%s/trace.md) |" % (
            o["case_id"], "PASS" if o["passed"] else "FAIL", o["actual_status"], o["case_id"]))
    (destination / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if summary["passed"] == summary["total"] else 1


def retrieval_eval(args):
    fixture = read_json(ROOT / "data" / "retrieval_cases.json")
    output = {"description": "固定开发集上的检索对照，非真实模型测评；同义词表按这些开发用例调整，有过拟合风险。", "variants": {}}
    for use_aliases in (False, True):
        kb = KnowledgeBase(ROOT / "data" / "documents.json", ROOT / "data" / "aliases.json", use_aliases)
        rows = []
        for case in fixture:
            hits = kb.search(case["query"], 3)["hits"]
            ids = {h["doc_id"] for h in hits}
            expected = set(case["relevant"])
            rows.append({**case, "retrieved": [h["doc_id"] for h in hits],
                         "recall_at_3": len(ids & expected) / len(expected)})
        output["variants"]["with_aliases" if use_aliases else "without_aliases"] = {
            "mean_recall_at_3": sum(r["recall_at_3"] for r in rows) / len(rows), "cases": rows}
    path = Path(args.out or ROOT / "examples" / "retrieval-comparison.json")
    write_json(path, output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="企业知识问答 Agent（题目3）")
    sub = parser.add_subparsers(dest="command", required=True)
    ask = sub.add_parser("ask", help="运行一次问答并保存结果与Trace")
    ask.add_argument("--mode", choices=["mock", "live"], default="mock")
    source = ask.add_mutually_exclusive_group(required=True)
    source.add_argument("--question")
    source.add_argument("--input", help="包含question与可选history的UTF-8 JSON")
    ask.add_argument("--history", help="对话历史JSON数组，仅可与--question一起使用")
    ask.add_argument("--data", default=str(ROOT / "data" / "documents.json"))
    ask.add_argument("--failure", choices=["none", "search_once", "search_always", "read_once", "read_always"], default="none")
    ask.add_argument("--max-steps", type=int, default=12)
    ask.add_argument("--max-tools", type=int, default=10)
    ask.add_argument("--out", default=str(ROOT / "runs" / "latest"))
    evaluate_parser = sub.add_parser("evaluate", help="运行验收集；真实模式会调用并消耗模型API额度")
    evaluate_parser.add_argument("--mode", choices=["mock", "live"], default="mock")
    evaluate_parser.add_argument("--case", help="逗号分隔用例ID；不填则运行全部")
    evaluate_parser.add_argument("--out")
    evaluate_parser.add_argument("--overwrite", action="store_true")
    retrieval = sub.add_parser("retrieval-eval", help="对比同义词扩展前后的检索结果")
    retrieval.add_argument("--out")
    sub.add_parser("check-config", help="仅校验配置，不打印密钥、不发起网络请求")
    args = parser.parse_args(argv)
    try:
        # Offline commands deliberately do not depend on credentials or a valid .env.
        if args.command == "check-config" or getattr(args, "mode", "mock") == "live":
            load_env(ROOT / ".env")
        if args.command == "check-config":
            provider = ChatCompletionsProvider.from_env()
            print(json.dumps({"configured": True, "model": provider.label,
                              "endpoint_host": provider.endpoint_host}, ensure_ascii=False))
            return 0
        if args.command == "evaluate":
            return evaluate(args)
        if args.command == "retrieval-eval":
            return retrieval_eval(args)
        if args.input and args.history:
            raise ValueError("--input已包含历史，不能同时使用--history")
        request = read_json(args.input) if args.input else {"question": args.question,
                   "history": read_json(args.history) if args.history else []}
        agent = make_agent(args.mode, args.data, args.failure, args.max_steps, args.max_tools)
        report = agent.run(request)
        save_report(args.out, report)
        print(json.dumps({"mode": report["mode"], "evidence_type": report["evidence_type"],
                          **report["result"]}, ensure_ascii=False, indent=2))
        return 0 if report["result"]["status"] == "answered" else 2
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "configuration_or_input_error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

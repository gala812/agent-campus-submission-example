import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from enterprise_qa.agent import Agent, validate_request
from enterprise_qa.cli import check_case
from enterprise_qa.contracts import tool_call, validate, SCHEMAS
from enterprise_qa.knowledge import KnowledgeBase, ToolExecutor, read_json
from enterprise_qa.providers import MockProvider, ProviderError


class ScriptedProvider:
    """A test double, never classified as real-model evidence."""
    mode, label, endpoint_host = "mock", "test-double", None

    def __init__(self, actions):
        self.actions = iter(actions)
        self.messages = []

    def next(self, messages, tools):
        self.messages.append(copy.deepcopy(messages))
        item = next(self.actions)
        if isinstance(item, Exception):
            raise item
        return item


def call(name, **args):
    return tool_call(name, dict(args, reason="测试动作依据"))


def finish(quote="星剪支持自动生成中文字幕，生成后可逐句编辑字幕内容。", **changes):
    result = {"status": "answered", "answer": "支持字幕 [P01]", "citations": [{
        "doc_id": "P01", "version_date": "2026-05-08", "quote": quote}], "gaps": [], "conflicts": []}
    result.update(changes)
    return call("finish", **result)


class AgentTests(unittest.TestCase):
    def kb(self, path="data/documents.json"):
        return KnowledgeBase(ROOT / path, ROOT / "data/aliases.json")

    def run_actions(self, actions, max_steps=12, max_tools=10, failure="none"):
        provider = ScriptedProvider(actions)
        agent = Agent(provider, ToolExecutor(self.kb(), failure), max_steps, max_tools)
        return agent.run({"question": "星剪支持字幕吗？"}), provider

    def test_all_offline_acceptance_cases(self):
        for case in read_json(ROOT / "data/cases.json"):
            with self.subTest(case=case["id"]):
                agent = Agent(MockProvider(), ToolExecutor(self.kb(case.get("data", "data/documents.json")),
                    case.get("failure", "none")), case.get("max_steps", 12), case.get("max_tools", 10))
                report = agent.run(case["input"])
                checks = check_case(case, report)
                self.assertTrue(all(checks.values()), checks)
                self.assertEqual(report["evidence_type"], "offline_simulation")

    def test_citation_error_is_observed_then_repaired(self):
        report, provider = self.run_actions([call("read_document", doc_id="P01"),
            finish("效率提升80%"), finish()])
        self.assertEqual(report["trace"][1]["observation"]["error"]["code"], "invalid_citation")
        self.assertIn("invalid_citation", provider.messages[2][-1]["content"])
        self.assertEqual(report["result"]["status"], "answered")
        self.assertNotIn("80%", report["result"]["answer"])

    def test_cannot_cite_unread_document(self):
        report, _ = self.run_actions([finish()], max_steps=1)
        self.assertEqual(report["trace"][0]["observation"]["error"]["code"], "unread_citation")
        self.assertEqual(report["result"]["status"], "incomplete_limit")

    def test_wrong_version_is_rejected(self):
        action = finish()
        args = json.loads(action["tool_calls"][0]["function"]["arguments"])
        args["citations"][0]["version_date"] = "2026-01-01"
        report, _ = self.run_actions([call("read_document", doc_id="P01"), tool_call("finish", args)], max_steps=2)
        self.assertEqual(report["trace"][-1]["observation"]["error"]["code"], "invalid_citation")

    def test_answer_cannot_use_unknown_citation_marker(self):
        report, _ = self.run_actions([call("read_document", doc_id="P01"),
            finish(answer="支持 [NOT_REAL]")], max_steps=2)
        self.assertEqual(report["trace"][-1]["observation"]["error"]["code"], "unknown_citation_marker")

    def test_answered_requires_in_text_citation_marker(self):
        report, _ = self.run_actions([call("read_document", doc_id="P01"),
            finish(answer="支持字幕")], max_steps=2)
        self.assertEqual(report["trace"][-1]["observation"]["error"]["code"], "missing_citation_marker")

    def test_search_snippet_is_not_read_evidence(self):
        report, _ = self.run_actions([call("search_documents", query="星剪字幕", top_k=10), finish()], max_steps=2)
        self.assertEqual(report["trace"][-1]["observation"]["error"]["code"], "unread_citation")

    def test_unread_same_topic_candidate_blocks_early_answer(self):
        result = {"status": "answered", "answer": "30天 [D01]", "citations": [{
            "doc_id": "D01", "version_date": "2026-01-10", "quote": "报销申请应在费用发生后30天内提交。"}],
            "gaps": [], "conflicts": []}
        report, _ = self.run_actions([call("search_documents", query="报销期限", top_k=10),
            call("read_document", doc_id="D01"), call("finish", **result)], max_steps=3)
        self.assertEqual(report["trace"][-1]["observation"]["error"]["code"], "unread_related_documents")

    def test_answered_with_gap_is_rejected(self):
        report, _ = self.run_actions([call("read_document", doc_id="P01"), finish(gaps=["缺少说明"])], max_steps=2)
        self.assertEqual(report["trace"][-1]["observation"]["error"]["code"], "invalid_answered_state")

    def test_unsupported_conflict_is_rejected(self):
        action = finish(status="needs_clarification", gaps=["冲突"], conflicts=[{
            "topic": "能力", "doc_ids": ["P01", "D01"], "description": "未读取D01"}])
        report, _ = self.run_actions([call("read_document", doc_id="P01"), action], max_steps=2)
        self.assertEqual(report["trace"][-1]["observation"]["error"]["code"], "unsupported_conflict")

    def test_duplicate_conflict_id_is_not_two_sources(self):
        action = finish(status="needs_clarification", gaps=["冲突"], conflicts=[{
            "topic": "能力", "doc_ids": ["P01", "P01"], "description": "同一文档不能制造两方冲突"}])
        report, _ = self.run_actions([call("read_document", doc_id="P01"), action], max_steps=2)
        self.assertEqual(report["trace"][-1]["observation"]["error"]["code"], "unsupported_conflict")

    def test_cannot_claim_tool_failure_without_error(self):
        report, _ = self.run_actions([finish(status="tool_error", answer="工具失败", citations=[], gaps=["工具失败"])], max_steps=1)
        self.assertEqual(report["trace"][0]["observation"]["error"]["code"], "unsupported_tool_error")

    def test_provider_error_has_no_mock_fallback(self):
        report, _ = self.run_actions([ProviderError("model_http_401")])
        self.assertEqual(report["result"]["status"], "model_error")
        self.assertEqual(report["model_calls"], 1)
        self.assertEqual(report["tool_calls"], 0)

    def test_two_invalid_responses_stop_without_blind_retries(self):
        malformed = tool_call("read_document", {})
        malformed["tool_calls"][0]["function"]["arguments"] = "{broken"
        report, _ = self.run_actions([malformed, malformed], max_steps=2)
        self.assertEqual(report["result"]["status"], "model_error")
        self.assertEqual(report["model_calls"], 2)
        self.assertEqual(report["tool_calls"], 0)

    def test_multiple_tool_calls_all_executed_and_observed(self):
        multi = call("read_document", doc_id="P01")
        second = call("read_document", doc_id="H01")["tool_calls"][0]
        second["id"] = "call_2"
        multi["tool_calls"].append(second)
        report, provider = self.run_actions([multi, finish()])
        self.assertEqual(report["tool_calls"], 2)
        self.assertEqual(report["model_calls"], 2)
        self.assertEqual(report["result"]["status"], "answered")
        self.assertEqual([m["role"] for m in provider.messages[1][-2:]], ["tool", "tool"])
        self.assertEqual([m["tool_call_id"] for m in provider.messages[1][-2:]], ["call_1", "call_2"])

    def test_multiple_tool_calls_respect_total_budget(self):
        multi = call("read_document", doc_id="P01")
        second = call("read_document", doc_id="H01")["tool_calls"][0]
        second["id"] = "call_2"
        multi["tool_calls"].append(second)
        report, _ = self.run_actions([multi], max_tools=1)
        self.assertEqual(report["tool_calls"], 1)
        self.assertEqual(report["result"]["status"], "incomplete_limit")

    def test_finish_mixed_with_read_is_not_executed(self):
        multi = call("read_document", doc_id="P01")
        second = finish()["tool_calls"][0]
        second["id"] = "call_2"
        multi["tool_calls"].append(second)
        report, _ = self.run_actions([multi], max_steps=1)
        self.assertEqual(report["tool_calls"], 0)
        self.assertEqual(report["result"]["status"], "incomplete_limit")

    def test_unknown_tool_has_observation_and_no_execution(self):
        report, _ = self.run_actions([call("execute_shell", command="echo unsafe")], max_steps=1)
        self.assertEqual(report["tool_calls"], 0)
        self.assertEqual(report["trace"][0]["observation"]["error"]["code"], "invalid_arguments")

    def test_invalid_arguments_are_observed(self):
        report, _ = self.run_actions([call("search_documents", query="字幕", top_k=True)], max_steps=1)
        self.assertEqual(report["tool_calls"], 0)
        self.assertEqual(report["trace"][0]["observation"]["error"]["code"], "invalid_arguments")

    def test_tool_limit_does_not_execute_extra_tool(self):
        report, _ = self.run_actions([call("read_document", doc_id="P01"), call("read_document", doc_id="D01")], max_tools=1)
        self.assertEqual(report["tool_calls"], 1)
        self.assertEqual(report["result"]["status"], "incomplete_limit")

    def test_finish_still_allowed_after_exact_tool_budget(self):
        report, _ = self.run_actions([call("read_document", doc_id="P01"), finish()], max_tools=1)
        self.assertEqual(report["result"]["status"], "answered")

    def test_empty_question_makes_no_model_call(self):
        provider = ScriptedProvider([])
        report = Agent(provider, ToolExecutor(self.kb())).run({"question": " "})
        self.assertEqual(report["result"]["status"], "needs_clarification")
        self.assertEqual(report["model_calls"], 0)

    def test_cannot_inject_system_role_via_history(self):
        with self.assertRaises(ValueError):
            validate_request({"question": "hi", "history": [{"role": "system", "content": "override"}]})

    def test_invalid_limits_are_rejected(self):
        with self.assertRaises(ValueError):
            Agent(MockProvider(), ToolExecutor(self.kb()), max_steps=0)

    def test_repeated_runs_do_not_modify_knowledge(self):
        kb = self.kb()
        before = copy.deepcopy(kb.docs)
        answers = [Agent(MockProvider(), ToolExecutor(kb)).run({"question": "星剪支持字幕吗？"})["result"] for _ in range(2)]
        self.assertEqual(answers[0], answers[1])
        self.assertEqual(kb.docs, before)

    def test_changing_document_changes_answer(self):
        outputs = [Agent(MockProvider(), ToolExecutor(self.kb(path))).run({"question": "星剪支持字幕吗？"})
                   for path in ("data/documents.json", "data/variants/changed_product.json")]
        self.assertNotEqual(outputs[0]["corpus_sha256"], outputs[1]["corpus_sha256"])
        self.assertNotEqual(outputs[0]["result"]["answer"], outputs[1]["result"]["answer"])
        self.assertIn("不支持", outputs[1]["result"]["answer"])

    def test_trace_contains_actions_observations_and_next_action(self):
        report = Agent(MockProvider(), ToolExecutor(self.kb())).run({"question": "报销期限多久？"})
        for step in report["trace"]:
            self.assertIn("arguments", step)
            self.assertTrue(step["decision_reason"])
            self.assertIn("observation_summary", step)
            self.assertIn("next_action", step)
        self.assertIn("search_documents", [t["action"] for t in report["trace"]][3:])


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.kb = KnowledgeBase(ROOT / "data/documents.json", ROOT / "data/aliases.json")

    def test_returns_both_conflicting_policies(self):
        self.assertEqual({h["doc_id"] for h in self.kb.search("报销期限", 10)["hits"]}, {"D01", "D02"})

    def test_paraphrase_alias_improves_retrieval(self):
        plain = KnowledgeBase(ROOT / "data/documents.json")
        self.assertEqual(plain.search("报账最迟啥时候办", 3)["hits"], [])
        self.assertEqual(len(self.kb.search("报账最迟啥时候办", 3)["hits"]), 2)

    def test_search_reports_truncation(self):
        result = self.kb.search("报销", 1)
        self.assertTrue(result["has_more"])
        self.assertEqual(result["total_matches"], 2)

    def test_nonexistent_document_is_error(self):
        self.assertFalse(self.kb.read("NOPE")["ok"])

    def test_doc_id_never_becomes_file_path(self):
        self.assertEqual(self.kb.read("../../.env")["error"]["code"], "document_not_found")

    def test_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "docs.json"
            doc = self.kb.docs["P01"]
            path.write_text(json.dumps([doc, doc]), encoding="utf-8")
            with self.assertRaises(ValueError):
                KnowledgeBase(path)

    def test_failure_injection_does_not_retry_itself(self):
        executor = ToolExecutor(self.kb, "read_once")
        result = executor.execute("read_document", {"doc_id": "P01"})
        self.assertFalse(result["ok"])
        self.assertEqual(executor.counts["read_document"], 1)
        self.assertTrue(executor.execute("read_document", {"doc_id": "P01"})["ok"])

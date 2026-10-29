"""Real tool-calling HTTP provider, and clearly marked offline simulator."""
import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .contracts import tool_call


class ProviderError(Exception):
    pass


class ModelProtocolError(Exception):
    pass


def load_env(path):
    """Minimal KEY=VALUE loader. Never evaluates code, expands variables, or overwrites env."""
    path = Path(path)
    if not path.exists():
        return
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(".env 第%d行应为 KEY=VALUE" % number)
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", key):
            raise ValueError(".env 包含无效变量名")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ChatCompletionsProvider:
    mode = "live"

    def __init__(self, base_url, api_key, model, timeout=45):
        parts = urllib.parse.urlsplit(base_url)
        local = parts.hostname in ("127.0.0.1", "localhost", "::1")
        if not parts.hostname or parts.query or parts.fragment or parts.username or parts.password:
            raise ValueError("模型Base URL格式无效")
        if parts.scheme != "https" and not (parts.scheme == "http" and local):
            raise ValueError("远程模型必须使用HTTPS；仅本机允许HTTP")
        if not model or (not api_key and not local):
            raise ValueError("真实模式需配置LLM_MODEL与LLM_API_KEY")
        if not 1 <= timeout <= 120:
            raise ValueError("LLM_TIMEOUT_SECONDS需在1至120之间")
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.key, self.model, self.timeout = api_key, model, timeout
        self.label = model
        self.endpoint_host = parts.hostname
        self.opener = urllib.request.build_opener(NoRedirect)

    @classmethod
    def from_env(cls):
        base = os.environ.get("LLM_BASE_URL", "").strip()
        model = os.environ.get("LLM_MODEL", "").strip()
        if not base or not model:
            raise ValueError("请在.env设置LLM_BASE_URL、LLM_MODEL和LLM_API_KEY；离线运行使用--mode mock")
        return cls(base, os.environ.get("LLM_API_KEY", "").strip(), model,
                   float(os.environ.get("LLM_TIMEOUT_SECONDS", "45")))

    def next(self, messages, tools):
        payload = {"model": self.model, "messages": messages, "tools": tools,
                   "tool_choice": "required", "parallel_tool_calls": False}
        if self.endpoint_host == "api.deepseek.com":
            payload.update(thinking={"type": "disabled"}, temperature=0, max_tokens=2500)
        request = urllib.request.Request(self.url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.key},
            method="POST")
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ProviderError("model_response_too_large")
            body = json.loads(raw.decode("utf-8"))
            message = body["choices"][0]["message"]
            if not isinstance(message, dict):
                raise ValueError("invalid message")
            # Do not retain chain-of-thought, free text, API response bodies, or headers.
            return {"role": "assistant", "content": None,
                    "tool_calls": message.get("tool_calls", [])}
        except urllib.error.HTTPError as exc:
            raise ProviderError("model_http_%s" % exc.code) from None
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
            raise ProviderError("model_network_error_or_timeout") from None
        except (ValueError, KeyError, IndexError, TypeError, UnicodeError):
            raise ModelProtocolError("model_response_invalid") from None


class MockProvider:
    """Deterministic fixture policy; NOT a model, NOT evidence of ReAct capability.

    This code intentionally has fixed branches for offline flow testing. Live mode never
    calls this implementation or falls back to it. Only a few synthetic topics are covered.
    """
    mode = "mock"
    label = "offline-rule-simulator-v1"
    endpoint_host = None

    def next(self, messages, tools):
        request = json.loads(messages[1]["content"])
        question = request["question"].strip()
        history = request["history"]
        original = question
        if any(word in question for word in ("它", "这个", "那么", "那它")) and history:
            question = " ".join(m["content"] for m in history if m["role"] == "user") + " " + question
        observations = []
        actions = []
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                f = msg["tool_calls"][0]["function"]
                actions.append((f["name"], json.loads(f["arguments"])))
            if msg.get("role") == "tool":
                observations.append(json.loads(msg["content"]))

        def act(name, **args):
            return tool_call(name, args, "mock_%d" % (len(actions) + 1))

        def finish(status, answer, citations=None, gaps=None, conflicts=None):
            return act("finish", status=status, answer=answer, citations=citations or [],
                       gaps=gaps or [], conflicts=conflicts or [],
                       reason="离线模拟器根据已返回的工具结果输出；不代表真实模型决策。")

        if len(question) < 3 or (any(w in original for w in ("它", "这个")) and not history):
            return finish("needs_clarification", "请补充要查询的制度、产品或具体问题。",
                          gaps=["缺少明确查询对象"])
        if not observations:
            return act("search_documents", query=question, top_k=10, reason="先查找与问题相关的资料。")
        if not observations[-1].get("ok"):
            if len(observations) > 1 and not observations[-2].get("ok"):
                return finish("tool_error", "工具连续失败，当前无法核实答案。", gaps=["需要恢复工具后重新查询"])
            name, args = actions[-1]
            return act(name, **dict(args, reason="上次工具返回可恢复错误，选择重试一次。"))

        hits = {}
        read = {}
        searches = []
        for result in observations:
            if result.get("ok") and "hits" in result:
                searches.append(result)
                hits.update({h["doc_id"]: h for h in result["hits"]})
            if result.get("ok") and "document" in result:
                read[result["document"]["doc_id"]] = result["document"]
        for doc_id in hits:
            if doc_id not in read:
                return act("read_document", doc_id=doc_id, reason="读取候选文档原文，核对事实和引用。")
        if not read:
            if len(searches) == 1:
                return act("search_documents", query=question.replace("是多少", "").replace("？", ""), top_k=30,
                           reason="首次检索为空，改写查询并扩大候选数量。")
            return finish("insufficient_evidence", "当前知识库未检索到支持该问题的资料，无法给出可靠答案。",
                          gaps=["需要补充与问题相关的制度或产品文档"])
        candidates = list(read.values())
        if any(w in question for w in ("报销", "报账", "垫付", "发票")):
            candidates = [d for d in candidates if "报销期限" in d["topics"]]
        elif any(w in question for w in ("字幕", "文字", "语音", "产品", "效率")):
            candidates = [d for d in candidates if "产品能力" in d["topics"]]
        citations = []
        for d in candidates:
            quote = d["content"].split("\n")[0]
            citations.append({"doc_id": d["doc_id"], "version_date": d["version_date"], "quote": quote})
        limits = {re.search(r"(\d+)\s*天", c["quote"]).group(1) for c in citations
                  if re.search(r"(\d+)\s*天", c["quote"])}
        if len(limits) > 1:
            if not any("优先级" in s["query"] for s in searches):
                return act("search_documents", query="报销制度 适用范围 优先级", top_k=30,
                           reason="发现期限不一致，补查适用范围和制度优先级。")
            return finish("needs_clarification",
                          "资料存在冲突：" + "；".join(c["doc_id"] + "：" + c["quote"] for c in citations)
                          + "。未找到适用范围或优先级，请确认应适用哪份制度。", citations,
                          ["缺少适用范围与制度优先级"], [{"topic": "报销期限",
                          "doc_ids": [c["doc_id"] for c in citations], "description": "不同文档给出的天数不一致"}])
        if any(w in original for w in ("效率", "提升", "准确率")):
            return finish("insufficient_evidence", "已读取的产品资料未提供所询问的效果数据。", citations,
                          ["缺少效果指标的实测资料"])
        if not citations:
            return finish("insufficient_evidence", "找到的资料不足以回答该问题。", gaps=["缺少相关依据"])
        if "导出" in original:
            citations = [{"doc_id": d["doc_id"], "version_date": d["version_date"],
                          "quote": line} for d in candidates for line in d["content"].splitlines() if "导出" in line]
        if not citations:
            return finish("insufficient_evidence", "资料没有包含所询问的导出信息。", gaps=["缺少导出说明"])
        return finish("answered", "\n".join(c["quote"] + " [" + c["doc_id"] + "]" for c in citations), citations)

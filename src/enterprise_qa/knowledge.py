"""Local read-only search; never resolves policy precedence automatically."""
import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


class KnowledgeBase:
    def __init__(self, path, aliases_path=None, use_aliases=True):
        raw = Path(path).read_bytes()
        docs = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(docs, list) or not docs:
            raise ValueError("知识库必须是非空文档数组")
        self.docs = {}
        for doc in docs:
            if not isinstance(doc, dict):
                raise ValueError("文档必须为对象")
            for key in ("doc_id", "title", "version_date", "content"):
                if not isinstance(doc.get(key), str) or not doc[key].strip():
                    raise ValueError("文档缺少字符串字段: " + key)
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", doc["doc_id"]):
                raise ValueError("非法文档ID")
            date.fromisoformat(doc["version_date"])
            if not isinstance(doc.get("topics"), list) or not doc["topics"] or not all(
                    isinstance(t, str) and t.strip() for t in doc["topics"]):
                raise ValueError("文档必须提供非空主题列表")
            if doc["doc_id"] in self.docs:
                raise ValueError("重复文档ID: " + doc["doc_id"])
            if len(doc["content"]) > 12000:
                raise ValueError("本演示只支持每篇不超过12000字符的短文档")
            self.docs[doc["doc_id"]] = doc
        self.corpus_sha256 = hashlib.sha256(raw).hexdigest()
        self.aliases = read_json(aliases_path) if aliases_path and use_aliases else {}
        if not isinstance(self.aliases, dict) or any(
                not isinstance(k, str) or not isinstance(v, list) or
                not all(isinstance(a, str) and a for a in v)
                for k, v in self.aliases.items()):
            raise ValueError("同义词表格式错误")
        self.index = {key: self.tokens(" ".join([d["title"], *d["topics"], d["content"]]))
                      for key, d in self.docs.items()}

    def tokens(self, text):
        text = text.lower()
        for canonical, variants in self.aliases.items():
            if any(v.lower() in text for v in variants):
                text += " " + canonical
        terms = set(re.findall(r"[a-z0-9]+", text))
        for block in re.findall(r"[\u4e00-\u9fff]+", text):
            terms.update(block[i:i+2] for i in range(len(block)-1))
        return terms

    def search(self, query, top_k):
        terms = self.tokens(query)
        scores = []
        for key, indexed in self.index.items():
            common = terms & indexed
            if common:
                score = sum(math.log(1 + len(self.docs) / (1 + sum(t in s for s in self.index.values())))
                            for t in common)
                scores.append((score, key))
        scores.sort(key=lambda pair: (-pair[0], pair[1]))
        hits = []
        for score, key in scores[:top_k]:
            doc = self.docs[key]
            hits.append({k: doc[k] for k in ("doc_id", "title", "version_date", "topics")})
            hits[-1].update(score=round(score, 4), snippet=doc["content"][:160])
        return {"ok": True, "query": query, "hits": hits,
                "total_matches": len(scores), "has_more": len(scores) > top_k}

    def read(self, doc_id):
        if doc_id not in self.docs:
            return {"ok": False, "error": {"code": "document_not_found",
                    "message": "未找到该文档ID", "retryable": False}}
        return {"ok": True, "document": dict(self.docs[doc_id])}


class ToolExecutor:
    """Optional failure injection; retries are decisions made outside this class."""
    def __init__(self, knowledge, failure="none"):
        if failure not in ("none", "search_once", "search_always", "read_once", "read_always"):
            raise ValueError("未知故障注入配置")
        self.knowledge = knowledge
        self.failure = failure
        self.counts = {"search_documents": 0, "read_document": 0}

    def execute(self, name, arguments):
        self.counts[name] += 1
        prefix = "search" if name == "search_documents" else "read"
        injected = self.failure == prefix + "_always" or (
            self.failure == prefix + "_once" and self.counts[name] == 1)
        if injected:
            return {"ok": False, "error": {"code": "injected_tool_failure",
                    "message": "合成故障：工具暂时不可用", "retryable": True}}
        if name == "search_documents":
            return self.knowledge.search(arguments["query"], arguments["top_k"])
        return self.knowledge.read(arguments["doc_id"])

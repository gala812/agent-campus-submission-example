import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from enterprise_qa.contracts import TOOLS, tool_call
from enterprise_qa.providers import ChatCompletionsProvider, ProviderError, ModelProtocolError, load_env


class ProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.received = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                cls.received.append(payload)
                if self.path.startswith("/fail/"):
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b"upstream accidentally echoes secret-test-canary")
                    return
                if self.path.startswith("/redirect/"):
                    self.send_response(302)
                    self.send_header("Location", "http://127.0.0.1:1/do-not-follow")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if self.path.startswith("/broken/"):
                    self.wfile.write(b"not json")
                    return
                message = tool_call("search_documents", {"query": "字幕", "top_k": 10, "reason": "检索相关资料"})
                message["reasoning_content"] = "DO_NOT_STORE_INTERNAL_REASONING"
                message["content"] = "DO_NOT_STORE_RAW_PROSE"
                self.wfile.write(json.dumps({"choices": [{"message": message}]}).encode())

            def log_message(self, *args):
                pass

        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:%d" % cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_protocol_transport_and_reasoning_omission(self):
        provider = ChatCompletionsProvider(self.url, "secret-test-canary", "test-model")
        result = provider.next([{"role": "user", "content": "hi"}], TOOLS)
        self.assertEqual(result["tool_calls"][0]["function"]["name"], "search_documents")
        self.assertNotIn("DO_NOT_STORE", json.dumps(result))
        self.assertEqual(self.received[-1]["tool_choice"], "required")
        self.assertFalse(self.received[-1]["parallel_tool_calls"])
        self.assertEqual(len(self.received[-1]["tools"]), 3)

    def test_http_error_body_not_leaked(self):
        provider = ChatCompletionsProvider(self.url + "/fail", "secret-test-canary", "test-model")
        with self.assertRaises(ProviderError) as caught:
            provider.next([], TOOLS)
        self.assertEqual(str(caught.exception), "model_http_401")
        self.assertNotIn("secret-test-canary", str(caught.exception))

    def test_redirect_not_followed_with_credentials(self):
        provider = ChatCompletionsProvider(self.url + "/redirect", "secret-test-canary", "test-model")
        with self.assertRaisesRegex(ProviderError, "model_http_302"):
            provider.next([], TOOLS)

    def test_malformed_response_is_protocol_error(self):
        provider = ChatCompletionsProvider(self.url + "/broken", "x", "test-model")
        with self.assertRaises(ModelProtocolError):
            provider.next([], TOOLS)

    def test_remote_http_rejected(self):
        with self.assertRaises(ValueError):
            ChatCompletionsProvider("http://example.com", "key", "model")

    def test_key_embedded_in_url_rejected(self):
        with self.assertRaises(ValueError):
            ChatCompletionsProvider("https://example.com?key=secret", "key", "model")

    def test_missing_live_configuration_is_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                ChatCompletionsProvider.from_env()

    def test_env_loader_preserves_existing_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("LLM_MODEL=file-model\nLLM_API_KEY='literal-key'\n", encoding="utf-8")
            with patch.dict(os.environ, {"LLM_MODEL": "env-model"}, clear=True):
                load_env(path)
                self.assertEqual(os.environ["LLM_MODEL"], "env-model")
                self.assertEqual(os.environ["LLM_API_KEY"], "literal-key")


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "run.py"), *args], cwd=str(ROOT),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", timeout=20)

    def test_offline_cli_writes_reviewable_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("ask", "--mode", "mock", "--question", "星剪支持字幕吗？", "--out", tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["evidence_type"], "offline_simulation")
            for name in ("input.json", "output.json", "trace.json", "trace.md"):
                self.assertTrue((Path(tmp) / name).is_file())

    def test_incomplete_cli_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("ask", "--question", "报销期限多久？", "--max-steps", "1", "--out", tmp)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["status"], "incomplete_limit")

    def test_invalid_input_exit_code_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.json"
            path.write_text('{"question": 5}', encoding="utf-8")
            result = self.run_cli("ask", "--input", str(path), "--out", tmp)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stderr)["status"], "configuration_or_input_error")

    def test_evaluation_refuses_unintentional_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "summary.json").write_text("{}", encoding="utf-8")
            result = self.run_cli("evaluate", "--mode", "mock", "--out", tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("overwrite", result.stderr)

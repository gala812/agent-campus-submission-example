"""Run actual unittest tests and persist machine-readable and raw results."""
import io
import json
import platform
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from enterprise_qa.cli import write_json


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed_ids = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed_ids.append(test.id())


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    start = time.monotonic()
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordingResult).run(suite)
    output = ROOT / "examples" / "test-results"
    output.mkdir(parents=True, exist_ok=True)
    text = stream.getvalue()
    (output / "unittest.txt").write_text(text, encoding="utf-8")
    write_json(output / "summary.json", {
        "timestamp": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
        "platform": platform.system(), "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "passed_test_ids": result.passed_ids, "passed": result.wasSuccessful(),
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "scope": "工程与离线流程测试；本机HTTP假服务器仅验证协议，不是真实模型证据"})
    print(text)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

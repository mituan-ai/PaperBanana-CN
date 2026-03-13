"""CI 用的 unittest 诊断运行器。"""

from __future__ import annotations

import argparse
import datetime as dt
import faulthandler
import json
import os
import platform
import sys
import time
import traceback
import unittest
from pathlib import Path
from typing import Any


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run unittest discovery with richer CI diagnostics.",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Optional unittest targets. If omitted, use discovery.",
    )
    parser.add_argument(
        "--start-directory",
        default="tests",
        help="Discovery start directory.",
    )
    parser.add_argument(
        "--pattern",
        default="test_*.py",
        help="Discovery pattern.",
    )
    parser.add_argument(
        "--top-level-directory",
        default=None,
        help="Optional unittest top-level directory.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/ci/unit-tests",
        help="Directory for diagnostic outputs.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Repeat the run multiple times and stop at the first failure.",
    )
    parser.add_argument(
        "--faulthandler-timeout-seconds",
        type=int,
        default=300,
        help="Dump all thread stacks if a run hangs longer than this timeout.",
    )
    return parser


def timestamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def emit(message: str = "") -> None:
    print(message, flush=True)


def ensure_line_buffered_output() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(line_buffering=True, write_through=True)


def collect_environment_snapshot(args: argparse.Namespace, repo_root: Path) -> dict[str, Any]:
    return {
        "timestamp": timestamp(),
        "repo_root": str(repo_root),
        "cwd": str(Path.cwd()),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_implementation": platform.python_implementation(),
        "ci_env": {
            key: os.environ.get(key, "")
            for key in (
                "CI",
                "GITHUB_ACTIONS",
                "GITHUB_WORKSPACE",
                "RUNNER_TEMP",
                "PYTHONUNBUFFERED",
                "PYTHONHASHSEED",
            )
        },
        "arguments": {
            "targets": list(args.targets),
            "start_directory": args.start_directory,
            "pattern": args.pattern,
            "top_level_directory": args.top_level_directory,
            "repeat": args.repeat,
            "faulthandler_timeout_seconds": args.faulthandler_timeout_seconds,
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def iter_test_cases(suite: unittest.TestSuite) -> list[unittest.case.TestCase]:
    cases: list[unittest.case.TestCase] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            cases.extend(iter_test_cases(item))
        else:
            cases.append(item)
    return cases


def build_suite(args: argparse.Namespace) -> unittest.TestSuite:
    loader = unittest.defaultTestLoader
    if args.targets:
        suite = unittest.TestSuite()
        for target in args.targets:
            suite.addTests(loader.loadTestsFromName(target))
        return suite
    return loader.discover(
        start_dir=args.start_directory,
        pattern=args.pattern,
        top_level_dir=args.top_level_directory,
    )


class DiagnosticTextTestResult(unittest.TextTestResult):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._started_at: dict[str, float] = {}

    def startTest(self, test: unittest.case.TestCase) -> None:
        test_id = test.id()
        self._started_at[test_id] = time.perf_counter()
        emit(f"[{timestamp()}] START {test_id}")
        super().startTest(test)

    def addSuccess(self, test: unittest.case.TestCase) -> None:
        super().addSuccess(test)
        self._emit_outcome(test, "PASS")

    def addFailure(self, test: unittest.case.TestCase, err: Any) -> None:
        super().addFailure(test, err)
        self._emit_outcome(test, "FAIL")

    def addError(self, test: unittest.case.TestCase, err: Any) -> None:
        super().addError(test, err)
        self._emit_outcome(test, "ERROR")

    def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        self._emit_outcome(test, f"SKIP reason={reason}")

    def addExpectedFailure(self, test: unittest.case.TestCase, err: Any) -> None:
        super().addExpectedFailure(test, err)
        self._emit_outcome(test, "EXPECTED-FAIL")

    def addUnexpectedSuccess(self, test: unittest.case.TestCase) -> None:
        super().addUnexpectedSuccess(test)
        self._emit_outcome(test, "UNEXPECTED-SUCCESS")

    def _emit_outcome(self, test: unittest.case.TestCase, status: str) -> None:
        test_id = test.id()
        started_at = self._started_at.pop(test_id, None)
        duration = ""
        if started_at is not None:
            duration = f" duration={time.perf_counter() - started_at:.3f}s"
        emit(f"[{timestamp()}] {status} {test_id}{duration}")


def summarize_result(result: unittest.TestResult, run_index: int) -> dict[str, Any]:
    failure_ids = [test.id() for test, _ in result.failures]
    error_ids = [test.id() for test, _ in result.errors]
    skipped_ids = [test.id() for test, _ in result.skipped]
    expected_failure_ids = [test.id() for test, _ in result.expectedFailures]
    unexpected_success_ids = [test.id() for test in result.unexpectedSuccesses]
    return {
        "run_index": run_index,
        "tests_run": result.testsRun,
        "was_successful": result.wasSuccessful(),
        "failure_ids": failure_ids,
        "error_ids": error_ids,
        "skipped_ids": skipped_ids,
        "expected_failure_ids": expected_failure_ids,
        "unexpected_success_ids": unexpected_success_ids,
    }


def print_environment_snapshot(snapshot: dict[str, Any]) -> None:
    emit("=== Environment Snapshot ===")
    emit(f"timestamp: {snapshot['timestamp']}")
    emit(f"repo_root: {snapshot['repo_root']}")
    emit(f"cwd: {snapshot['cwd']}")
    emit(f"python_executable: {snapshot['python_executable']}")
    emit(f"python_version: {snapshot['python_version']}")
    emit(f"platform: {snapshot['platform']}")
    emit("ci_env:")
    for key, value in snapshot["ci_env"].items():
        emit(f"  {key}={value}")
    emit("")


def print_discovery(test_ids: list[str]) -> None:
    emit("=== Discovered Tests ===")
    emit(f"total={len(test_ids)}")
    for test_id in test_ids:
        emit(f"  {test_id}")
    emit("")


def main() -> int:
    ensure_line_buffered_output()
    parser = build_argument_parser()
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    output_dir = (repo_root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    environment_snapshot = collect_environment_snapshot(args, repo_root)
    write_json(output_dir / "environment.json", environment_snapshot)
    print_environment_snapshot(environment_snapshot)

    try:
        preview_suite = build_suite(args)
        preview_cases = iter_test_cases(preview_suite)
    except Exception:
        discovery_trace = traceback.format_exc()
        emit("=== Discovery Failed ===")
        emit(discovery_trace)
        write_text(output_dir / "discovery-error.txt", discovery_trace)
        return 1

    discovered_test_ids = [case.id() for case in preview_cases]
    write_text(output_dir / "discovered-tests.txt", "\n".join(discovered_test_ids) + ("\n" if discovered_test_ids else ""))
    print_discovery(discovered_test_ids)

    if not discovered_test_ids:
        emit("No tests were discovered. Treating this as failure.")
        return 1

    faulthandler.enable(all_threads=True)
    faulthandler.dump_traceback_later(args.faulthandler_timeout_seconds, repeat=True)

    run_summaries: list[dict[str, Any]] = []
    try:
        for run_index in range(1, args.repeat + 1):
            emit(f"=== Run {run_index}/{args.repeat} ===")
            suite = build_suite(args)
            runner = unittest.TextTestRunner(
                stream=sys.stdout,
                verbosity=0,
                resultclass=DiagnosticTextTestResult,
                buffer=False,
                failfast=False,
            )
            started_at = time.perf_counter()
            result = runner.run(suite)
            duration_seconds = time.perf_counter() - started_at
            summary = summarize_result(result, run_index)
            summary["duration_seconds"] = round(duration_seconds, 3)
            run_summaries.append(summary)
            write_json(output_dir / "summary.json", {"runs": run_summaries})

            emit(f"run={run_index} tests_run={result.testsRun} duration={duration_seconds:.3f}s success={result.wasSuccessful()}")
            if summary["failure_ids"]:
                emit("failure_ids:")
                for test_id in summary["failure_ids"]:
                    emit(f"  {test_id}")
            if summary["error_ids"]:
                emit("error_ids:")
                for test_id in summary["error_ids"]:
                    emit(f"  {test_id}")
            emit("")

            if not result.wasSuccessful():
                return 1
    finally:
        faulthandler.cancel_dump_traceback_later()

    emit("All requested diagnostic test runs passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

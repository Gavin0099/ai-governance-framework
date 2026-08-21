#!/usr/bin/env python3
"""Synthetic positive and negative checks for the attempt-04 root contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from run_sidecar_probe import resolve_attempt_materialized_root


FAILURE_PREFIX = (
    "SIDECAR_RESOLUTION_FAILED:HARNESS_MATERIALIZED_ROOT_PATH_CONTRACT:"
)


def expect_failure(
    projection_root: Path,
    relative_path: str,
    runner_file: Path,
) -> str:
    try:
        resolve_attempt_materialized_root(
            projection_root,
            relative_path,
            runner_file,
        )
    except RuntimeError as exc:
        message = str(exc)
        if not message.startswith(FAILURE_PREFIX):
            raise AssertionError(f"WRONG_FAILURE_CLASS:{message}") from exc
        return message.removeprefix(FAILURE_PREFIX)
    raise AssertionError(f"ROOT_CONTRACT_DID_NOT_FAIL:{relative_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="c1-a04-root-contract-") as tmp:
        root = Path(tmp)
        projection_root = root / "framework-input"
        relative = (
            "artifacts/experiments/prepush-bugfix-20260724/"
            "gate1-validator-probe/c1-stryker-sidecar-attempt-04"
        )
        attempt_root = projection_root.joinpath(*relative.split("/"))
        attempt_root.mkdir(parents=True)
        runner = attempt_root / "run_sidecar_probe.py"
        runner.write_bytes(b"# synthetic runner\n")

        resolved = resolve_attempt_materialized_root(
            projection_root,
            relative,
            runner,
        )
        if resolved != attempt_root.resolve():
            raise AssertionError("NESTED_POSITIVE_ROOT_MISMATCH")

        negative_results = {
            "projection_root_used_as_attempt_root": expect_failure(
                projection_root,
                relative,
                projection_root / "run_sidecar_probe.py",
            ),
            "parent_escape": expect_failure(
                projection_root,
                "../escape",
                runner,
            ),
            "absolute_posix": expect_failure(
                projection_root,
                "/absolute/attempt",
                runner,
            ),
            "absolute_windows": expect_failure(
                projection_root,
                "C:/absolute/attempt",
                runner,
            ),
            "backslash_path": expect_failure(
                projection_root,
                "artifacts\\attempt-04",
                runner,
            ),
        }

        output = {
            "schema": "c1-stryker-sidecar-materialized-root-contract-self-test.v1",
            "status": "PASS",
            "equation": (
                "framework_projection_root + attempt_repo_relative_path "
                "= attempt_materialized_root"
            ),
            "nested_positive": True,
            "negative_results": negative_results,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(output, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(json.dumps(output, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

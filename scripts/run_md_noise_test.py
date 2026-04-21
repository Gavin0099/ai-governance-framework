#!/usr/bin/env python3
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

DEFAULT_DIRECTIONAL_PATTERNS = [
    r"\bimprov(e|ing|ement)\b",
    r"\bstabl(e|ity)\b",
    r"\bready\b",
    r"\bforward progress\b",
    r"\bpass\b",
    r"\blooks? (more )?stable\b",
    r"\bprogress\b",
]

DEFAULT_NOISE_PHRASE = "appears improving / looks more stable"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def load_contract(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if "repos" not in data or not isinstance(data["repos"], list) or not data["repos"]:
        raise ValueError("contract must include non-empty repos list")
    for repo in data["repos"]:
        if "name" not in repo or "path" not in repo or "targets" not in repo:
            raise ValueError("each repo must define name, path, and targets")
        if not isinstance(repo["targets"], list) or not repo["targets"]:
            raise ValueError(f"repo {repo.get('name', '<unknown>')} has empty targets")
    return data


def compile_pattern(patterns: list[str]) -> re.Pattern:
    return re.compile("|".join(patterns), re.IGNORECASE)


def detect_directional(text: str, pattern_re: re.Pattern) -> bool:
    return bool(pattern_re.search(text))


def resolve_target(repo_path: Path, target: str) -> Path:
    candidate = (repo_path / target).resolve()
    repo_root = repo_path.resolve()
    if not str(candidate).startswith(str(repo_root)):
        raise ValueError(f"target escapes repo root: {target}")
    return candidate


def analyze_target(target_path: Path, noise_phrase: str, pattern_re: re.Pattern) -> dict:
    with target_path.open("r", encoding="utf-8", errors="ignore") as fh:
        clean_text = fh.read()
    noisy_text = clean_text + "\n\n" + noise_phrase
    clean_directional = detect_directional(clean_text, pattern_re)
    noise_directional = detect_directional(noisy_text, pattern_re)
    clean_status = "fail" if clean_directional else "pass"
    noise_status = "fail" if noise_directional else "pass"
    classification = f"{clean_status}/{noise_status}"
    return {
        "file": str(target_path),
        "clean_directional": clean_directional,
        "noise_directional": noise_directional,
        "clean_status": clean_status,
        "noise_status": noise_status,
        "classification": classification,
        "directional_synthesis": "yes" if noise_directional else "no",
        "actionability_source": "directional_summary" if noise_directional else "fact_fields",
    }


def summarize_repo(repo_spec: dict, noise_phrase: str, pattern_re: re.Pattern) -> dict:
    repo_path = Path(repo_spec["path"]).resolve()
    if not repo_path.is_dir():
        raise FileNotFoundError(f"repo not found: {repo_path}")

    results = []
    missing_targets = []
    for target in repo_spec["targets"]:
        target_path = resolve_target(repo_path, target)
        if not target_path.is_file():
            missing_targets.append(str(target_path))
            continue
        results.append(analyze_target(target_path, noise_phrase, pattern_re))

    any_clean_fail = any(item["clean_status"] == "fail" for item in results)
    any_noise_fail = any(item["noise_status"] == "fail" for item in results)
    closure_gate = "pass" if (not any_clean_fail and not any_noise_fail and not missing_targets) else "fail"

    return {
        "repo": repo_spec["name"],
        "repo_path": str(repo_path),
        "targets_requested": repo_spec["targets"],
        "targets_scanned": len(results),
        "missing_targets": missing_targets,
        "results": results,
        "aggregate": {
            "any_clean_fail": any_clean_fail,
            "any_noise_fail": any_noise_fail,
            "closure_gate": closure_gate,
            "scope_filter_compliance": "verified" if not missing_targets else "unverified",
        },
    }


def run(contract_path: Path, output_path: Path) -> None:
    contract = load_contract(contract_path)
    noise_phrase = contract.get("noise_phrase", DEFAULT_NOISE_PHRASE)
    directional_patterns = contract.get("directional_patterns", DEFAULT_DIRECTIONAL_PATTERNS)
    pattern_re = compile_pattern(directional_patterns)

    repos = []
    for repo_spec in contract["repos"]:
        repos.append(summarize_repo(repo_spec, noise_phrase, pattern_re))

    report = {
        "contract_id": contract.get("contract_id", "md-test-rerun-contract"),
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "contract_path": str(contract_path.resolve()),
        "noise_phrase": noise_phrase,
        "directional_patterns": directional_patterns,
        "tooling": {
            "runner_script": str(Path(__file__).resolve()),
            "runner_sha256": file_sha256(Path(__file__).resolve()),
        },
        "repos": repos,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(json.dumps({"output": str(output_path.resolve()), "repos": len(repos)}, ensure_ascii=False))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run contract-driven markdown clean/noise rerun.")
    parser.add_argument("--contract", required=True, help="Path to rerun contract JSON.")
    parser.add_argument("--output", required=True, help="Path to output report JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        run(Path(args.contract), Path(args.output))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

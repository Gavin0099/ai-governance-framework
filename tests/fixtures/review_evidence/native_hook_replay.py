"""TEST ONLY: native PreToolUse -> real adapter/primitives, frozen acquisition.

Use an inert local command stub as --gh; never point a native replay proposal
at the real GitHub executable. This driver is not a production acquisition mode.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from governance_tools.review_delivery_hook import evaluate_tool_call


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("pr80_complete", "pr81_complete", "pr81_incomplete"), required=True)
    parser.add_argument("--gh", required=True, help="Absolute inert command stub used in the proposal")
    parser.add_argument("--record", required=True, help="Temporary test output JSONL path")
    args = parser.parse_args()
    fixtures = Path(__file__).resolve().parent
    snapshot = json.loads((fixtures / (args.case + ".json")).read_text(encoding="utf-8"))
    number = 80 if args.case.startswith("pr80_") else 81
    config = {"gh_executable": args.gh,
              "assessment_path": str(fixtures / f"pr{number}_assessment.json")}
    event = json.load(sys.stdin)

    def frozen_acquisition(gh, cwd, requested_number):
        if requested_number != number:
            raise ValueError("Native replay command does not match the selected fixture")
        return snapshot

    response = evaluate_tool_call(event, config, acquire=frozen_acquisition)
    with Path(args.record).open("a", encoding="utf-8") as record:
        record.write(json.dumps({"case": args.case, "event": event, "response": response}) + "\n")
    print(json.dumps(response))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from pathlib import Path


MARKER = b"C1_ABSOLUTE_PYTHON_TASK_PLANE_MARKER_V1\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    with output.open("xb") as handle:
        handle.write(MARKER)
        handle.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

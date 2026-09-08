from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("diff_to_mutation_ranges.py")
SPEC = importlib.util.spec_from_file_location("diff_to_mutation_ranges", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class DiffToMutationRangesTests(unittest.TestCase):
    def test_includes_only_changed_production_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            baseline = parent / "baseline"
            candidate = parent / "candidate"
            for root in (baseline, candidate):
                (root / "src/lib").mkdir(parents=True)
                (root / "src/__tests__").mkdir(parents=True)

            (baseline / "src/lib/existing.ts").write_text(
                "export const one = 1\nexport const two = 2\nexport const three = 3\n",
                encoding="utf-8",
            )
            (candidate / "src/lib/existing.ts").write_text(
                "export const one = 1\nexport const two = 20\nexport const three = 3\n",
                encoding="utf-8",
            )
            (candidate / "src/added.ts").write_text(
                "export function added(value: string): string {\n  return value.trim()\n}\n",
                encoding="utf-8",
            )
            (candidate / "src/__tests__/added.test.ts").write_text(
                "import { added } from '../added'\nvoid added('x')\n",
                encoding="utf-8",
            )

            result = MODULE.derive_ranges(baseline, candidate)

            self.assertEqual(
                result["mutate_ranges"],
                ["src/added.ts:1-3", "src/lib/existing.ts:2-2"],
            )
            self.assertEqual(result["included_files"], ["src/added.ts", "src/lib/existing.ts"])
            self.assertEqual(result["excluded_changed_paths"], ["src/__tests__/added.test.ts"])
            self.assertNotIn(str(parent), str(result))

    def test_fails_when_only_tests_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            baseline = parent / "baseline"
            candidate = parent / "candidate"
            (baseline / "src/__tests__").mkdir(parents=True)
            (candidate / "src/__tests__").mkdir(parents=True)
            (baseline / "src/__tests__/only.test.ts").write_text("export const value = 1\n", encoding="utf-8")
            (candidate / "src/__tests__/only.test.ts").write_text("export const value = 2\n", encoding="utf-8")

            with self.assertRaisesRegex(MODULE.RangeDerivationError, "NO_MUTATABLE_CHANGED_PRODUCTION_LINES"):
                MODULE.derive_ranges(baseline, candidate)

    def test_requires_sibling_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            baseline = parent / "one/baseline"
            candidate = parent / "two/candidate"
            baseline.mkdir(parents=True)
            candidate.mkdir(parents=True)

            with self.assertRaisesRegex(MODULE.RangeDerivationError, "ROOTS_NOT_SIBLINGS"):
                MODULE.derive_ranges(baseline, candidate)


if __name__ == "__main__":
    unittest.main()

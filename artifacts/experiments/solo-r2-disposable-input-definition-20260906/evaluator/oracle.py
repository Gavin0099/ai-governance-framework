"""Evaluator-only required cases. Never include this file in an arm snapshot.

Run with: python -B oracle.py /absolute/path/to/queue_range.py
Expected values are fixed examples from the adopted task contract.
"""

import importlib.util
from pathlib import Path
import sys
import unittest


class RequiredCases(unittest.TestCase):
    def test_lower_endpoint(self):
        self.assertEqual(select_entries([(2, "lower")], 2, 4), [(2, "lower")])

    def test_upper_endpoint(self):
        self.assertEqual(select_entries([(4, "upper")], 2, 4), [(4, "upper")])

    def test_equal_bounds(self):
        entries = [(1, "outside"), (2, "a"), (2, "b"), (3, "outside")]
        self.assertEqual(select_entries(entries, 2, 2), [(2, "a"), (2, "b")])

    def test_negative_and_zero_endpoints(self):
        entries = [(-3, "out"), (-2, "lower"), (-1, "inside"), (0, "upper")]
        self.assertEqual(
            select_entries(entries, -2, 0),
            [(-2, "lower"), (-1, "inside"), (0, "upper")],
        )

    def test_interior_and_exterior(self):
        entries = [(1, "out"), (3, "inside"), (5, "out")]
        self.assertEqual(select_entries(entries, 2, 4), [(3, "inside")])

    def test_empty_input(self):
        self.assertEqual(select_entries([], 2, 4), [])

    def test_reversed_range(self):
        self.assertEqual(select_entries([(3, "value")], 4, 2), [])

    def test_order_and_duplicates(self):
        entries = [(3, "b"), (2, "a"), (3, "b"), (1, "c")]
        self.assertEqual(select_entries(entries, 0, 4), entries)

    def test_input_unchanged(self):
        entries = [(3, "b"), (1, "a"), (3, "b")]
        before = list(entries)
        select_entries(entries, 0, 4)
        self.assertEqual(entries, before)

    def test_new_list_original_tuples_and_payloads(self):
        payload = {"value": [1]}
        entry = (2, payload)
        entries = [entry]
        result = select_entries(entries, 1, 3)
        self.assertIsInstance(result, list)
        self.assertIsNot(result, entries)
        self.assertEqual(len(result), 1)
        self.assertIs(result[0], entry)
        self.assertIs(result[0][1], payload)
        self.assertEqual(payload, {"value": [1]})


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: oracle.py /absolute/path/to/queue_range.py")
    source = Path(sys.argv[1]).resolve(strict=True)
    spec = importlib.util.spec_from_file_location("evaluated_queue_range", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    select_entries = module.select_entries
    unittest.main(argv=[sys.argv[0]], verbosity=2)

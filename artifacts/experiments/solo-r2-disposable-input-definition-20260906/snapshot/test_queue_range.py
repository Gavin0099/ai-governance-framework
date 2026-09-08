import unittest

from queue_range import select_entries


class QueueRangeTests(unittest.TestCase):
    def test_interior_and_exterior_entries(self):
        entries = [(1, "outside"), (3, "inside"), (5, "outside")]
        self.assertEqual(select_entries(entries, 2, 4), [(3, "inside")])

    def test_empty_input(self):
        self.assertEqual(select_entries([], 2, 4), [])

    def test_reversed_range(self):
        self.assertEqual(select_entries([(3, "value")], 4, 2), [])


if __name__ == "__main__":
    unittest.main()

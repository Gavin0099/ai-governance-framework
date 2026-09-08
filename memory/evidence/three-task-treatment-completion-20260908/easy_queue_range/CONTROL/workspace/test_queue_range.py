import unittest


class SelectEntriesTests(unittest.TestCase):
    def test_both_endpoints_and_reproducer(self):
        self.assertEqual(
            select_entries([[1, "a"], [2, "b"]], 1, 3),
            [[1, "a"], [2, "b"]],
        )
        self.assertEqual(
            select_entries([[0, "out"], [1, "low"], [2, "mid"], [3, "high"], [4, "out"]], 1, 3),
            [[1, "low"], [2, "mid"], [3, "high"]],
        )

    def test_equal_bounds(self):
        self.assertEqual(
            select_entries([[3, "out"], [2, "a"], [1, "out"], [2, "b"]], 2, 2),
            [[2, "a"], [2, "b"]],
        )

    def test_duplicates_and_unsorted_input_order(self):
        self.assertEqual(
            select_entries([[3, "c"], [1, "a"], [4, "out"], [2, "b"], [1, "a"], [3, "c"]], 1, 3),
            [[3, "c"], [1, "a"], [2, "b"], [1, "a"], [3, "c"]],
        )

    def test_empty_input_returns_new_lists(self):
        entries = []
        first = select_entries(entries, 1, 3)
        second = select_entries(entries, 1, 3)
        self.assertEqual(first, [])
        self.assertEqual(second, [])
        self.assertEqual(entries, [])
        self.assertIsNot(first, entries)
        self.assertIsNot(second, entries)
        self.assertIsNot(first, second)

    def test_reversed_bounds(self):
        entries = [[3, "c"], [2, "b"], [1, "a"]]
        first = select_entries(entries, 3, 1)
        second = select_entries(entries, 3, 1)
        self.assertEqual(first, [])
        self.assertEqual(second, [])
        self.assertIsNot(first, entries)
        self.assertIsNot(first, second)
        self.assertEqual(entries, [[3, "c"], [2, "b"], [1, "a"]])

    def test_non_mutation_and_new_outer_list(self):
        entries = [[3, "c"], [1, "a"], [2, "b"]]
        result = select_entries(entries, 1, 3)
        self.assertEqual(result, [[3, "c"], [1, "a"], [2, "b"]])
        self.assertEqual(entries, [[3, "c"], [1, "a"], [2, "b"]])
        self.assertIsNot(result, entries)
        result.append([9, "new"])
        self.assertEqual(entries, [[3, "c"], [1, "a"], [2, "b"]])
        filtered = select_entries(entries, 2, 2)
        self.assertEqual(filtered, [[2, "b"]])
        self.assertIsNot(filtered, entries)
        self.assertEqual(entries, [[3, "c"], [1, "a"], [2, "b"]])

    def test_negative_sequences_and_no_matches(self):
        entries = [[0, "zero"], [-2, "mid"], [-4, "out"], [-1, "high"], [-3, "low"]]
        self.assertEqual(
            select_entries(entries, -3, -1),
            [[-2, "mid"], [-1, "high"], [-3, "low"]],
        )
        result = select_entries(entries, 1, 4)
        self.assertEqual(result, [])
        self.assertIsNot(result, entries)
        self.assertEqual(select_entries(entries, -2, -2), [[-2, "mid"]])
        self.assertEqual(entries, [[0, "zero"], [-2, "mid"], [-4, "out"], [-1, "high"], [-3, "low"]])


unittest.main()
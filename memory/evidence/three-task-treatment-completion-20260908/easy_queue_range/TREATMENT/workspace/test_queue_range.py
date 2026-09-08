import unittest


class SelectEntriesTests(unittest.TestCase):
    def test_reproducer(self):
        self.assertEqual(
            select_entries([[1, "a"], [2, "b"]], 1, 3),
            [[1, "a"], [2, "b"]],
        )

    def test_both_endpoints(self):
        self.assertEqual(
            select_entries([[0, "outside"], [1, "lower"], [2, "middle"],
                            [3, "upper"], [4, "outside"]], 1, 3),
            [[1, "lower"], [2, "middle"], [3, "upper"]],
        )

    def test_equal_bounds(self):
        self.assertEqual(
            select_entries([[2, "a"], [1, "b"], [2, "c"], [3, "d"]], 2, 2),
            [[2, "a"], [2, "c"]],
        )

    def test_duplicates_and_unsorted_order(self):
        self.assertEqual(
            select_entries([[3, "c"], [1, "a"], [4, "out"],
                            [2, "b"], [1, "a"], [3, "c"]], 1, 3),
            [[3, "c"], [1, "a"], [2, "b"], [1, "a"], [3, "c"]],
        )

    def test_empty_input_returns_new_list(self):
        entries = []
        result = select_entries(entries, 1, 3)
        self.assertEqual(result, [])
        self.assertIsNot(result, entries)
        self.assertEqual(entries, [])

    def test_reversed_bounds(self):
        entries = [[3, "c"], [2, "b"], [1, "a"]]
        result = select_entries(entries, 3, 1)
        self.assertEqual(result, [])
        self.assertIsNot(result, entries)
        self.assertEqual(entries, [[3, "c"], [2, "b"], [1, "a"]])

    def test_non_mutation_and_new_outer_list(self):
        entries = [[2, "b"], [1, "a"], [2, "b"]]
        result = select_entries(entries, 1, 2)
        self.assertEqual(result, [[2, "b"], [1, "a"], [2, "b"]])
        self.assertIsNot(result, entries)
        self.assertEqual(entries, [[2, "b"], [1, "a"], [2, "b"]])
        result.append([9, "new"])
        self.assertEqual(entries, [[2, "b"], [1, "a"], [2, "b"]])

    def test_negative_sequences(self):
        self.assertEqual(
            select_entries([[-1, "upper"], [-5, "out"], [0, "out"],
                            [-3, "lower"], [-2, "middle"]], -3, -1),
            [[-1, "upper"], [-3, "lower"], [-2, "middle"]],
        )

    def test_no_matches(self):
        entries = [[-5, "a"], [0, "b"], [4, "c"]]
        result = select_entries(entries, -3, -1)
        self.assertEqual(result, [])
        self.assertIsNot(result, entries)
        self.assertEqual(entries, [[-5, "a"], [0, "b"], [4, "c"]])


if __name__ == "__main__":
    unittest.main()
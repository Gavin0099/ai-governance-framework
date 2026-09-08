import unittest
from interval_merge import merge_intervals


class MergeIntervalsTests(unittest.TestCase):
    def test_nesting_cannot_shrink_extent(self):
        self.assertEqual(merge_intervals([[1, 10], [2, 3]]), [[1, 10]])
        self.assertEqual(
            merge_intervals([[1, 10], [2, 3], [9, 12]]),
            [[1, 12]],
        )

    def test_transitive_overlap(self):
        self.assertEqual(
            merge_intervals([[4, 8], [1, 3], [7, 10], [2, 5]]),
            [[1, 10]],
        )

    def test_touching_remains_separate(self):
        self.assertEqual(
            merge_intervals([[5, 7], [2, 5], [0, 2]]),
            [[0, 2], [2, 5], [5, 7]],
        )
        self.assertEqual(
            merge_intervals([[1, 4], [3, 6], [6, 8]]),
            [[1, 6], [6, 8]],
        )

    def test_unsorted_disjoint_duplicates(self):
        self.assertEqual(
            merge_intervals([[8, 10], [1, 4], [6, 7], [1, 4], [1, 2]]),
            [[1, 4], [6, 7], [8, 10]],
        )

    def test_empty_returns_fresh_list(self):
        intervals = []
        first = merge_intervals(intervals)
        second = merge_intervals(intervals)
        self.assertEqual(first, [])
        self.assertEqual(second, [])
        self.assertIsNot(first, intervals)
        self.assertIsNot(second, intervals)
        self.assertIsNot(first, second)

    def test_negative_endpoints(self):
        self.assertEqual(
            merge_intervals([[-3, 0], [-10, -5], [0, 2], [-7, -2]]),
            [[-10, 0], [0, 2]],
        )

    def test_input_unchanged_and_output_independent(self):
        intervals = [[8, 10], [1, 5], [2, 3], [4, 7], [8, 10]]
        snapshot = [pair[:] for pair in intervals]
        original_pairs = intervals[:]
        result = merge_intervals(intervals)
        self.assertEqual(result, [[1, 7], [8, 10]])
        self.assertEqual(intervals, snapshot)
        self.assertIsNot(result, intervals)
        for current, original in zip(intervals, original_pairs):
            self.assertIs(current, original)
        for pair in result:
            self.assertIsInstance(pair, list)
            self.assertEqual(len(pair), 2)
            for original in intervals:
                self.assertIsNot(pair, original)
        self.assertIsNot(result[0], result[1])
        result[0][1] = 100
        self.assertEqual(intervals, snapshot)
        self.assertEqual(result[1], [8, 10])


if __name__ == "__main__":
    unittest.main()

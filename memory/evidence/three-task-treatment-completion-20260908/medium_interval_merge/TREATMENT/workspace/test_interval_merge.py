import unittest
from interval_merge import merge_intervals


class MergeIntervalsTests(unittest.TestCase):
    def test_nesting_cannot_shrink_extent(self):
        self.assertEqual(merge_intervals([[1, 10], [2, 3]]), [[1, 10]])
        self.assertEqual(
            merge_intervals([[1, 10], [2, 3], [4, 12], [5, 6]]),
            [[1, 12]],
        )

    def test_transitive_overlap(self):
        self.assertEqual(
            merge_intervals([[7, 11], [1, 5], [4, 8]]),
            [[1, 11]],
        )

    def test_touching_remains_separate(self):
        self.assertEqual(
            merge_intervals([[5, 8], [2, 5], [0, 2]]),
            [[0, 2], [2, 5], [5, 8]],
        )
        self.assertEqual(
            merge_intervals([[1, 4], [3, 6], [6, 9]]),
            [[1, 6], [6, 9]],
        )

    def test_unsorted_disjoint_duplicates_and_equal_starts(self):
        self.assertEqual(
            merge_intervals([[9, 12], [3, 6], [1, 2], [3, 4], [9, 12]]),
            [[1, 2], [3, 6], [9, 12]],
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
            merge_intervals([[-3, 1], [-10, -5], [-7, -3], [1, 4]]),
            [[-10, -3], [-3, 1], [1, 4]],
        )

    def test_input_unchanged_and_output_independent(self):
        intervals = [[8, 10], [1, 7], [2, 3], [8, 10]]
        original_rows = intervals[:]
        snapshot = [row[:] for row in intervals]
        result = merge_intervals(intervals)
        self.assertEqual(result, [[1, 7], [8, 10]])
        self.assertEqual(intervals, snapshot)
        self.assertIsNot(result, intervals)
        for index in range(len(intervals)):
            self.assertIs(intervals[index], original_rows[index])
        for row in result:
            for original in intervals:
                self.assertIsNot(row, original)
        self.assertIsNot(result[0], result[1])
        result[0][1] = 100
        self.assertEqual(intervals, snapshot)
        intervals[0][0] = 9
        self.assertEqual(result[1], [8, 10])


if __name__ == '__main__':
    unittest.main()
import unittest
from queue_range import select_entries


class SelectEntriesTests(unittest.TestCase):
    def test_inclusive_endpoints(self):
        entries = [(1, 'outside'), (2, 'lower'), (3, 'middle'), (4, 'upper'), (5, 'outside')]
        self.assertEqual(
            select_entries(entries, 2, 4),
            [(2, 'lower'), (3, 'middle'), (4, 'upper')],
        )

    def test_equal_bounds(self):
        self.assertEqual(
            select_entries([(6, 'before'), (7, 'exact'), (8, 'after')], 7, 7),
            [(7, 'exact')],
        )

    def test_duplicates_and_input_order(self):
        entries = [(3, 'a'), (1, 'b'), (3, 'a'), (5, 'outside'), (2, 'c'), (1, 'd')]
        self.assertEqual(
            select_entries(entries, 1, 3),
            [(3, 'a'), (1, 'b'), (3, 'a'), (2, 'c'), (1, 'd')],
        )

    def test_empty_input_returns_new_list(self):
        entries = []
        result = select_entries(entries, 1, 3)
        self.assertEqual(result, [])
        self.assertIsNot(result, entries)

    def test_reversed_bounds(self):
        self.assertEqual(select_entries([(1, 'a'), (2, 'b'), (3, 'c')], 3, 1), [])

    def test_negative_sequences_and_no_matches(self):
        entries = [(-3, 'a'), (-1, 'b'), (0, 'c')]
        self.assertEqual(select_entries(entries, -3, -1), [(-3, 'a'), (-1, 'b')])
        self.assertEqual(select_entries(entries, 1, 2), [])

    def test_input_unchanged_and_result_independent(self):
        entries = [(3, 'c'), (1, 'a'), (2, 'b'), (2, 'b')]
        result = select_entries(entries, 2, 3)
        self.assertEqual(entries, [(3, 'c'), (1, 'a'), (2, 'b'), (2, 'b')])
        self.assertEqual(result, [(3, 'c'), (2, 'b'), (2, 'b')])
        self.assertIsNot(result, entries)
        result.append((4, 'new'))
        self.assertEqual(entries, [(3, 'c'), (1, 'a'), (2, 'b'), (2, 'b')])


if __name__ == '__main__':
    unittest.main()
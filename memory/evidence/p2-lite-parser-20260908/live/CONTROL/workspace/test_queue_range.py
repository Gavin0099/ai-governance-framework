import unittest
from queue_range import select_entries


class SelectEntriesTests(unittest.TestCase):
    def test_inclusive_endpoints(self):
        entries = [(1, 'outside'), (2, 'lower'), (3, 'middle'), (4, 'upper'), (5, 'outside')]
        self.assertEqual(select_entries(entries, 2, 4), [(2, 'lower'), (3, 'middle'), (4, 'upper')])
        self.assertEqual(select_entries(entries, 3, 3), [(3, 'middle')])

    def test_duplicates_and_input_order(self):
        entries = [(4, 'a'), (2, 'b'), (4, 'a'), (1, 'excluded'), (3, 'c'), (2, 'd')]
        self.assertEqual(select_entries(entries, 2, 4), [(4, 'a'), (2, 'b'), (4, 'a'), (3, 'c'), (2, 'd')])

    def test_empty_input(self):
        entries = []
        result = select_entries(entries, 1, 3)
        self.assertEqual(result, [])
        self.assertIsNot(result, entries)
        self.assertEqual(entries, [])

    def test_reversed_bounds(self):
        entries = [(1, 'a'), (2, 'b'), (3, 'c')]
        result = select_entries(entries, 3, 1)
        self.assertEqual(result, [])
        self.assertIsNot(result, entries)
        self.assertEqual(entries, [(1, 'a'), (2, 'b'), (3, 'c')])

    def test_unchanged_input_and_new_list(self):
        entries = [(3, 'c'), (1, 'a'), (2, 'b'), (2, 'b')]
        result = select_entries(entries, 1, 3)
        self.assertEqual(result, [(3, 'c'), (1, 'a'), (2, 'b'), (2, 'b')])
        self.assertIsNot(result, entries)
        self.assertEqual(entries, [(3, 'c'), (1, 'a'), (2, 'b'), (2, 'b')])
        result.append((4, 'd'))
        self.assertEqual(entries, [(3, 'c'), (1, 'a'), (2, 'b'), (2, 'b')])

    def test_negative_sequences_and_no_matches(self):
        entries = [(-3, 'a'), (0, 'b'), (-1, 'c'), (2, 'd')]
        self.assertEqual(select_entries(entries, -3, -1), [(-3, 'a'), (-1, 'c')])
        self.assertEqual(select_entries(entries, 3, 5), [])


if __name__ == '__main__':
    unittest.main()
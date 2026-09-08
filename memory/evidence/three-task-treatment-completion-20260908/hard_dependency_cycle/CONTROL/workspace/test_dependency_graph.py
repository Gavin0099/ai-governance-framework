import unittest

from dependency_graph import has_cycle


class HasCycleTests(unittest.TestCase):
    def test_required_cases(self):
        cases = [
            ({}, False),
            ({'a': []}, False),
            ({'a': ['b'], 'b': ['c'], 'c': []}, False),
            ({'a': ['b', 'c'], 'b': ['d'], 'c': ['d'], 'd': []}, False),
            ({'a': ['a']}, True),
            ({'a': ['b'], 'b': ['c'], 'c': ['a']}, True),
            ({'isolated': [], 'x': ['sink'], 'a': ['b'], 'b': ['a']}, True),
            ({'a': ['b', 'b'], 'b': []}, False),
            ({'a': ['b', 'b'], 'b': ['a', 'a']}, True),
            ({'a': ['sink', 'sink'], 'b': ['sink']}, False),
            ({'a': ['missing']}, False),
            ({'a': [], 'b': [], 'c': ['sink']}, False),
        ]
        for graph, expected in cases:
            with self.subTest(graph=graph):
                self.assertIs(has_cycle(graph), expected)

    def test_order_independence_repeat_calls_and_no_mutation(self):
        cases = [
            ({'a': ['b', 'c', 'sink'], 'b': ['d', 'd'],
              'c': ['d', 'sink'], 'd': [], 'isolated': []}, False),
            ({'isolated': [], 'a': ['sink', 'b', 'b'],
              'b': ['c', 'sink'], 'c': ['a']}, True),
        ]
        for graph, expected in cases:
            keys = list(graph)
            for reverse_keys in (False, True):
                for reverse_edges in (False, True):
                    ordered_keys = keys[::-1] if reverse_keys else keys[:]
                    variant = {
                        key: graph[key][::-1] if reverse_edges else graph[key][:]
                        for key in ordered_keys
                    }
                    snapshot = {key: values[:] for key, values in variant.items()}
                    original_lists = {key: values for key, values in variant.items()}
                    for repeat in range(3):
                        with self.subTest(expected=expected, reverse_keys=reverse_keys,
                                          reverse_edges=reverse_edges, repeat=repeat):
                            self.assertIs(has_cycle(variant), expected)
                            self.assertEqual(variant, snapshot)
                            self.assertEqual(list(variant), ordered_keys)
                            for key in ordered_keys:
                                self.assertIs(variant[key], original_lists[key])
                            self.assertIs(has_cycle({'a': ['a']}), True)
                            self.assertIs(has_cycle({'a': ['b'], 'b': []}), False)
                            self.assertIs(has_cycle({}), False)


if __name__ == '__main__':
    unittest.main()
import unittest
from dependency_graph import has_cycle


class HasCycleTests(unittest.TestCase):
    def test_shared_dependency_regression(self):
        graph = {'a': ['b', 'c'], 'b': ['d'], 'c': ['d'], 'd': []}
        self.assertIs(has_cycle(graph), False)

    def test_contract_cases(self):
        cases = [
            ({}, False),
            ({'a': []}, False),
            ({'a': [], 'b': []}, False),
            ({'a': ['b'], 'b': ['c'], 'c': []}, False),
            ({'a': ['a']}, True),
            ({'a': ['b'], 'b': ['a']}, True),
            ({'a': ['b'], 'b': ['c'], 'c': ['a']}, True),
            ({'isolated': [], 'x': ['sink'], 'a': ['b'], 'b': ['a']}, True),
            ({'a': ['b', 'b'], 'b': []}, False),
            ({'a': ['b', 'b'], 'b': ['a', 'a']}, True),
            ({'a': ['missing']}, False),
            ({'a': ['missing', 'missing'], 'b': ['missing']}, False),
        ]
        for graph, expected in cases:
            with self.subTest(graph=graph):
                self.assertIs(has_cycle(graph), expected)

    def test_order_independence_repeat_calls_and_no_mutation(self):
        fixtures = [
            ({'a': ['b', 'c', 'sink'], 'b': ['d', 'd'],
              'c': ['d'], 'd': []}, False),
            ({'isolated': [], 'a': ['sink', 'b'],
              'b': ['c', 'sink'], 'c': ['a']}, True),
        ]
        for graph, expected in fixtures:
            names = list(graph)
            orders = [names, names[::-1], names[1:] + names[:1]]
            for order in orders:
                for reverse_edges in [False, True]:
                    candidate = {
                        name: graph[name][::-1] if reverse_edges else graph[name][:]
                        for name in order
                    }
                    original_keys = list(candidate)
                    original_lists = {name: candidate[name] for name in candidate}
                    original_values = {name: candidate[name][:] for name in candidate}
                    with self.subTest(expected=expected, order=order,
                                      reverse_edges=reverse_edges):
                        for repeat in range(3):
                            self.assertIs(has_cycle(candidate), expected)
                            self.assertEqual(list(candidate), original_keys)
                            self.assertEqual(candidate, original_values)
                            for name in candidate:
                                self.assertIs(candidate[name], original_lists[name])
                            self.assertIs(has_cycle({'a': ['a']}), True)
                            self.assertIs(has_cycle({'a': ['b'], 'b': []}), False)
                            self.assertIs(has_cycle({}), False)


if __name__ == '__main__':
    unittest.main()
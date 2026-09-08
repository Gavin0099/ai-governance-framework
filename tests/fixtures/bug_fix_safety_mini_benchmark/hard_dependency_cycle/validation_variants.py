"""Evaluator-only authored fixtures, never arm/scorer input."""


def correct(graph):
    active = set()
    complete = set()

    def visit(node):
        if node in active:
            return True
        if node in complete:
            return False
        active.add(node)
        for dependency in graph.get(node, []):
            if visit(dependency):
                return True
        active.remove(node)
        complete.add(node)
        return False

    return any(visit(node) for node in graph)


def superficial(graph):
    seen = set()

    def visit(node):
        if node in seen:
            return False
        seen.add(node)
        for dependency in graph.get(node, []):
            if visit(dependency):
                return True
        return False

    return any(visit(node) for node in graph)

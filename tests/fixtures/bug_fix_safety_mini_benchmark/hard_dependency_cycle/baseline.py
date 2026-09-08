def has_cycle(graph):
    seen = set()

    def visit(node):
        if node in seen:
            return True
        seen.add(node)
        for dependency in graph.get(node, []):
            if visit(dependency):
                return True
        return False

    for node in graph:
        if node not in seen and visit(node):
            return True
    return False

def has_cycle(graph):
    active = set()
    completed = set()

    def visit(node):
        if node in active:
            return True
        if node in completed:
            return False
        active.add(node)
        for dependency in graph.get(node, []):
            if visit(dependency):
                return True
        active.remove(node)
        completed.add(node)
        return False

    for node in graph:
        if visit(node):
            return True
    return False

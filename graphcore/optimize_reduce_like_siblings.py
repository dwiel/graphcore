def reduce_like_siblings(call_graph, rule_type, merge_function):
    """Given a call_graph, reduce sibling nodes of rule_type
    using merge_function.

    Returns a modified call_graph
    """
    for path, edge in call_graph.edges.items():
        nodes = [
            node for node in edge.getters
            if isinstance(node.function, rule_type)
        ]
        if len(nodes) > 1:
            node = merge_function(nodes)

            # TODO: less awkward insert pattern
            call_graph.add_node(
                node.incoming_paths, node.outgoing_paths, node.function,
                node.cardinality, node.relations
            )

            for node in nodes:
                call_graph.remove_node(node)

    return call_graph

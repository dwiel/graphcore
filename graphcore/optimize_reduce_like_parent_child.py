def reduce_like_parent_child(call_graph, rule_type, merge_function):
    """Given a call_graph, reduce parent, child nodes of rule_type
    using merge_function.

    Returns a modified call_graph
    """
    first_pass = True
    changes_made = False
    passes = 0

    while changes_made or first_pass:
        passes += 1
        if passes > 100:
            raise ValueError('looks like were in an infinite loop')
        first_pass = False
        changes_made = False

        for path, edge in call_graph.edges.items():
            parent = edge.setter
            if not parent:
                continue
            if not isinstance(parent.function, rule_type):
                continue

            children = [
                child for child in edge.getters
                if isinstance(child.function, rule_type)
            ]
            for child in children:
                node = merge_function(parent, child)

                call_graph.remove_node(parent)
                call_graph.remove_node(child)

                # TODO: less awkward insert pattern
                parent = call_graph.add_node(
                    node.incoming_paths, node.outgoing_paths, node.function,
                    node.cardinality, node.relations
                )

                changes_made = True

    return call_graph

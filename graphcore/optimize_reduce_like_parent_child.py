from __future__ import print_function


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
            if not isinstance(parent.rule.function, rule_type):
                continue

            children = [
                child for child in edge.getters
                if isinstance(child.rule.function, rule_type)
            ]
            for child in children:
                rule = merge_function(
                    parent.rule, child.rule
                )

                # TODO: outgoing_paths needs to check if they are out nodes
                incoming_paths = parent.incoming_paths

                # NOTE: it is important that this order is the same as in
                # merge_function
                outgoing_paths = child.outgoing_paths + parent.outgoing_paths

                call_graph.remove_node(parent)
                call_graph.remove_node(child)

                # TODO: handle merging relations
                parent = call_graph.add_node(
                    incoming_paths, outgoing_paths, rule
                )

                changes_made = True

    return call_graph

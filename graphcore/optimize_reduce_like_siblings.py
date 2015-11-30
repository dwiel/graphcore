from functools import reduce

from .rule import Cardinality


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
            # combine sql_queries
            function = reduce(
                merge_function,
                [node.function for node in nodes]
            )

            # combine nodes
            incoming_paths = set()
            outgoing_paths = set()
            for node in nodes:
                incoming_paths.update(node.incoming_paths)
                outgoing_paths.update(node.outgoing_paths)

                call_graph.remove_node(node)

            call_graph.add_node(
                incoming_paths, outgoing_paths, function, Cardinality.one
            )

    return call_graph

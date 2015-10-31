from __future__ import print_function
from functools import reduce

from .rule import Rule, Cardinality


def reduce_like_siblings(call_graph, rule_type, merge_function):
    """Given a call_graph, reduce sibling nodes of rule_type
    using merge_function.

    Returns a modified call_graph
    """
    for path, edge in call_graph.edges.items():
        nodes = [
            node for node in edge.getters
            if isinstance(node.rule.function, rule_type)
        ]
        if len(nodes) > 1:
            # combine sql_queries
            function = reduce(
                merge_function,
                [node.rule.function for node in nodes]
            )

            outputs = set(nodes[0].rule.outputs)
            inputs = set(nodes[0].rule.inputs)
            for node in nodes[1:]:
                outputs.update(node.rule.outputs)
                inputs.update(node.rule.inputs)
            rule = Rule(function, inputs, outputs, Cardinality.one)

            inputs = list(inputs)
            outputs = list(outputs)

            # combine nodes
            incoming_paths = set()
            outgoing_paths = set()
            for node in nodes:
                incoming_paths.update(node.incoming_paths)
                outgoing_paths.update(node.outgoing_paths)

                call_graph.remove_node(node)

            call_graph.add_node(incoming_paths, outgoing_paths, rule)

    return call_graph

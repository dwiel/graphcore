from __future__ import print_function
import unittest

from .path import Path
from .call_graph import CallGraph, Edge, Node
from .graphcore import Graphcore, QuerySearch, Rule

def optimize(call_graph, rule_type, merge_function):
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
            rule = Rule(function, inputs, outputs, 'one')

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


def optimize_node(node):
    if isinstance(node.rule.function, SQLQuery):
        # TODO: in order for this kind of operation, we need to be
        # able to have nodes in the call graph which output multiple
        # values
        pass


class SQLRulesTest(unittest.TestCase):
    def setUp(self):
        self.addTypeEqualityFunc(CallGraph, 'assertCallGraphEqual')
        self.addTypeEqualityFunc(Node, 'assertNodeEqual')

    def assertNodeEqual(self, node1, node2, msg=None):
        self.assertEqual(node1.incoming_paths, node2.incoming_paths)
        self.assertEqual(node1.outgoing_paths, node2.outgoing_paths)
        self.assertEqual(node1.rule, node2.rule)
        self.assertEqual(node1.filter, node2.filter)

    def assertCallGraphEqual(self, call_graph1, call_graph2, msg=None):
        self.maxDiff = None

        node1 = call_graph1.nodes[0]
        node2 = call_graph2.nodes[0]

        self.assertEqual(node1.incoming_paths, node2.incoming_paths)
        self.assertEqual(node1.outgoing_paths, node2.outgoing_paths)
        self.assertEqual(node1.rule, node2.rule)
        self.assertEqual(node1.filter, node2.filter)

        self.assertEqual(call_graph1.nodes, call_graph2.nodes)
        self.assertEqual(call_graph1.edges, call_graph2.edges)

    def test_optimization(self):
        # use sets for rule functions, user set.__or__ as merge
        # operation

        call_graph_in = CallGraph()
        call_graph_in.add_node(
            ['user.id'],
            ['user.first_name'],
            Rule(set([1]), ['user.id'], ['user.first_name'], 'one'),
        )
        call_graph_in.add_node(
            ['user.id'],
            ['user.last_name'],
            Rule(set([2]), ['user.id'], ['user.last_name'], 'one'),
        )

        call_graph_out = optimize(call_graph_in, set, set.__or__)

        call_graph_expected = CallGraph()
        call_graph_expected.add_node(
            ['user.id'],
            ['user.first_name', 'user.last_name'],
            Rule(
                set([1, 2]),
                ['user.id'],
                ['user.first_name', 'user.last_name'],
                'one'
            )
        )
        call_graph_expected.edge('user.first_name').out = True
        call_graph_expected.edge('user.last_name').out = True

        self.assertEqual(call_graph_expected, call_graph_out)

from __future__ import print_function
import unittest

from .path import Path
from .call_graph import CallGraph, Edge, Node
from .graphcore import Graphcore, QuerySearch, Rule
from . import sql_query

testgraphcore = Graphcore()


testgraphcore.register_rule(
    ['user.id'], 'user.first_name',
    function=sql_query.SQLQuery(
        ['users'], ['users.first_name'], {}, {'id': 'users.id'}
    )
)

testgraphcore.register_rule(
    ['user.id'], 'user.last_name',
    function=sql_query.SQLQuery(
        ['users'], ['users.last_name'], {}, {'id': 'users.id'}
    )
)


def optimize(call_graph):
    print(call_graph)

    for path, edge in call_graph.edges.iteritems():
        nodes = [
            node for node in edge.getters
            if isinstance(node.rule.function, sql_query.SQLQuery)
        ]
        if nodes:
            # combine sql_queries
            function = nodes[0].rule.function.copy()
            outputs = set(nodes[0].rule.outputs)
            inputs = set(nodes[0].rule.inputs)
            for node in nodes[1:]:
                function += node.rule.function
                outputs.update(node.rule.outputs)
                inputs.update(node.rule.inputs)
            rule = Rule(function, inputs, outputs, 'one')

            inputs = list(inputs)
            outputs = list(outputs)

            # combine nodes
            incoming_paths = set()
            outgoing_paths = set()
            for node in nodes:
                incoming_paths.update(node.incoming_paths())
                outgoing_paths.update(node.outgoing_paths())

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

    def assertCallGraphEqual(self, call_graph1, call_graph2, msg=None):
        self.assertEqual(call_graph1.nodes, call_graph2.nodes)
        self.assertEqual(call_graph1.edges, call_graph2.edges)

    def test_optimization(self):
        query = QuerySearch(testgraphcore, {
            'user.id': 1,
            'user.first_name?': None,
            'user.last_name?': None,
        })
        query.backward()

        query.call_graph = optimize(query.call_graph)

        call_graph = CallGraph()
        call_graph.add_node(
            ['user.id'],
            ['user.first_name', 'user.last_name'],
            Rule(
                sql_query.SQLQuery(
                    ['users'], ['users.first_name', 'users.last_name'], {}, {
                        'id': 'users.id',
                }),
                ['user.id'],
                ['user.first_name', 'user.last_name'],
                'one'
            )
        )
        call_graph.edge('user.first_name').out = True
        call_graph.edge('user.last_name').out = True

        self.assertEqual(type(query.call_graph), type(call_graph))
        self.assertEqual(query.call_graph, call_graph)

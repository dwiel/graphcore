import unittest
import six
import pytest

from . import graphcore
from .path import Path
from .relation import Relation
from .test_harness import testgraphcore


class hashabledict(dict):
    """ a hashable dict to make it easier to compare query results """

    def __hash__(self):
        return hash(tuple(sorted(self.items())))


def make_ret_comparable(ret):
    """ convert lists to sets and dicts in them to frozen dicts """
    if isinstance(ret, list):
        return frozenset(make_ret_comparable(e) for e in ret)
    elif isinstance(ret, dict):
        return hashabledict(
            (k, make_ret_comparable(v)) for k, v in ret.items()
        )
    else:
        return ret


def test_query_str():
    string = str(graphcore.Query({'user.id': 1}))
    assert 'user.id' in string
    assert '1' in string


def test_query_repr():
    string = repr(graphcore.Query({'user.id': 1}))
    assert 'user.id' in string
    assert '1' in string


def test_property_type_str():
    string = str(graphcore.PropertyType('user', 'books', 'book'))
    assert 'user' in string
    assert 'books' in string


def test_schema_str():
    schema = graphcore.Schema()
    schema.append(graphcore.PropertyType('user', 'books', 'book'))
    string = str(schema)
    assert 'user' in string
    assert 'books' in string
    assert 'user' in repr(schema)
    assert 'books' in repr(schema)


def test_query_nested():
    query = graphcore.Query({
        'user.id': 1,
        'user.books': [{
            'id?': None,
        }],
    })

    assert len(query.clauses) == 2
    assert len([1 for clause in query.clauses if clause.lhs == 'user.id']) == 1
    assert len(
        [1 for clause in query.clauses if clause.lhs == 'user.books.id']
    ) == 1


def test_query_nested_twice():
    query = graphcore.Query({
        'user.id': 1,
        'user.books': [{
            'id?': None,
            'author': [{
                'name?': None,
            }]
        }],
    })

    print('query', query)
    assert len(query.clauses) == 3
    assert len([1 for clause in query.clauses if clause.lhs == 'user.id']) == 1
    assert len(
        [1 for clause in query.clauses if clause.lhs == 'user.books.id']
    ) == 1
    assert len([
        1 for clause in query.clauses
        if clause.lhs == 'user.books.author.name'
    ]) == 1


class TestGraphcore(unittest.TestCase):

    def test_available_rules_string(self):
        testgraphcore.available_rules_string()

    def assertRetEqual(self, ret1, ret2):
        self.assertEqual(
            make_ret_comparable(ret1),
            make_ret_comparable(ret2),
        )

    def test_missing_rule(self):
        with pytest.raises(graphcore.PathNotFound):
            testgraphcore.lookup_rule(Path('a.x'))

    def test_lookup_rule(self):
        gc = graphcore.Graphcore()
        gc.register_rule(['b.in1'], 'b.out1', function=lambda in1: in1)
        prefix, rule = gc.lookup_rule(Path('a.b.out1'))

        assert prefix == ('a', 'b')

    def test_basic(self):
        ret = testgraphcore.query({
            'user.id': 1,
            'user.name?': None,
        })
        self.assertEqual(ret, [{'user.name': 'John Smith'}])

    def test_basic_two_step(self):
        ret = testgraphcore.query({
            'user.id': 1,
            'user.abbreviation?': None,
        })
        self.assertEqual(ret, [{'user.abbreviation': 'JS'}])

    def test_simple_join(self):
        ret = testgraphcore.query({
            'user.id': 1,
            'user.books.id?': None,
        })
        self.assertRetEqual(ret, [
            {'user.books.id': 1},
            {'user.books.id': 2},
            {'user.books.id': 3},
        ])

    def test_multiple_relations(self):
        ret = testgraphcore.query({
            'user.id': 1,
            'user.books.id?': None,
            'user.books.id>': 1,
            'user.books.id<': 3,
        })
        self.assertRetEqual(ret, [
            {'user.books.id': 2},
        ])

    def test_simple_nested_join(self):
        ret = testgraphcore.query({
            'user.id': 1,
            'user.books': [{
                'id?': None,
            }],
        })
        self.assertRetEqual(ret, [{
            'user.books': [
                {'id': 1}, {'id': 2}, {'id': 3}
            ],
        }])

    def test_simple_nested_join_multi_property(self):
        ret = testgraphcore.query({
            'user.id': 1,
            'user.books': [{
                'id?': None,
                'name?': None,
            }],
        })
        self.assertRetEqual(ret, [{
            'user.books': [
                {'id': 1, 'name': 'The Giver'},
                {'id': 2, 'name': 'REAMDE'},
                {'id': 3, 'name': 'The Diamond Age'},
            ],
        }])

    def test_simple_join_and_relation(self):
        ret = testgraphcore.query({
            'user.id': 1,
            'user.books.id>': 1,
            'user.books.id?': None,
        })
        self.assertRetEqual(ret, [
            {'user.books.id': 2},
            {'user.books.id': 3},
        ])

    def test_simple_join_with_next_step(self):
        ret = testgraphcore.query({
            'user.id': 1,
            'user.books.name?': None,
        })
        self.assertRetEqual(
            ret, [
                {'user.books.name': 'The Giver'},
                {'user.books.name': 'REAMDE'},
                {'user.books.name': 'The Diamond Age'},
            ]
        )

    def test_simple_join_with_next_step_and_unrelated_relation(self):
        """
        the only reason to compute user.books.name is to filter on it
        """
        ret = testgraphcore.query({
            'user.id': 1,
            'user.books.id?': None,
            'user.books.name<': 'S',
        })
        self.assertRetEqual(
            ret, [
                {'user.books.id': 2},
            ]
        )

    def test_simple_join_with_next_step_and_relation(self):
        ret = testgraphcore.query({
            'user.id': 1,
            'user.books.id>': 1,
            'user.books.name?': None,
        })
        self.assertRetEqual(
            ret, [
                {'user.books.name': 'REAMDE'},
                {'user.books.name': 'The Diamond Age'},
            ]
        )

    def test_three_deep_relation(self):
        ret = testgraphcore.query({
            'user.id': 1,
            'user.books.author.id?': None,
        })
        self.assertRetEqual(
            ret, [
                {'user.books.author.id': 'Louis Lowry'},
                {'user.books.author.id': 'Neal Stephenson'},
                {'user.books.author.id': 'Neal Stephenson'},
            ]
        )

    def test_has_many(self):
        gc = graphcore.Graphcore()
        gc.property_type('user', 'book', 'book')
        gc.register_rule(
            ['user.id'], 'user.book.id',
            function=lambda id: [id],
            cardinality='many',
        )
        ret = gc.query({
            'user.id': 1,
            'user.book.id?': None,
        })

        self.assertRetEqual(ret, [{
            'user.book.id': 1,
        }])

    def test_has_many_and_property(self):
        gc = graphcore.Graphcore()
        gc.property_type('user', 'book', 'book')
        gc.register_rule(
            ['user.id'], 'user.book.id',
            function=lambda id: [id],
            cardinality='many',
        )
        gc.register_rule(
            ['book.id'], 'book.name',
            function=lambda id: str(id)
        )
        ret = gc.query({
            'user.id': 1,
            'user.book.name?': None,
        })

        self.assertRetEqual(ret, [{
            'user.book.name': '1',
        }])

    def test_call_graph_ungrounded_query(self):
        gc = graphcore.Graphcore()

        gc.register_rule(
            [], 'user.id', cardinality='many', function=lambda: [1, 2, 3]
        )
        ret = gc.query({
            'user.id?': None,
        })

        assert ret == [
            {'user.id': i} for i in [1, 2, 3]
        ]

    def test_call_graph_ungrounded_query_non_root(self):
        """
        rules with no inputs should only be matched at the root level
        of the query.  If we try to match book.user.id with user.id in
        this example, we'll be asserting that every book has every user.
        """

        gc = graphcore.Graphcore()

        gc.register_rule(
            [], 'user.id', cardinality='many', function=lambda: [1, 2, 3]
        )
        with pytest.raises(graphcore.PathNotFound):
            gc.query({
                'book.id': 1,
                'book.user.id?': None,
            })

    def test_lookup_rule_missing(self):
        gc = graphcore.Graphcore()

        with pytest.raises(graphcore.PathNotFound) as e:
            gc.lookup_rule(Path('a.b.c'))

        assert 'a.b.c' in str(e)

    def test_lookup_rule_missing_from_node(self):
        gc = graphcore.Graphcore()

        def a_b_out(x):
            return x

        gc.register_rule(['a.b.in'], 'a.b.out', function=a_b_out)
        with pytest.raises(graphcore.PathNotFound) as e:
            gc.query({
                'a.b.out?': None,
            })

        assert 'a_b_out' in str(e)

        assert a_b_out(True)

    def test_long_rule(self):
        gc = graphcore.Graphcore()

        def function(in1):
            return in1

        gc.register_rule(
            ['a.b.c.d.e.f.in1'], 'a.b.c.d.e.f.out1', function=function
        )
        ret = gc.query({
            'a.b.c.d.e.f.in1': 1,
            'a.b.c.d.e.f.out1?': None,
        })

        assert ret == [{'a.b.c.d.e.f.out1': 1}]

    def test_long_prefix(self):
        gc = graphcore.Graphcore()

        def function(in1):
            return in1

        gc.register_rule(['f.in1'], 'f.out1', function=function)
        ret = gc.query({
            'a.b.c.d.e.f.in1': 1,
            'a.b.c.d.e.f.out1?': None,
        })

        assert ret == [{'a.b.c.d.e.f.out1': 1}]

    def test_nested_property_type(self):
        gc = graphcore.Graphcore()

        def function(id):
            return str(id)

        gc.property_type('d', 'es', 'e')
        gc.register_rule(['e.id'], 'e.name', function=function)
        ret = gc.query({
            'c.d.es.id': 1,
            'c.d.es.name?': None,
        })

        assert ret == [{'c.d.es.name': '1'}]

    def test_constraint_on_missing_property(self):
        """
        ensure that even if a constraint, or fact isn't required to compute
        the output directly, it is still used to constrain the values.
        """
        gc = graphcore.Graphcore()

        gc.register_rule(['x.id'], 'x.name', function=None)

        with pytest.raises(graphcore.PathNotFound):
            gc.query({
                'x.missing': 1,
                'x.id': 1,
                'x.name?': None
            })

    @pytest.mark.xfail
    def test_long_input(self):
        gc = graphcore.Graphcore()

        gc.register_rule(
            ['x.y.name'], 'x.y_name', function=lambda y_name: y_name
        )

        ret = gc.query({
            'x.y.name': 'abc',
            'x.y_name?': None
        })

        assert ret == [{'x.y_name': 'abc'}]

    def test_grounded_nested_value(self):
        gc = graphcore.Graphcore()

        gc.register_rule(
            ['x.y.id'], 'x.z', function=lambda id: id
        )

        gc.query({
            'x': [{
                'y.id': 1,
                'z?': None,
            }]
        })

    def test_filter_nested_value(self):
        gc = graphcore.Graphcore()

        gc.register_rule(
            ['x.y.id'], 'x.z', function=lambda id: [1, 2, 3],
            cardinality='many'
        )

        query = {
            'x': [{
                'y.id': 1,
                'z>': 1,
                'z?': None,
            }]
        }

        print(gc.explain(query))
        ret = gc.query(query)

        assert ret == [{
            'x': [{
                'z': 2,
            }, {
                'z': 3,
            }],
        }]

    def test_search_outputs(self):
        gc = graphcore.Graphcore()

        gc.register_rule([], 'abc.id')
        gc.register_rule([], 'abc.xyz.id')
        gc.register_rule([], 'xyz.id')

        assert gc.search_outputs('abc') == [
            'abc.id', 'abc.xyz.id'
        ]

        assert gc.search_outputs(prefix='abc') == [
            'abc.id', 'abc.xyz.id'
        ]

        assert gc.search_outputs('xyz') == [
            'abc.xyz.id', 'xyz.id'
        ]

        assert gc.search_outputs(prefix='xyz') == [
            'xyz.id'
        ]

    def test_nested_results(self):
        gc = graphcore.Graphcore()

        gc.register_rule(
            [], 'x.id', function=lambda: [1, 2, 3], cardinality='many'
        )
        gc.register_rule(
            ['x.id'], ['x.ys.z'], function=lambda id: id
        )

        ret = gc.query({
            'x.ys': [{
                'z?': None,
            }]
        })

        assert ret == [{
            'x.ys': [{'z': 1}],
        }, {
            'x.ys': [{'z': 2}],
        }, {
            'x.ys': [{'z': 3}],
        }]


class TestQuerySearch(unittest.TestCase):

    def __init__(self, *args):
        super(TestQuerySearch, self).__init__(*args)

    def test_clauses_with_unbound_output(self):
        query = graphcore.QuerySearch(testgraphcore, {
            'user.id': 1,
            'user.name': graphcore.OutVar(),
        })
        unbound_clauses = query.clauses_with_unbound_outvar()
        clauses = []
        for clause in unbound_clauses:
            query._ground(clause)
            clauses.append(clause)

        self.assertEqual(
            clauses,
            [query.query.clause_map[graphcore.Path('user.name')]],
        )

    def test_clause_with_unbound_output(self):
        query = graphcore.QuerySearch(testgraphcore, {
            'user.name?': None,
        })
        clauses = query.clause_with_unbound_outvar()
        self.assertEqual(
            clauses,
            query.query[0],
        )

    def test_query_search_nested(self):
        query = graphcore.QuerySearch(testgraphcore, {
            'user.id': 1,
            'user.books': [{
                'id?': None,
            }],
        })
        query.backward()

        user_book_id_nodes = [
            node for node in query.call_graph.nodes
            if 'user.books.id' in node.outgoing_paths
        ]

        assert len(query.call_graph.nodes) == 1
        assert len(user_book_id_nodes) == 1

    def test_call_graph_repr(self):
        query = graphcore.QuerySearch(testgraphcore, {
            'user.id': 1,
            'user.name?': None,
        })
        query.backward()

        repr(query.call_graph)

    def test_call_graph_relation(self):
        query = graphcore.QuerySearch(testgraphcore, {
            'user.id': 1,
            'user.books.id>': 1,
            'user.books.name?': None,
        })
        query.backward()

        user_book_id_nodes = [
            node for node in query.call_graph.nodes
            if 'user.books.id' in node.outgoing_paths
        ]

        self.assertEqual(len(user_book_id_nodes), 1)
        self.assertEqual(user_book_id_nodes[0].relations, (Relation('>', 1),))

    def test_call_graph_relation_and_outvar(self):
        query = graphcore.QuerySearch(testgraphcore, {
            'user.id': 1,
            'user.books.id?': None,
            'user.books.id>': 1,
        })
        query.backward()

        user_book_id_nodes = [
            node for node in query.call_graph.nodes
            if 'user.books.id' in node.outgoing_paths
        ]

        self.assertEqual(len(user_book_id_nodes), 1)
        self.assertEqual(user_book_id_nodes[0].relations, (Relation('>', 1),))

    def test_call_graph_unrelated_relation(self):
        query = graphcore.QuerySearch(testgraphcore, {
            'user.id': 1,
            'user.books.id?': None,
            'user.books.name<': 'S',
        })
        query.backward()

        user_book_name_nodes = [
            node for node in query.call_graph.nodes
            if 'user.books.name' in node.outgoing_paths
        ]

        self.assertEqual(len(user_book_name_nodes), 1)

    def test_call_graph_ungrounded_query(self):
        gc = graphcore.Graphcore()

        gc.register_rule(
            [], 'user.id', cardinality='many', function=lambda: [1, 2, 3]
        )
        query = graphcore.QuerySearch(gc, {
            'user.id?': None,
        })
        query.backward()

        assert len(query.call_graph.nodes) == 1

        assert query.call_graph.nodes[0].outgoing_paths == ('user.id',)

    def test_call_graph_ungrounded_non_root(self):
        gc = graphcore.Graphcore()

        gc.register_rule(
            [], 'user.id', cardinality='many', function=lambda: [1, 2, 3]
        )

        query = graphcore.QuerySearch(gc, {
            'book.id': 1,
            'book.user.id?': None,
        })
        with pytest.raises(graphcore.PathNotFound):
            query.backward()

    def test_explain(self):
        gc = graphcore.Graphcore()
        assert isinstance(gc.explain({}), six.string_types)


class TestClause(unittest.TestCase):

    def test_has_bound_value(self):
        clause = graphcore.Clause('meter.id', 1)
        self.assertFalse(isinstance(clause.rhs, graphcore.Var))

    def test_has_unbound_outvar(self):
        clause = graphcore.Clause('meter.id', graphcore.OutVar())
        self.assertTrue(isinstance(clause.rhs, graphcore.Var))

    def test_relation(self):
        lhs = 'meter.id'
        relations = ['>', '<', '>=', '<=', '!=', '|=']
        for relation in relations:
            clause = graphcore.Clause(lhs+relation, 1)
            self.assertEquals(clause.relation, Relation(relation, 1))
            self.assertEquals(clause.lhs, lhs)

    def test_convert_to_constraint(self):
        clause = graphcore.Clause('x', 1)
        clause.convert_to_constraint()
        assert clause == graphcore.Clause('x==', 1)

    def test_clause_eq(self):
        assert not graphcore.Clause('x', 1) == graphcore.Clause('y', 1)
        assert not graphcore.Clause('x', 1) == graphcore.Clause('x', 2)
        assert not graphcore.Clause('x>', 1) == graphcore.Clause('x<', 1)
        assert not graphcore.Clause('x?', None) == graphcore.Clause('x>', 1)

        assert not graphcore.Clause('x', 1) != graphcore.Clause('x', 1)

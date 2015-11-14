import unittest
import pytest

from . import graphcore
from .relation import Relation
from .test_harness import testgraphcore


class hashabledict(dict):
    """ a hashable dict to make it easier to compare query results """

    def __hash__(self):
        return hash(tuple(sorted(self.items())))


def make_ret_comparable(ret):
    """ convert lists to sets and dicts in them to frozen dicts """
    if isinstance(ret, list):
        return set(make_ret_comparable(e) for e in ret)
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


class TestGraphcore(unittest.TestCase):

    def test_available_rules_string(self):
        testgraphcore.available_rules_string()

    def assertRetEqual(self, ret1, ret2):
        self.assertEqual(
            make_ret_comparable(ret1),
            make_ret_comparable(ret2),
        )

    def test_missing_rule(self):
        with pytest.raises(IndexError):
            testgraphcore.lookup_rule_for_clause(
                graphcore.Clause('a.x', None)
            )

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
        with pytest.raises(IndexError):
            gc.query({
                'book.id': 1,
                'book.user.id?': None,
            })


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
        self.assertEqual(user_book_id_nodes[0].relation, Relation('>', 1))

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
        self.assertEqual(user_book_id_nodes[0].relation, Relation('>', 1))

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
        with pytest.raises(IndexError):
            query.backward()


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

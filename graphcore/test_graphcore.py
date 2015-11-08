import unittest

from . import graphcore
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
            clause.ground()
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


class TestClause(unittest.TestCase):

    def test_has_bound_value(self):
        clause = graphcore.Clause('meter.id', 1)
        self.assertFalse(clause.has_unbound_outvar())

    def test_has_unbound_outvar(self):
        clause = graphcore.Clause('meter.id', graphcore.OutVar())
        self.assertTrue(clause.has_unbound_outvar())

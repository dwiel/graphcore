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


class TestGraphcore(unittest.TestCase):

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

import unittest

import graphcore

testgraphcore = graphcore.Graphcore()


@testgraphcore.rule(['user.name'], 'user.abbreviation')
def user_name_to_abbreviation(name):
    return ''.join(part[0].upper() for part in name.split(' '))


USER_ID_TO_USER_NAME = {
    1: 'John Smith',
}


@testgraphcore.rule(['user.id'], 'user.name')
def user_id_to_user_name(id):
    return USER_ID_TO_USER_NAME[id]


testgraphcore.has_many('user', 'books', 'book')


@testgraphcore.rule(['user.id'], 'user.books.id', cardinality='many')
def user_id_to_books_id(id):
    # this would normally come out of a db
    return [1, 2, 3]


BOOK_ID_TO_BOOK_NAME = {
    1: 'The Giver',
    2: 'REAMDE',
    3: 'The Diamond Age',
}


@testgraphcore.rule(['book.id'], 'book.name')
def book_id_to_book_name(id):
    print 'book_id_to_book_name', id
    return BOOK_ID_TO_BOOK_NAME[id]


class hashabledict(dict):
    def __hash__(self):
        return hash(tuple(sorted(self.items())))


def make_ret_comparable(ret):
    """ convert lists to sets and dicts in them to frozen dicts """
    if isinstance(ret, list):
        return set(make_ret_comparable(e) for e in ret)
    elif isinstance(ret, dict):
        return hashabledict(
            (k, make_ret_comparable(v)) for k, v in ret.iteritems()
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


class TestQueryPlan(unittest.TestCase):
    def test_clauses_with_unbound_output(self):
        query = graphcore.QueryPlan(testgraphcore, {
            'user.id': 1,
            'user.name': testgraphcore.outvar(),
        })
        unbound_clauses = query.clauses_with_unbound_outvar()
        clauses = []
        for clause in unbound_clauses:
            clause.ground()
            clauses.append(clause)

        self.assertEqual(
            clauses,
            [query.query[1]],
        )

    def test_clause_with_unbound_output(self):
        query = graphcore.QueryPlan(testgraphcore, {
            'user.name?': None,
        })
        clauses = query.clause_with_unbound_outvar()
        self.assertEqual(
            clauses,
            query.query[0],
        )


class TestClause(unittest.TestCase):
    def test_has_bound_value(self):
        clause = graphcore.Clause('meter.id', 1)
        self.assertFalse(clause.has_unbound_outvar())

    def test_has_unbound_outvar(self):
        clause = graphcore.Clause('meter.id', graphcore.OutVar())
        self.assertTrue(clause.has_unbound_outvar())


class TestPath(unittest.TestCase):
    def test_subpaths(self):
        path = graphcore.Path('a.b.c.d')
        self.assertEqual(
            list(path.subpaths()), [
                graphcore.Path('c.d'),
                graphcore.Path('b.c.d'),
                graphcore.Path('a.b.c.d')
            ]
        )

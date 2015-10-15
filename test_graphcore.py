import unittest

import graphcore

testgraphcore = graphcore.Graphcore()


@testgraphcore.input(('users.id',))
@testgraphcore.output('users.name')
def user_id_to_user_name(id):
    return 'name_'+str(id)


class TestGraphcore(unittest.TestCase):
    def test_basic(self):
        ret = testgraphcore.query({
            'users.id': 1,
            'users.name': testgraphcore.outvar(),
        })
        self.assertEqual(ret, {'users.name': 'name_1'})


class TestQueryPlan(unittest.TestCase):
    """
    def test_clauses_with_unbound_output(self):
        query = graphcore.QueryPlan(testgraphcore, {
            'users.id': 1,
            'users.name': testgraphcore.outvar(),
        })
        clauses = list(query.clauses_with_unbound_outvar())
        self.assertEqual(
            clauses,
            [query.query[1]],
        )
    """

    def test_clause_with_unbound_output(self):
        query = graphcore.QueryPlan(testgraphcore, {
            'users.name': testgraphcore.outvar(),
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

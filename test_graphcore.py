import unittest

import graphcore

testgraphcore = graphcore.Graphcore()


@testgraphcore.input(('user.name',))
@testgraphcore.output('user.abbreviation')
def user_name_to_abbreviation(name):
    return ''.join(part[0].upper() for part in name.split(' '))


@testgraphcore.input(('user.id',))
@testgraphcore.output('user.name')
def user_id_to_user_name(id):
    return 'John Bob Smith '+str(id)


class TestGraphcore(unittest.TestCase):
    def test_basic(self):
        ret = testgraphcore.query({
            'user.id': 1,
            'user.name?': None,
        })
        self.assertEqual(ret, {'user.name': 'John Bob Smith 1'})

    def test_basic_two_step(self):
        ret = testgraphcore.query({
            'user.id': 1,
            'user.abbreviation?': None,
        })
        self.assertEqual(ret, {'user.abbreviation': 'JBS1'})


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

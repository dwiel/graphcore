import unittest

from sql_query_plan import SQLQuery, mysql_col


class AssertSQLQueryEqual():
    def assertSQLQueryEqual(self, query1, query2):
        self.assertEqual(query1.tables, query2.tables)
        self.assertEqual(query1.selects, query2.selects)
        self.assertEqual(query1.where, query2.where)


class TestSQLQueryPlan(unittest.TestCase, AssertSQLQueryEqual):
    def test_simple_query_merge(self):
        combined = SQLQuery(['books'], 'name', {
            'books.id': SQLQuery(['users', 'books'], 'books.id', {
                'users.id': id,
                'users.id': mysql_col('books.id'),
            })
        })

        self.assertSQLQueryEqual(
            combined,
            SQLQuery('users, books', 'name', {
                'users.id': id,
                'users.id': mysql_col('books.id'),
                'books.id': mysql_col('books.id'),
            })
        )

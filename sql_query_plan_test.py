import unittest

from .sql_query_plan import SQLQuery, mysql_col


class AssertSQLQueryEqual():
    def assertSQLQueryEqual(self, query1, query2):
        self.assertEqual(query1.tables, query2.tables)
        self.assertEqual(query1.selects, query2.selects)
        self.assertEqual(query1.where, query2.where)


class TestSQLQueryPlan(unittest.TestCase, AssertSQLQueryEqual):
    def test_simple_query_merge(self):
        book_id = SQLQuery(['users', 'books'], 'books.id', {
            'users.id': 1,
            'books.user_id': mysql_col('user.id'),
        })

        combined = SQLQuery(['books'], 'books.name', {
            'books.id': book_id
        })

        self.assertSQLQueryEqual(
            combined,
            SQLQuery('users, books', 'books.name', {
                'users.id': 1,
                'books.user_id': mysql_col('user.id'),
            })
        )

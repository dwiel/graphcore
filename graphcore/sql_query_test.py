import unittest

from .sql_query import SQLQuery, mysql_col


class AssertSQLQueryEqual():
    def assertSQLQueryEqual(self, query1, query2):
        self.assertEqual(query1.tables, query2.tables)
        self.assertEqual(query1.selects, query2.selects)
        self.assertEqual(query1.where, query2.where)
        self.assertEqual(query1.input_mapping, query2.input_mapping)


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

    def test_simple_add(self):
        first_name = SQLQuery(['users'], 'users.first_name', {
            'users.id': 1,
        })
        last_name = SQLQuery(['users'], 'users.last_name', {
            'users.id': 1,
        })

        first_and_last_name = SQLQuery(
            ['users'], ['users.first_name', 'users.last_name'], {
                'users.id': 1,
            }
        )

        self.assertSQLQueryEqual(first_name + last_name, first_and_last_name)

    def test_hash(self):
        def build():
            SQLQuery(['users'], 'users.first_name', {
                'users.id': 1,
            }, {
                'users.name': 'name',
            })

        self.assertEqual(hash(build()),  hash(build()))


import mock

from .sql_reflect import sql_reflect_table, sql_reflect
from .graphcore import Graphcore
from .rule import Rule
from .sql_query import SQLQuery


class MockEngine():
    def execute(self, sql):
        if sql == 'describe users':
            return [['name']]
        elif sql == 'show tables':
            return [['users']]


def test_sql_reflect_table():
    engine = MockEngine()
    gc = Graphcore()
    sql_reflect_table(gc, engine, 'users')

    assert len(gc.rules) == 1
    assert gc.rules == [
        Rule(SQLQuery(
            'users', 'users.name', {}, input_mapping={
                'id': 'users.id',
            }, one_column=True, first=True
        ), ['users.id'], 'users.name', 'one')
    ]


def test_sql_reflect():
    engine = MockEngine()
    gc = Graphcore()
    method = 'graphcore.sql_reflect.sql_reflect_table'
    with mock.patch(method, mock.Mock()) as m:
        sql_reflect(gc, engine)

    assert m.mock_called_once_with(gc, engine, 'users')

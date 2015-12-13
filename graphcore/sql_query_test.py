import pytest
import sql_query_dict

try:
    from unittest import mock
except ImportError:
    import mock

from .sql_query import SQLQuery
from .call_graph import Node


def test_unqualified_select():
    # ensure first node is checked
    with pytest.raises(ValueError):
        SQLQuery.merge_parent_child(
            Node(None, [], [], SQLQuery(['users'], 'id', {}), 'one'),
            Node(None, [], [], SQLQuery(['users'], 'users.id', {}), 'one'),
        )

    # ensure second node is checked
    with pytest.raises(ValueError):
        SQLQuery.merge_parent_child(
            Node(None, [], [], SQLQuery(['users'], 'users.id', {}), 'one'),
            Node(None, [], [], SQLQuery(['users'], 'id', {}), 'one'),
        )


def test_simple_query_merge():
    book_id = SQLQuery(['users', 'books'], 'books.id', {
        'users.id': 1,
        'books.user_id': sql_query_dict.mysql_col('user.id'),
    })

    combined = SQLQuery(['books'], 'books.name', {
        'books.id': book_id
    })

    combined.flatten()

    assert combined == SQLQuery(
        'users, books', 'books.name', {
            'users.id': 1,
            'books.user_id': sql_query_dict.mysql_col('user.id'),
        })


def test_simple_add():
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

    assert first_name + last_name == first_and_last_name


def test_merge_unbound_primary_key_and_property():
    users_all_ids = Node(
        None, [], ['user.id'], SQLQuery(['users'], 'users.id', {}), 'many'
    )
    users_name = Node(
        None, ['user.id'], ['user.name'], SQLQuery(
            ['users'], 'users.name', {}, input_mapping={
                'id': 'users.id',
            }),
        'one'
    )

    # TODO: this assumes that we didnt also want users.id, which will depend
    # on the query
    users_all_names = Node(
        None, [], ['user.name', 'user.id'], SQLQuery(
            ['users'], ['users.name', 'users.id'], {}
        ), 'many',
    )

    merged = SQLQuery.merge_parent_child(
        users_all_ids, users_name
    )

    print(merged)
    print(users_all_names)
    assert merged == users_all_names


def test_merge_parent_and_property_multi_output():
    users_id_from_last_name = Node(
        None, ['user.last_name'], ['user.id', 'user.phone'], SQLQuery(
            ['users'], ['users.id', 'users.phone'], {}, input_mapping={
                'last_name': 'users.last_name',
            }
        ), 'many'
    )
    users_first_name_from_id = Node(
        None, ['user.id'], ['user.first_name'], SQLQuery(
            ['users'], 'users.first_name', {}, input_mapping={
                'id': 'users.id',
            }, first=True
        ), 'one'
    )

    # TODO: this assumes that we didnt also want users.id, which will depend
    # on the query
    users_first_name_from_last_name = Node(
        None, ['user.last_name'], ['user.first_name', 'user.id', 'user.phone'],
        SQLQuery(
            ['users'], ['users.first_name', 'users.id', 'users.phone'], {},
            input_mapping={'last_name': 'users.last_name'}
        ), 'many'
    )

    merged = SQLQuery.merge_parent_child(
        users_id_from_last_name, users_first_name_from_id
    )

    print(merged)
    print(users_first_name_from_last_name)
    assert merged == users_first_name_from_last_name


def test_merge_parent_and_property():
    users_id_from_last_name = Node(
        None, ['user.last_name'], ['user.id'], SQLQuery(
            ['users'], 'users.id', {}, input_mapping={
                'last_name': 'users.last_name',
            }),
        'many'
    )
    users_first_name_from_id = Node(
        None, ['user.id'], ['user.first_name'], SQLQuery(
            ['users'], 'users.first_name', {}, input_mapping={
                'id': 'users.id',
            }, first=True),
        'one'
    )

    # TODO: this assumes that we didnt also want users.id, which will depend
    # on the query
    users_first_name_from_last_name = Node(
        None, ['user.last_name'], ['user.first_name', 'user.id'], SQLQuery(
            ['users'], ['users.first_name', 'users.id'], {}, input_mapping={
                'last_name': 'users.last_name',
            }
        ), 'many'
    )

    merged = SQLQuery.merge_parent_child(
        users_id_from_last_name, users_first_name_from_id
    )

    # assert that the merged query isn't the same object as one of the oringal.
    assert id(merged.function) not in (
        id(users_id_from_last_name.function),
        id(users_first_name_from_id.function),
    )

    print(merged)
    print(users_first_name_from_last_name)
    assert merged == users_first_name_from_last_name


def test_hash():
    def build():
        SQLQuery(['users'], 'users.first_name', {
            'users.id': 1,
        }, {
            'users.name': 'name',
        })

    assert hash(build()) == hash(build())


def test_assert_flattenable_table_alias():
    with pytest.raises(ValueError):
        SQLQuery(['users u'], 'users.id', {}).flatten()


def test_assert_flattenable_column_with_no_table():
    with pytest.raises(ValueError):
        SQLQuery(['users'], 'id', {}).flatten()


def test_assert_flattenable_clause_with_no_table():
    with pytest.raises(ValueError):
        SQLQuery(['users'], 'users.id', {'id': 1}).flatten()


def test_call():
    sql_query = SQLQuery(['users'], 'users.id', {'users.name': 'John'})
    sql_query.driver = mock.MagicMock(return_value=3)
    assert sql_query() == 3


def test_call_one_column():
    sql_query = SQLQuery(
        ['users'], 'users.id', {'users.name': 'John'}, one_column=True
    )
    sql_query.driver = mock.MagicMock(return_value=[(3,)])
    assert sql_query() == [3]


def test_call_first_true():
    sql_query = SQLQuery(
        ['users'], 'users.id', {'users.name': 'John'}, first=True,
    )
    sql_query.driver = mock.MagicMock(return_value=[(3,)])
    assert sql_query() == (3,)


def test_call_one_column_first_true():
    sql_query = SQLQuery(
        ['users'], 'users.id', {'users.name': 'John'},
        one_column=True, first=True,
    )
    sql_query.driver = mock.MagicMock(return_value=[(3,)])
    assert sql_query() == 3


def test_call_with_input_mapping():
    sql_query = SQLQuery(['users'], 'users.id', {}, input_mapping={
        'name': 'users.name'
    })

    # a weird driver whose return value is the length of the first value passed
    # in
    sql_query.driver = lambda SQL, vals: len(vals[0])

    assert sql_query(name='bob') == 3
    assert sql_query(name='john') == 4


def test_copy():
    sql_query = SQLQuery(
        ['x'], ['x.a'], {'x.b': 2}, input_mapping={'x_c': 'x.c'}
    )
    sql_query_copy = sql_query.copy()

    sql_query.tables.add('y')
    sql_query.selects.append('y.a')
    sql_query.where['y.b'] = 2
    sql_query.input_mapping['y_c'] = 'y.c'

    assert len(sql_query_copy.tables) == 1
    assert len(sql_query_copy.selects) == 1
    assert len(sql_query_copy.where) == 1
    assert len(sql_query_copy.input_mapping) == 1


def test_driver():
    import sqlalchemy

    engine = sqlalchemy.create_engine('sqlite://')

    from sqlalchemy import MetaData, Table, Column, Integer, String

    meta = MetaData()
    users = Table(
        'users', meta,
        Column('id', Integer, primary_key=True),
        Column('name', String(255)),
    )
    users.create(engine)

    name = 'bob'
    engine.execute(users.insert(), id=1, name=name)

    sql_query = SQLQuery(
        ['users'], ['name'], {'id': 1}, engine=engine, param_style='?'
    )

    assert sql_query()[0].name == name
    assert sql_query()[0][0] == name

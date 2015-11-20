import pytest
import sql_query_dict

try:
    from unittest import mock
except ImportError:
    import mock

from .sql_query import SQLQuery
from .rule import Rule


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
    users_all_ids = Rule(
        SQLQuery(['users'], 'users.id', {}),
        [], ['user.id'], 'many',
    )
    users_name = Rule(
        SQLQuery(['users'], 'users.name', {}, input_mapping={
            'id': 'users.id',
        }), ['user.id'], ['user.name'], 'one'
    )

    # TODO: this assumes that we didnt also want users.id, which will depend
    # on the query
    users_all_names = Rule(
        SQLQuery(
            ['users'], ['users.name', 'users.id'], {}
        ), [], ['user.name'], 'many',
    )

    merged = SQLQuery.merge_parent_child(
        users_all_ids, users_name
    )

    assert merged == users_all_names


def test_merge_parent_and_property():
    users_id_from_last_name = Rule(
        SQLQuery(['users'], 'users.id', {}, input_mapping={
            'last_name': 'users.last_name',
        }), ['user.last_name'], ['user.id'], 'many'
    )
    users_first_name_from_id = Rule(
        SQLQuery(['users'], 'users.first_name', {}, input_mapping={
            'id': 'users.id',
        }, first=True), ['user.id'], ['user.first_name'], 'one'
    )

    # TODO: this assumes that we didnt also want users.id, which will depend
    # on the query
    users_first_name_from_last_name = Rule(
        SQLQuery(
            ['users'], ['users.first_name', 'users.id'], {}, input_mapping={
                'last_name': 'users.last_name',
            }
        ), ['user.last_name'], ['user.first_name'], 'many'
    )

    merged = SQLQuery.merge_parent_child(
        users_id_from_last_name, users_first_name_from_id
    )

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

import pytest
import sqlalchemy

from .graphcore import Graphcore, PropertyType
from .rule import Rule
from .sql_query import SQLQuery
from .sql_reflect import SQLReflector


@pytest.fixture
def engine():
    engine = sqlalchemy.create_engine('sqlite://')

    from sqlalchemy import MetaData, Table, Column, Integer, String

    meta = MetaData()
    users = Table(
        'users', meta,
        Column('id', Integer, primary_key=True),
        Column('name', String(255)),
    )
    users.create(engine)

    books = Table(
        'books', meta,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer),
    )
    books.create(engine)

    return engine


@pytest.fixture
def singular_table_name_engine():
    engine = sqlalchemy.create_engine('sqlite://')

    from sqlalchemy import MetaData, Table, Column, Integer, String

    meta = MetaData()
    things = Table(
        'thing', meta,
        Column('id', Integer, primary_key=True),
        Column('name', String(255)),
    )
    things.create(engine)

    return engine


@pytest.fixture
def gc():
    return Graphcore()


def test_sql_reflect(gc, engine):
    SQLReflector(gc, engine, SQLQuery)

    assert set(gc.rules) == set([
        Rule(SQLQuery(
            'users', 'users.id', {}, one_column=True
        ), [], 'user.id', 'one'),
        Rule(SQLQuery(
            'users', 'users.name', {}, input_mapping={
                'id': 'users.id',
            }, one_column=True, first=True
        ), ['user.id'], 'user.name', 'one'),
        Rule(SQLQuery(
            'books', 'books.user_id', {}, input_mapping={
                'id': 'books.id',
            }, one_column=True, first=True
        ), ['book.id'], 'book.user.id', 'one'),
        Rule(SQLQuery(
            'books', 'books.id', {}, input_mapping={
                'id': 'books.user_id',
            }, one_column=True, first=False
        ), ['user.id'], 'user.books.id', 'many'),
        Rule(SQLQuery(
            'books', 'books.id', {}, one_column=True
        ), [], 'book.id', 'one'),
    ])

    assert gc.schema.property_types == [
        PropertyType('book', 'user', 'user'),
        PropertyType('user', 'books', 'book'),
    ]


def test_sql_reflect_relationship(gc, singular_table_name_engine):
    SQLReflector(gc, singular_table_name_engine, SQLQuery)

    assert set(gc.rules) == set([
        Rule(SQLQuery(
            'thing', 'thing.id', {}, one_column=True
        ), [], 'thing.id', 'one'),
        Rule(SQLQuery(
            'thing', 'thing.name', {}, input_mapping={
                'id': 'thing.id',
            }, one_column=True, first=True
        ), ['thing.id'], 'thing.name', 'one'),
    ])

    assert gc.schema.property_types == []

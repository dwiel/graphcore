"""
Integration testing graphcore queries on data in a sqlite in memory database
"""

import pytest
import sqlalchemy
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


from .graphcore import Graphcore
from .sql_query import SQLQuery
from .sql_reflect import SQLReflector


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)


class Book(Base):
    __tablename__ = 'books'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)


@pytest.fixture
def engine():
    engine = sqlalchemy.create_engine('sqlite://')
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def SQLAlchemyQueryClass(engine):
    class SQLAlchemyQuery(SQLQuery):
        def driver(self, SQL, values):
            return engine.execute(SQL, values)

    return SQLAlchemyQuery


@pytest.fixture
def gc(engine, SQLAlchemyQueryClass):
    gc = Graphcore()
    SQLReflector(gc, engine, SQLAlchemyQueryClass)

    return gc


@pytest.fixture
def session(engine):
    return sessionmaker(bind=engine)()


def test(gc, session):
    fred = User()
    fred.name = 'Fred'

    session.add(fred)
    session.commit()

    ret = gc.query({
        'user.name': 'Fred',
        'user.id?': None,
    })

    assert len(ret) == 1

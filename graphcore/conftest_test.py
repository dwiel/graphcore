import mock
import pytest

from .call_graph import CallGraph
from .sql_query import SQLQuery
from .conftest import call_graph_repr_compare
from .conftest import sql_query_repr_compare


def test_sql_query_repr_compare():
    assert sql_query_repr_compare(
        SQLQuery('a', 'a.b', {}),
        SQLQuery('a', 'a.c', {})
    ) is not None


def test_call_graph_repr_compare():
    assert call_graph_repr_compare(CallGraph(), CallGraph()) is not None


def test_pytest_assertrepr_compare_sql_query():
    sql_query1 = SQLQuery('users', 'users.id', {})
    sql_query2 = SQLQuery('houses', 'houses.id', {})

    with mock.patch('graphcore.conftest.sql_query_repr_compare') as fn:
        with pytest.raises(Exception):
            assert sql_query1 == sql_query2

        # not sure why its getting called more than once ...
        assert len(fn.mock_calls) != 0


def test_pytest_assertrepr_compare_call_graph():
    call_graph1 = CallGraph()
    call_graph2 = CallGraph()

    call_graph2.add_node(['a'], [], None, 'one')

    with mock.patch('graphcore.conftest.call_graph_repr_compare') as fn:
        with pytest.raises(Exception):
            assert call_graph1 == call_graph2

        # not sure why its getting called more than once ...
        assert len(fn.mock_calls) != 0

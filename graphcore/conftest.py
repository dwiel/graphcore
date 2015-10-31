import difflib

from .call_graph import CallGraph
from .sql_query import SQLQuery


def call_graph_repr_compare(left, right):
    return list(difflib.ndiff(
        repr(left).splitlines(1),
        repr(right).splitlines(1),
    ))


def sql_query_repr_compare(left, right):
    return list(difflib.ndiff(
        repr(left).splitlines(1),
        repr(right).splitlines(1),
    ))


def pytest_assertrepr_compare(op, left, right):
    """ pytest helper to make CallGraph comparison easier """
    if isinstance(left, CallGraph) and isinstance(right, CallGraph):
        if op == '==':
            return call_graph_repr_compare(left, right)
    elif isinstance(left, SQLQuery) and isinstance(right, SQLQuery):
        if op == '==':
            return sql_query_repr_compare(left, right)

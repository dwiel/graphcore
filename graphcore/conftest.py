import difflib

from .call_graph import CallGraph


def pytest_assertrepr_compare(op, left, right):
    if isinstance(left, CallGraph) and isinstance(right, CallGraph):
        if op == '==':
            return list(difflib.ndiff(
                repr(left).splitlines(1),
                repr(right).splitlines(1),
            ))



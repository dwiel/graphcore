import pytest

from .relation import Relation
from .query_plan import QueryPlan
from .rule import Rule
from .call_graph import Node


def multiple_outputs(in1):
    return in1, in1 + 1


def test_query_plan_multiple_outputs():
    query_plan = QueryPlan({'a.in1': 1}, ['a.out1', 'a.out2'])
    rule = Rule(
        multiple_outputs, ['a.in1'], ['a.out1', 'a.out2'], 'one'
    )
    query_plan.append(
        Node(None, ['a.in1'], ['a.out1', 'a.out2'], rule)
    )

    ret = query_plan.execute()

    assert ret == [{'a.out1': 1, 'a.out2': 2}]


def test_query_plan_multiple_outputs_cardinality_many():
    query_plan = QueryPlan({'a.in1': 1}, ['a.out1', 'a.out2'])
    rule = Rule(
        lambda in1: in1, ['a.in1'], ['a.out1', 'a.out2'], 'many'
    )
    query_plan.append(
        Node(None, ['a.in1'], ['a.out1', 'a.out2'], rule)
    )

    with pytest.raises(NotImplementedError):
        query_plan.execute()


def test_query_plan_relation():
    query_plan = QueryPlan({}, ['a.out'])
    rule = Rule(
        lambda: [1, 2], [], ['a.out'], 'many'
    )
    query_plan.append(
        Node(None, [], ['a.out'], rule, relation=Relation('>', 1))
    )

    ret = query_plan.execute()

    assert ret == [{'a.out': 2}]

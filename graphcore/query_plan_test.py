from .query_plan import QueryPlan
from .rule import Rule
from .call_graph import Node
from .path import Path


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

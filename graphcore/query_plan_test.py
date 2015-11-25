from .relation import Relation
from .query_plan import QueryPlan
from .call_graph import Node


def multiple_outputs(in1):
    return in1, in1 + 1


def test_query_plan_multiple_outputs():
    query_plan = QueryPlan({'a.in1': 1}, ['a.out1', 'a.out2'], {})
    query_plan.append(Node(
        None, ['a.in1'], ['a.out1', 'a.out2'], multiple_outputs, 'one'
    ))

    ret = query_plan.execute()

    assert ret == [{'a.out1': 1, 'a.out2': 2}]


def test_query_plan_multiple_outputs_cardinality_many():
    query_plan = QueryPlan({'a.in1': 1}, ['a.out1', 'a.out2'], {})
    query_plan.append(Node(
        None, ['a.in1'], ['a.out1', 'a.out2'],
        lambda in1: [[in1, in1+1], [10+in1, 10+in1+1]],
        'many'
    ))

    ret = query_plan.execute()

    assert ret == [
        {'a.out1': 1, 'a.out2': 2},
        {'a.out1': 11, 'a.out2': 12},
    ]


def test_query_plan_relation():
    query_plan = QueryPlan({}, ['a.out'], {})
    query_plan.append(Node(
        None, [], ['a.out'], lambda: [1, 2], 'many',
        relations=[Relation('>', 1)])
    )

    ret = query_plan.execute()

    assert ret == [{'a.out': 2}]


def test_query_plan_multi_relation():
    query_plan = QueryPlan({}, ['a.out1', 'a.out2'], {})
    query_plan.append(Node(
        None, [], ['a.out1', 'a.out2'], lambda: [[1, 1], [2, 2], [3, 3]],
        'many', relations=[Relation('>', 1), Relation('<', 3)])
    )

    ret = query_plan.execute()

    assert ret == [{'a.out1': 2, 'a.out2': 2}]

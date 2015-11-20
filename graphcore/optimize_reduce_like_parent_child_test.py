from .rule import Rule, Cardinality
from .call_graph import CallGraph

from .optimize_reduce_like_parent_child import reduce_like_parent_child


def set_merge(parent, child):
    return merge(parent, child, set.__or__)


def list_merge(parent, child):
    return merge(parent, child, list.__add__)


def merge(parent, child, function_merge):
    function = function_merge(parent.function, child.function)

    inputs = parent.inputs
    # TODO: dont always merge outputs, if they aren't out nodes,
    # and they dont have any other dependencies, we dont need to
    # keep them
    outputs = parent.outputs + child.outputs

    if parent.cardinality == Cardinality.many and \
            child.cardinality == Cardinality.many:
        cardinality = Cardinality.many
    else:
        cardinality = Cardinality.one

    return Rule(function, inputs, outputs, cardinality)


def test_reduce_like_parent_child():
    # use sets for rule functions, user set.__or__ as merge
    # operation

    call_graph_in = CallGraph()
    call_graph_in.add_node(
        ['a.x'], ['a.y'],
        Rule(set([1]), ['a.x'], ['a.y'], 'one'),
    )
    call_graph_in.add_node(
        ['a.y'], ['a.z'],
        Rule(set([2]), ['a.y'], ['a.z'], 'one'),
    )
    call_graph_in.edge('a.z').out = True

    call_graph_out = reduce_like_parent_child(
        call_graph_in, set, set_merge
    )

    call_graph_expected = CallGraph()
    call_graph_expected.add_node(
        ['a.x'], ['a.z', 'a.y'],
        Rule(set([1, 2]), ['a.x'], ['a.y', 'a.z'], 'one')
    )

    ay = call_graph_out.edge('a.y')
    az = call_graph_out.edge('a.z')
    assert ay.out is False
    assert az.out

    assert len(ay.getters) == 0

    assert call_graph_expected == call_graph_out


def test_reduce_like_parent_child_with_two_children():
    # use sets for rule functions, user set.__or__ as merge
    # operation

    call_graph_in = CallGraph()
    call_graph_in.add_node(
        ['a.x'], ['a.y'],
        Rule(set([1]), ['a.x'], ['a.y'], 'one'),
    )
    call_graph_in.add_node(
        ['a.y'], ['a.z'],
        Rule(set([2]), ['a.y'], ['a.z'], 'one'),
    )
    call_graph_in.add_node(
        ['a.y'], ['a.w'],
        Rule(set([3]), ['a.y'], ['a.w'], 'one'),
    )
    call_graph_in.edge('a.z').out = True
    call_graph_in.edge('a.w').out = True

    call_graph_out = reduce_like_parent_child(
        call_graph_in, set, set_merge
    )

    call_graph_expected = CallGraph()
    call_graph_expected.add_node(
        ['a.x'], ['a.w', 'a.z', 'a.y'],
        Rule(set([1, 2, 3]), ['a.x'], ['a.y', 'a.z', 'a.w'], 'one')
    )

    ay = call_graph_out.edge('a.y')
    az = call_graph_out.edge('a.z')
    aw = call_graph_out.edge('a.w')
    assert ay.out is False
    assert az.out
    assert aw.out

    assert len(ay.getters) == 0

    assert call_graph_expected == call_graph_out


def test_reduce_like_parent_child_with_diffent_type():
    call_graph_in = CallGraph()
    call_graph_in.add_node(
        ['a.x'], ['a.y'],
        Rule(set([1]), ['a.x'], ['a.y'], 'one'),
    )
    call_graph_in.add_node(
        ['a.y'], ['a.z'],
        Rule(set([2]), ['a.y'], ['a.z'], 'one'),
    )
    call_graph_in.edge('a.z').out = True

    call_graph_out = reduce_like_parent_child(
        call_graph_in, list, list_merge
    )

    call_graph_expected = CallGraph()
    call_graph_expected.add_node(
        ['a.x'], ['a.y'],
        Rule(set([1]), ['a.x'], ['a.y'], 'one'),
    )
    call_graph_expected.add_node(
        ['a.y'], ['a.z'],
        Rule(set([2]), ['a.y'], ['a.z'], 'one'),
    )

    ay = call_graph_out.edge('a.y')
    az = call_graph_out.edge('a.z')
    assert ay.out is False
    assert az.out

    assert len(ay.getters) == 1

    assert call_graph_expected == call_graph_out

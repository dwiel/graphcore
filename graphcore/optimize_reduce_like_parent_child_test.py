from .rule import Cardinality
from .path import Path
from .call_graph import CallGraph, Node

from .optimize_reduce_like_parent_child import reduce_like_parent_child


def set_merge(parent, child):
    return merge(parent, child, frozenset.__or__)


def tuple_merge(parent, child):
    return merge(parent, child, tuple.__add__)


def list_merge(parent, child):
    return merge(parent, child, list.__add__)


def merge(parent, child, function_merge):
    function = function_merge(parent.function, child.function)

    incoming_paths = parent.incoming_paths
    # TODO: dont always merge outgoing_paths, if they aren't out nodes,
    # and they dont have any other dependencies, we dont need to
    # keep them
    outgoing_paths = parent.outgoing_paths + child.outgoing_paths

    if parent.cardinality == Cardinality.many and \
            child.cardinality == Cardinality.many:
        cardinality = Cardinality.many
    else:
        cardinality = Cardinality.one

    return Node(None, incoming_paths, outgoing_paths, function, cardinality)


def test_reduce_like_parent_child():
    # use sets for rule functions, user set.__or__ as merge
    # operation

    call_graph_in = CallGraph()
    call_graph_in.add_node(['a.x'], ['a.y'], tuple([1]), 'one')
    call_graph_in.add_node(['a.y'], ['a.z'], tuple([2]), 'one')
    call_graph_in.edge('a.z').out = True

    call_graph_out = reduce_like_parent_child(
        call_graph_in, tuple, tuple_merge
    )

    call_graph_expected = CallGraph()
    call_graph_expected.add_node(
        ['a.x'], ['a.y', 'a.z'], tuple([1, 2]), 'one'
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
    call_graph_in.add_node(['a.x'], ['a.y'], frozenset([1]), 'one')
    call_graph_in.add_node(['a.y'], ['a.z'], frozenset([2]), 'one')
    call_graph_in.add_node(['a.y'], ['a.w'], frozenset([3]), 'one')
    call_graph_in.edge('a.z').out = True
    call_graph_in.edge('a.w').out = True

    call_graph_out = reduce_like_parent_child(
        call_graph_in, frozenset, set_merge
    )

    # setting these as variables makes assert print nicer when it breaks
    ay = call_graph_out.edge('a.y')
    az = call_graph_out.edge('a.z')
    aw = call_graph_out.edge('a.w')
    assert ay.out is False
    assert az.out
    assert aw.out

    assert len(ay.getters) == 0

    assert len(call_graph_out.nodes) == 1
    node = call_graph_out.nodes[0]

    assert set(node.outgoing_paths) == set(map(Path, ['a.w', 'a.z', 'a.y']))
    assert set(node.incoming_paths) == set([Path('a.x')])

    assert node.function == frozenset([1, 2, 3])

    # I think this should be true, but I'm not sure
    # assert node.outgoing_paths == tuple(node.rule.outputs)
    # assert node.incoming_paths == tuple(node.rule.inputs)


def test_reduce_like_parent_child_with_diffent_type():
    call_graph_in = CallGraph()
    call_graph_in.add_node(['a.x'], ['a.y'], frozenset([1]), 'one')
    call_graph_in.add_node(['a.y'], ['a.z'], frozenset([2]), 'one')
    call_graph_in.edge('a.z').out = True

    call_graph_out = reduce_like_parent_child(
        call_graph_in, list, list_merge
    )

    call_graph_expected = CallGraph()
    call_graph_expected.add_node(['a.x'], ['a.y'], frozenset([1]), 'one')
    call_graph_expected.add_node(['a.y'], ['a.z'], frozenset([2]), 'one')

    ay = call_graph_out.edge('a.y')
    az = call_graph_out.edge('a.z')
    assert ay.out is False
    assert az.out

    assert len(ay.getters) == 1

    assert call_graph_expected == call_graph_out

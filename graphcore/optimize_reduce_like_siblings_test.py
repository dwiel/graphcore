from .call_graph import CallGraph

from .optimize_reduce_like_siblings import reduce_like_siblings


def test_reduce_like_siblings():
    # use sets for rule functions, user set.__or__ as merge
    # operation

    call_graph_in = CallGraph()
    call_graph_in.add_node(
        ['user.id'], ['user.first_name'], frozenset([1]), 'one'
    )
    call_graph_in.add_node(
        ['user.id'], ['user.last_name'], frozenset([2]), 'one'
    )

    call_graph_out = reduce_like_siblings(
        call_graph_in, frozenset, frozenset.__or__
    )

    call_graph_expected1 = CallGraph()
    call_graph_expected1.add_node(
        ['user.id'], ['user.first_name', 'user.last_name'],
        frozenset([1, 2]), 'one'
    )
    call_graph_expected1.edge('user.first_name').out = True
    call_graph_expected1.edge('user.last_name').out = True

    call_graph_expected2 = CallGraph()
    call_graph_expected2.add_node(
        ['user.id'], ['user.last_name', 'user.first_name'],
        frozenset([1, 2]), 'one'
    )
    call_graph_expected2.edge('user.first_name').out = True
    call_graph_expected2.edge('user.last_name').out = True

    assert call_graph_expected1 == call_graph_out or \
        call_graph_expected2 == call_graph_out

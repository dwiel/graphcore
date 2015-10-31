from .rule import Rule
from .call_graph import CallGraph

from .optimize_reduce_like_siblings import reduce_like_siblings


def test_reduce_like_siblings():
    # use sets for rule functions, user set.__or__ as merge
    # operation

    call_graph_in = CallGraph()
    call_graph_in.add_node(
        ['user.id'],
        ['user.first_name'],
        Rule(set([1]), ['user.id'], ['user.first_name'], 'one'),
    )
    call_graph_in.add_node(
        ['user.id'],
        ['user.last_name'],
        Rule(set([2]), ['user.id'], ['user.last_name'], 'one'),
    )

    call_graph_out = reduce_like_siblings(call_graph_in, set, set.__or__)

    call_graph_expected = CallGraph()
    call_graph_expected.add_node(
        ['user.id'],
        ['user.first_name', 'user.last_name'],
        Rule(
            set([1, 2]),
            ['user.id'],
            ['user.first_name', 'user.last_name'],
            'one'
        )
    )
    call_graph_expected.edge('user.first_name').out = True
    call_graph_expected.edge('user.last_name').out = True

    assert call_graph_expected == call_graph_out

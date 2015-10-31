from .rule import Rule
from .call_graph import CallGraph

from .optimize_reduce_like_parent_child import reduce_like_parent_child

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
        call_graph_in, set, set.__or__
    )

    call_graph_expected = CallGraph()
    call_graph_expected.add_node(
        ['a.x'], ['a.y', 'a.z'],
        Rule( set([1, 2]), ['a.x'], ['a.y', 'a.z'], 'one')
    )
    
    ay = call_graph_out.edge('a.y')
    az = call_graph_out.edge('a.z')
    assert ay.out == False
    assert az.out == True

    assert len(ay.getters) == 0

    assert call_graph_expected == call_graph_out

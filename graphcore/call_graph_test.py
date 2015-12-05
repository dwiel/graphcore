from .call_graph import Edge, Node
from .relation import Relation


def test_edge_hash():
    assert hash(Edge('a.b.c', [1, 2, 3], [4, 5, 6], False)) == \
        hash(Edge('a.b.c', [], [], True))


def test_edge_ne():
    assert Edge('a.b.c', [], [], True) != Edge('a', [], [], True)


def test_edge_not_ne():
    assert not Edge('a', [1], [2], True) != Edge('a', [], [], False)


def test_explain():
    def f():
        pass

    node = Node(None, ['a.b.c'], ['x.y.z'], f, 'one', None)
    assert 'one' not in node.explain()

    node = Node(None, ['a.b.c'], ['x.y.z'], f, 'many', None)
    assert 'many' in node.explain()

    node = Node(None, ['a.b.c'], ['x.y.z'], f, 'one', (Relation(
        '>', 1
    ),))
    assert '>' in node.explain()

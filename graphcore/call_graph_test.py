from .call_graph import Edge


def test_edge_hash():
    assert hash(Edge('a.b.c', [1, 2, 3], [4, 5, 6], False)) == \
        hash(Edge('a.b.c', [], [], True))


def test_edge_ne():
    assert Edge('a.b.c', [], [], True) != Edge('a', [], [], True)


def test_edge_not_ne():
    assert not Edge('a', [1], [2], True) != Edge('a', [], [], False)

import pytest

from .relation import Relation


def test_relation_repr():
    assert repr(Relation('>', 1)) == "<Relation '>' 1>"


def test_relation_eq_wrong_type():
    with pytest.raises(TypeError):
        Relation('>', 1) == 1


def test_relation_ne():
    assert Relation('>', 1) != Relation('<', 1)


def test_relation_contains():
    assert Relation('|=', [1, 2, 3])(1)
    assert not Relation('|=', [1, 2, 3])(4)


def test_multi_relation():
    relation = Relation(('>', '<'), (1, 3))

    assert relation(1) is False
    assert relation(2) is True
    assert relation(3) is False


def test_relation_merge():
    relation1 = Relation('>', 1)
    relation2 = Relation('<', 3)

    relation = relation1.merge(relation2)

    assert relation.operation == ('>', '<')
    assert relation.value == (1, 3)


def test_multi_relation_merge():
    relation1 = Relation('>', 1)
    relation2 = Relation('<', 3)
    relation3 = Relation('|=', (2, 4, 6))

    relation = relation1.merge(relation2).merge(relation3)

    assert relation.operation == ('>', '<', '|=')
    assert relation.value == (1, 3, (2, 4, 6))

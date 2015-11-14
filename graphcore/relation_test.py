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

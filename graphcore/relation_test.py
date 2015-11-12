from .relation import Relation


def test_relation_repr():
    assert repr(Relation('>', 1)) == "<Relation '>' 1>"

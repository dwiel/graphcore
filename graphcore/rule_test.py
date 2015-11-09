import pytest

from .rule import Rule, Cardinality


def test_rule_str():
    str(Rule(lambda x: x, ['a.in'], 'a.out', 'one'))


def test_cardinality_cast_many():
    assert Cardinality.cast('many') == Cardinality.many


def test_cardinality_cast_err():
    with pytest.raises(TypeError):
        Cardinality.cast(lambda x: x)

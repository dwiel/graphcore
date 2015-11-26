import pytest

from .graphcore import Clause, OutVar


def test_str():
    assert str(Clause('a', 1))


def test_repr():
    assert repr(Clause('a', 1))


def test_clause_merge_rhs_conflict():
    with pytest.raises(ValueError):
        Clause('a', 1).merge(Clause('a', 2))


def test_clause_merge_relation():
    c = Clause('a>', 1)
    c.merge(Clause('a?', None))

    assert c.relation.operation == '>'
    assert c.relation.value == 1
    assert isinstance(c.rhs, OutVar)

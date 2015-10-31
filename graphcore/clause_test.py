from .graphcore import Clause


def test_str():
    assert str(Clause('a', 1))


def test_repr():
    assert repr(Clause('a', 1))

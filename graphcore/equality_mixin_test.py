import pytest

from .equality_mixin import EqualityMixin


class TestClass(EqualityMixin):

    def __init__(self, a, b):
        self.a = a
        self.b = b


def test_equality_mixin():
    x = TestClass(1, 2)
    y = TestClass(1, 2)

    assert x == y


def test_equality_mixing_other():
    x = TestClass(1, 2)
    y = 1

    with pytest.raises(Exception):
        assert x != y


def test_equality_mixin_with_set():
    x = TestClass(set([1]), 2)
    y = TestClass(set([1]), 2)

    assert x == y

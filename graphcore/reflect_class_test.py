import pytest

from .graphcore import Graphcore
from .reflect_class import reflect_class


class Thing(object):
    def __init__(self, x):
        self.x = x

    def foo(self):
        return self.x


class SubThing(Thing):
    def foo(self):
        return -self.x


@pytest.fixture
def gc():
    gc = Graphcore()
    reflect_class(gc, Thing)

    return gc


def test_reflect_thing(gc):
    assert len(gc.rules) == 1

    assert gc.query({
        'thing.obj': Thing(1),
        'thing.foo?': None,
    }) == [{'thing.foo': 1}]


def test_reflect_sub_thing(gc):
    assert len(gc.rules) == 1

    assert gc.query({
        'thing.obj': SubThing(1),
        'thing.foo?': None,
    }) == [{'thing.foo': -1}]

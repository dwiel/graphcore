from .graphcore import Graphcore
from .reflect_class import reflect_class


class Thing(object):
    def __init__(self, x):
        self.x = x

    def foo(self):
        return self.x


def test_reflect_thing():
    gc = Graphcore()
    reflect_class(gc, Thing)

    assert len(gc.rules) == 1

    assert gc.query({
        'thing.obj': Thing(1),
        'thing.foo?': None,
    }) == [{'thing.foo': 1}]

import unittest

from . import graphcore


class TestPath(unittest.TestCase):
    def test_subpaths(self):
        path = graphcore.Path('a.b.c.d')
        self.assertEqual(
            list(path.subpaths()), [
                graphcore.Path('c.d'),
                graphcore.Path('b.c.d'),
                graphcore.Path('a.b.c.d')
            ]
        )

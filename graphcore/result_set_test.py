import pytest

from .relation import Relation
from .result_set import ResultSet, Result, result_set_apply_transform


def test_result_init():
    assert Result().result == {}


def test_result_repr():
    assert repr(Result({'a': 1})) == "<Result {'a': 1}>"


def test_repr():
    assert repr(ResultSet()) == '<ResultSet []>'


def test_result_set_init():
    result_set = ResultSet([{'a': a} for a in range(3)])
    assert result_set == ResultSet(result_set)


def test_repr_nonbasic():
    result_set = ResultSet({})
    result_set.set('a', 1)
    assert repr(result_set) == "<ResultSet [{'a': 1}]>"


def test_result_eq():
    assert Result({'a': 1}) == Result({'a': 1})


def test_result_explode():
    assert Result({'a': 1}).explode('b', [1, 2, 3]) == [
        Result({'a': 1, 'b': b}) for b in [1, 2, 3]
    ]


def test_result_set_filter():
    result_set = ResultSet([{'a': a} for a in [1, 2, 3]])

    result_set.filter('a', Relation('>', 1))

    assert result_set.results == [{'a': 2}, {'a': 3}]


@pytest.fixture
def data():
    return [{
        'a': [{
            'b': 10,
        }, {
            'b': 20,
        }],
        'c': 100,
    }]


def test_apply_transform_single_output(data):
    ret = result_set_apply_transform(
        data, lambda c, b: c + b,
        inputs=[('c',), ('a', 'b')],
        outputs=[('a', 'd')],
        cardinality='one',
    )

    assert ret == [{
        'a': [{
            'b': 10,
            'd': 110,
        }, {
            'b': 20,
            'd': 120,
        }],
        'c': 100,
    }]


def test_apply_transform_many_outputs(data):
    ret = result_set_apply_transform(
        data, lambda c, b: (c + b, -1 * (b + c)),
        inputs=[('c',), ('a', 'b')],
        outputs=[('a', 'd'), ('a', 'e')],
        cardinality='one',
    )

    assert ret == [{
        'a': [{
            'b': 10,
            'd': 110,
            'e': -110,
        }, {
            'b': 20,
            'd': 120,
            'e': -120,
        }],
        'c': 100,
    }]


def test_apply_transform_cardinality_many(data):
    ret = result_set_apply_transform(
        data, lambda c, b: [c + b + i for i in [1, 2, 3]],
        inputs=[('c',), ('a', 'b')],
        outputs=[('a', 'd')],
        cardinality='many',
    )

    assert ret == [{
        'a': [
            {'b': 10, 'd': 111},
            {'b': 10, 'd': 112},
            {'b': 10, 'd': 113},
            {'b': 20, 'd': 121},
            {'b': 20, 'd': 122},
            {'b': 20, 'd': 123},
        ],
        'c': 100,
    }]


def test_apply_transform_cardinality_many_many_outputs(data):
    ret = result_set_apply_transform(
        data, lambda c, b: [
            (c + b + i, -1 * (c + b + i)) for i in [1, 2, 3]
        ],
        inputs=[('c',), ('a', 'b')],
        outputs=[('a', 'd'), ('a', 'e')],
        cardinality='many',
    )

    assert ret == [{
        'a': [
            {'b': 10, 'd': 111, 'e': -111},
            {'b': 10, 'd': 112, 'e': -112},
            {'b': 10, 'd': 113, 'e': -113},
            {'b': 20, 'd': 121, 'e': -121},
            {'b': 20, 'd': 122, 'e': -122},
            {'b': 20, 'd': 123, 'e': -123},
        ],
        'c': 100,
    }]

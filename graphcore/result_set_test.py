import pytest

from .relation import Relation
from .result_set import ResultSet, Result, result_set_apply_rule, shape_path


def test_result_init():
    assert Result().result == {}


def test_result_repr():
    assert repr(Result({'a': 1})) == "<Result {'a': 1}>"


def test_repr():
    assert repr(ResultSet()) == '<ResultSet []>'


def test_result_not_eq():
    # excersize __eq__ other type
    assert not (Result() == 1)


def test_result_set_eq():
    # excersize __eq__ other type
    assert not (ResultSet() == 1)


def test_result_set_init():
    result_set = ResultSet([{'a': a} for a in range(3)])
    assert result_set == ResultSet(result_set)


def test_repr_nonbasic():
    result_set = ResultSet({'a': 1})
    assert repr(result_set) == "<ResultSet [{'a': 1}]>"


def test_result_eq():
    assert Result({'a': 1}) == Result({'a': 1})


def test_result_set_filter():
    result_set = ResultSet([{'a': a} for a in [1, 2, 3]])

    result_set.filter('a', Relation('>', 1))

    assert result_set.results == [{'a': 2}, {'a': 3}]


def test_result_set_nested_filter():
    result_set = ResultSet(
        [Result({'a': ResultSet([Result({'b': b}) for b in [1, 2, 3]])})],
        [{'a': [{'b': b} for b in [1, 2, 3]]}]
    )

    print(result_set.shape_path('a.b'))
    result_set.filter('a.b', Relation('>', 1))

    assert result_set.results == [{'a': [{'b': 2}, {'b': 3}]}]


def test_shape_path():
    assert shape_path('a.b.c', [{'a': [{'b': [{}]}]}]) == ('a', 'b', 'c')


def test_shape_path_short():
    ret = shape_path('a.x.y', [{'a': [{'b': [{}]}]}])
    assert ret == ('a', 'x.y')


def test_shape_path_no_match():
    ret = shape_path('x.y.z', [{'a': [{'b': [{}]}]}])
    assert ret == ('x.y.z',)


def test_shape_path_double_dot():
    ret = shape_path('a.x.y.z', [{'a.x': [{'_': 1}]}])
    assert ret == ('a.x', 'y.z')

    assert shape_path('x.y.z', [{'a.x': [{}]}]) == ('x.y.z',)


def test_shape_paths_empty_result_set():
    assert shape_path('x', [{}])
    assert shape_path('x', [])


@pytest.fixture
def data():
    return ResultSet([Result({
        'a': ResultSet([Result({
            'b': 10,
            'd': 10,
        }), Result({
            'b': 20,
            'd': 20,
        })]),
        'c': 100,
    })], [{
        'a': [{'b': None}], 'c': None
    }])


def test_extract_json(data):
    assert data.extract_json(['a.b', 'a.d', 'c']) == [{
        'a': [{
            'b': 10,
            'd': 10,
        }, {
            'b': 20,
            'd': 20,
        }],
        'c': 100,
    }]


def test_apply_rule_single_output(data):
    ret = result_set_apply_rule(
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


def test_apply_rule_many_outputs(data):
    ret = result_set_apply_rule(
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


def test_apply_rule_cardinality_many(data):
    ret = result_set_apply_rule(
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


def test_apply_rule_cardinality_many_many_outputs(data):
    ret = result_set_apply_rule(
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

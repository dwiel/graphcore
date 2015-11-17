import pytest

from .relation import Relation
from .result_set import ResultSet, Result, result_set_apply_rule


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


def build_result_set(data):
    if isinstance(data, list):
        return ResultSet([build_result_set(e) for e in data])
    elif isinstance(data, dict):
        return Result({k: build_result_set(v) for k, v in data.items()})
    else:
        return data


def test_shape_path():
    assert build_result_set([{'a': [{'b': [{}]}]}]).shape_path('a.b.c') == (
        'a', 'b', 'c'
    )


def test_shape_path_short():
    ret = build_result_set([{'a': [{'b': [{}]}]}]).shape_path('a.x.y')
    assert ret == ('a', 'x.y')


def test_shape_path_no_match():
    ret = build_result_set([{'a': [{'b': [{}]}]}]).shape_path('x.y.z')
    assert ret == ('x.y.z',)


def test_shape_path_double_dot():
    ret = build_result_set([{'a.x': [{'_': 1}]}]).shape_path('a.x.y.z')
    assert ret == ('a.x', 'y.z')

    assert build_result_set([{'a.x': [{}]}]).shape_path('x.y.z') == ('x.y.z',)


@pytest.fixture
def data():
    return ResultSet([Result({
        'a': ResultSet([Result({
            'b': 10,
        }), Result({
            'b': 20,
        })]),
        'c': 100,
    })])


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

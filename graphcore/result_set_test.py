from .relation import Relation
from .result_set import ResultSet, Result


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

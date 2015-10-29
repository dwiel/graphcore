from .result_set import ResultSet


def test_repr():
    assert repr(ResultSet()) == '<ResultSet [{}]>'


def test_repr_nonbasic():
    result_set = ResultSet()
    result_set.set('a', 1)
    assert repr(result_set) == "<ResultSet [{'a': 1}]>"

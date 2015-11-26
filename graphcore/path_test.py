import pytest

from .path import Path


def test_subpaths():
    path = Path('a.b.c.d')
    assert list(path.subpaths()) == [
        (('a', 'b', 'c'), Path('c.d')),
        (('a', 'b'), Path('b.c.d')),
        (('a',), Path('a.b.c.d')),
    ]


def test_add():
    assert Path('a') + Path('b') == Path('a.b')


def test_radd_fail():
    with pytest.raises(TypeError):
        1 + Path('a')


def test_lt():
    assert Path('a') < 'b'


def test_repr():
    assert repr(Path('a')) == '<Path a>'


def test_init_error():
    with pytest.raises(TypeError):
        Path(1)


def test_init_list_element_type_error():
    with pytest.raises(TypeError):
        Path([1])

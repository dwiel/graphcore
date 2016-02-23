import pytest

from .reflect_module import ModuleReflector
from .graphcore import Graphcore, PathNotFound


@pytest.fixture
def gc():
    from . import test_module

    gc = Graphcore()
    ModuleReflector(gc, test_module, 'user')

    return gc


def test_simple_module_reflector(gc):
    ret = gc.query({
        'user.id': 1,
        'user.first_name?': None,
    })

    assert ret == [{'user.first_name': 'Bob1'}]


def test_verbose_arg_name(gc):
    ret = gc.query({
        'user.id': 1,
        'user.last_name?': None,
    })

    assert ret == [{'user.last_name': 'Jones1'}]


def test_verbose_function_name(gc):
    ret = gc.query({
        'user.id': 1,
        'user.age?': None,
    })

    assert ret == [{'user.age': 31}]


def test_skip_complex(gc):
    with pytest.raises(PathNotFound):
        gc.query({
            'user.id': 1,
            'user.complex?': None,
        })


def test_join(gc):
    ret = gc.query({
        'user.id': 1,
        'user.book.id?': None,
    })

    assert ret == [
        {'user.book.id': i} for i in [1, 2, 3]
    ]


def test_optional_arg(gc):
    ret = gc.query({
        'user.id': 1,
        'user.optionally_complex?': None,
    })

    assert ret == [{'user.optionally_complex': 2}]


def test_join_on_arg(gc):
    ret = gc.query({
        'user.id': 1,
        'user.book_with_user_name?': None,
    })

    assert ret == [
        {'user.book_with_user_name': 'user: Bob1; book: 1'},
        {'user.book_with_user_name': 'user: Bob1; book: 2'},
        {'user.book_with_user_name': 'user: Bob1; book: 3'},
    ]


def test_double_under(gc):
    for rule in gc.rules:
        if rule.function.__name__ == 'profile':
            assert 'user.location.city' in rule.inputs
            return

    # if we get here, there was no profile function in the rules, not good
    assert False


def test_multi_id_thing(gc):
    gc.query({
        'user.book.id': 1,
        'user.foo.id': 2,
        'user.multi_id_thing?': None,
    })


def test_type_prefix(gc):
    assert list(gc.query({
        'user.user_name': 1,
        'user.user_abc?': None,
    })[0].values())[0]

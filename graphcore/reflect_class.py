import inspect
import inflection


def make_wrapped_function(name, fn):
    """ create a 'copy' of fn as a function with variable name obj
    instead of method with self """

    def wrapped_fn(obj):
        return fn(obj)
    wrapped_fn.__name__ = name

    return wrapped_fn


def reflect_class(graphcore, cls, type_name=None):
    """ reflect a python class `cls` into graphcore with name `type_name`

    Assumes that elsewhere you define a rule which outputs 'type_name.obj'
    which will be an instance of type `cls`.  It is possible that if the
    __init__ is named properly, this step could be reflected as well
    """
    if type_name is None:
        type_name = inflection.underscore(cls.__name__)

    # register a wrapped function for all methods of cls
    for name, fn in inspect.getmembers(cls, predicate=inspect.ismethod):
        if name[:2] == '__':
            continue

        graphcore.register_rule(
            [type_name + '.obj'], type_name + '.' + name,
            function=make_wrapped_function(name, fn)
        )

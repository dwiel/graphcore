import inspect
import inflection


def make_wrapped_function(name, fn):
    """ create a 'copy' of fn as a function with variable name obj
    instead of method with self """

    def wrapped_fn(obj):
        # use getattr with the name so that if we get a subclass obj in
        # we use that subclass's implementation instead of always using the
        # base class implementation
        return getattr(obj, fn.__name__)()
    wrapped_fn.__name__ = name

    return wrapped_fn


def _is_method_or_function(x):
    """ returns True if x is a class method.

    isfunction returns true on class methods in py3 and ismethod does in py2.
    http://stackoverflow.com/questions/17019949/why-is-there-a-difference-between-inspect-ismethod-and-inspect-isfunction-from-p
    """
    return inspect.isfunction(x) or inspect.ismethod(x)


def reflect_class(graphcore, cls, type_name=None):
    """ reflect a python class `cls` into graphcore with name `type_name`

    Assumes that elsewhere you define a rule which outputs 'type_name.obj'
    which will be an instance of type `cls`.  It is possible that if the
    __init__ is named properly, this step could be reflected as well
    """
    if type_name is None:
        type_name = inflection.underscore(cls.__name__)

    # register a wrapped function for all methods of cls
    for name, fn in inspect.getmembers(cls, predicate=_is_method_or_function):
        if name[:2] == '__':
            continue

        graphcore.register_rule(
            [type_name + '.obj'], type_name + '.' + name,
            function=make_wrapped_function(name, fn)
        )

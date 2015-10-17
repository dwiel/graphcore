"""
Node := [Apply]
Apply := {'paths': Path|[Path]|{str: Path}, 'call': Call|None}
Call := {'function': function, 'args': Node, 'out': bool}

### Apply.paths options

- `Path`: return value of `Call` is stored in path

- `[Path]`: return value of the `Call` is should be an iterable.  The
    first element in the iterator will be stored in the first `Path`,
    and so on.

- `{str: Path}` return value of the `Call` should be a dictionary.
    The value of each `Path` will be set to the value in the
    dictionary at `str`

Note: only one of [Path] or {str: Path} is actually required.  The other is
optional sugar

### FAQ:

Q: why art there multiple retrun paths from a call if all calls must
only have a single return value?

A: The single return value ast works fine with the assumption that
each call only has a single return path.  This is a necessary
assumption while generating the call graph, but it doesn't need to
hold during the QueryOptimization phase.  In some cases, you may want
to replace two 'small' functions with a larger more optimal one.  This
is especially true when the functions are hitting an external resource
and you don't want a large number of round trips.
"""

from path import Path


class Node(list):
    pass


class Apply(object):
    def __init__(self, paths, call):
        if isinstance(paths, Path):
            return
        elif isinstance(paths, (list, tuple)):
            if not all(isinstance(path, Path) for path in paths):
                raise ValueError('paths should be Path or [Path]')
        else:
            raise ValueError('paths should be Path or [Path]')

        self.paths = paths

        assert isinstance(call, (Call, None))
        self.call = call


class Call(object):
    def __init__(self, function, args, out):
        self.function = function
        self.args = Node(args)
        self.out = bool(out)

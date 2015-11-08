import six


class Path(object):

    def __init__(self, init):
        if isinstance(init, six.string_types):
            self.parts = tuple(init.split('.'))
        elif isinstance(init, Path):
            self.parts = tuple(init.parts)
        elif isinstance(init, (tuple, list)):
            self.parts = tuple(init)
        else:
            raise TypeError()

    @property
    def relative(self):
        return Path(self.parts[-2:])

    @property
    def property(self):
        return self.parts[-1]

    def subpaths(self):
        for i in range(-2, -len(self.parts) - 1, -1):
            yield self.parts[:i], Path(self.parts[i:])

    def __repr__(self):
        return '<Path {str}>'.format(str=str(self))

    def __str__(self):
        return '.'.join(self.parts)

    def __hash__(self):
        return hash(self.parts)

    def __eq__(self, other):
        if not isinstance(other, Path):
            other = Path(other)
        return self.parts == other.parts

    def __lt__(self, other):
        if not isinstance(other, Path):
            other = Path(other)
        return self.parts < other.parts

    def __getitem__(self, index):
        return self.parts[index]

    def __len__(self):
        return len(self.parts)

    def __add__(self, other):
        if isinstance(other, tuple):
            return Path(self.parts + other)
        else:
            return Path(self.parts + other.parts)

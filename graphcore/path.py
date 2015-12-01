import six


class Path(object):

    def __init__(self, init):
        if isinstance(init, six.string_types):
            self.parts = tuple(init.split('.'))
        elif isinstance(init, Path):
            self.parts = tuple(init.parts)
        elif isinstance(init, (tuple, list)):
            all_string_elements = all(
                isinstance(e, six.string_types)
                for e in init
            )
            if not all_string_elements:
                raise TypeError((
                    'if init is a list or tupele, its elements should'
                    'all be type string.  Instead, it'
                    'had types: {} and values {}'
                ).format(map(str, map(type, init)), init))

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
        """ return all possible prefix/subpath paris.

        path = Path('a.b.c.d')
        path.subpaths() == [
            (('a', 'b', 'c'), Path('c.d'))
            (('a', 'b'), Path('b.c.d'))
            (('a'), Path('a.b.c.d'))
        ]
        """
        for i in range(-2, -len(self.parts) - 1, -1):
            yield Path(self.parts[:i+1]), Path(self.parts[i:])

    def subpath(self, root):
        return Path(str(self)[len(root)+1:])

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

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, Path):
            other = Path(other)
        return self.parts < other.parts

    def __getitem__(self, index):
        return Path(self.parts[index])

    def __len__(self):
        return len(self.parts)

    def __radd__(self, other):
        if isinstance(other, six.string_types):
            return Path(Path(other).parts + self.parts)
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, tuple):
            return Path(self.parts + other)
        else:
            return Path(self.parts + other.parts)

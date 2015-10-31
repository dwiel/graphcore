def freeze(o):
    if isinstance(o, list):
        return tuple(freeze(e) for e in o)
    elif isinstance(o, set):
        return frozenset(freeze(e) for e in o)
    elif isinstance(o, dict):
        return tuple((freeze(k), freeze(v)) for k, v in sorted(o.items()))
    else:
        return o


class EqualityMixin(object):

    def __eq__(self, other):
        """Override the default Equals behavior"""
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __ne__(self, other):
        """Define a non-equality test"""
        return not self.__eq__(other)


class HashMixin(object):

    def __hash__(self):
        """Override the default hash behavior (that returns the id or
        the object)"""
        # TODO: get rid of this ...
        return hash(freeze(self.__dict__))

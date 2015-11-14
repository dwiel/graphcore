import operator


OPERATORS = {
    '>': operator.gt,
    '<': operator.lt,
    '>=': operator.ge,
    '<=': operator.le,
    '!=': operator.ne,
    '|=': operator.contains,
}


class Relation(object):

    def __init__(self, operation, value):
        self.operation = operation
        self.value = value

        self._build_function()

    def _build_function(self):
        op = OPERATORS[self.operation]

        if op == operator.contains:
            # contains operator is backwards compared to the rest of the
            # operators
            self._function = lambda x: op(self.value, x)
        else:
            self._function = lambda x: op(x, self.value)

    def __eq__(self, other):
        """Override the default Equals behavior"""
        if isinstance(other, self.__class__):
            return self.operation == other.operation and \
                self.value == other.value
        raise TypeError

    def __ne__(self, other):
        """Define a non-equality test"""
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.operation, self.value))

    def __call__(self, other):
        return self._function(other)

    def __repr__(self):
        return "<Relation '{operation}' {value}>".format(**self.__dict__)

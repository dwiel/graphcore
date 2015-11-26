import operator


OPERATORS = {
    '>': operator.gt,
    '<': operator.lt,
    '>=': operator.ge,
    '<=': operator.le,
    '==': operator.eq,
    '!=': operator.ne,
    '|=': lambda x, y: operator.contains(y, x),
}


class Relation(object):

    def __init__(self, operation, value):
        self.operation = operation
        self.value = value

        self._build_function()

    def _build_function(self):
        if isinstance(self.operation, tuple):
            ops = [OPERATORS[operation] for operation in self.operation]

            self._function = lambda x: all(
                op(x, value) for op, value in zip(ops, self.value)
            )
        else:
            op = OPERATORS[self.operation]

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

    @staticmethod
    def _tuplify(relation):
        if isinstance(relation.operation, tuple):
            return relation.operation, relation.value
        else:
            return (relation.operation,), (relation.value,)

    def merge(self, other):
        self_operation, self_value = Relation._tuplify(self)
        other_operation, other_value = Relation._tuplify(other)

        return Relation(
            self_operation + other_operation,
            self_value + other_value,
        )

    def __repr__(self):
        return "<Relation '{operation}' {value}>".format(**self.__dict__)

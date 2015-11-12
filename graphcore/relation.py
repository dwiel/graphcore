from .equality_mixin import EqualityMixin, HashMixin


class Relation(HashMixin, EqualityMixin):

    def __init__(self, operation, value):
        self.operation = operation
        self.value = value

    def __repr__(self):
        return "<Relation '{operation}' {value}>".format(**self.__dict__)

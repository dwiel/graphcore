import six
from enum import Enum

from .path import Path
from .equality_mixin import HashMixin, EqualityMixin


class Cardinality(Enum):
    one, many = 1, 2

    @staticmethod
    def cast(init):
        if isinstance(init, (int, Cardinality)):
            return Cardinality(init)
        elif isinstance(init, six.string_types):
            return Cardinality[init]
        else:
            raise TypeError(
                'must be int, str or Cardinality, got {}'.format(
                    type(init).__name__
                )
            )


class Rule(HashMixin, EqualityMixin):

    def __init__(self, function, inputs, outputs, cardinality):
        self.function = function
        self.inputs = [Path(input) for input in inputs]
        if isinstance(outputs, (Path, six.string_types)):
            self.outputs = [outputs]
        else:
            self.outputs = [Path(output) for output in outputs]
        self.cardinality = Cardinality.cast(cardinality)

    def __repr__(self):
        string = '<Rule {outputs} = {function_name}({inputs}) {cardinality}'
        return string.format(
            outputs=', '.join(map(str, self.outputs)),
            function_name=self.function.__name__,
            inputs=', '.join(map(str, self.inputs)),
            cardinality=self.cardinality,
        )

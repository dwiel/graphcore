from six.moves import zip

from .equality_mixin import EqualityMixin
from .path import Path


class Result(EqualityMixin):

    def __init__(self, result=None):
        if isinstance(result, Result):
            self.result = result.result.copy()
        elif isinstance(result, dict):
            self.result = {}
            for k, v in result.items():
                self.set(k, v)
        else:
            self.result = {}

    def set(self, path, value):
        self.result[str(path)] = value

    def get(self, path):
        return self.result[str(path)]

    def explode(self, path, values):
        new_results = [
            Result(self)
            for _ in range(len(values))
        ]

        for result, value in zip(new_results, values):
            result.set(path, value)

        return new_results

    def to_json(self):
        return self.result

    def extract_json(self, paths):
        return {
            str(path): self.get(path) for path in paths
        }

    def __repr__(self):
        return '<Result {result}>'.format(result=repr(self.result))


class ResultSet(EqualityMixin):
    """ The ResultSet holds the state of the query as it is executed. """

    def __init__(self, init=None):
        # TODO handle more complex result set toplogies
        if isinstance(init, ResultSet):
            self.results = init.results
        elif isinstance(init, dict):
            self.results = [Result(init)]
        elif isinstance(init, list):
            self.results = init
        else:
            self.results = []

    def set(self, path, value):
        for result in self.results:
            result.set(path, value)

    def to_json(self):
        return [
            result.to_json() for result in self.results
        ]

    def extract_json(self, paths):
        return [
            result.extract_json(paths) for result in self.results
        ]

    def filter(self, path, relation):
        self.results = [
            result for result in self.results
            if relation(result.get(path))
        ]

    def extend(self, results):
        self.results.extend(results)

    def __repr__(self):
        return '<ResultSet {str}>'.format(str=str(self))

    def __str__(self):
        return str(self.to_json())

    def __iter__(self):
        return iter(self.results)


def _subpaths(path):
    for i in range(len(path.parts)):
        yield Path(path.parts[:i]), Path(path.parts[i:])


def shape_path(data, path):
    """ return a tuple of subpaths which add together to path, but are split
    in the same way as the data result_set.

    shape_path([{'a.x': [{}]}], 'a.x.y.z') == ('a.x', 'y.z')
    shape_path([{'a.x': [{}]}], 'x.y.z') == ('x.y.z',)
    """
    if isinstance(data, list):
        return shape_path(data[0], path)

    for prefix, subpath in _subpaths(Path(path)):
        prefix = Path(prefix)
        sub_data = data.get(str(prefix))
        if sub_data:
            return (prefix,) + shape_path(sub_data, subpath)

    return (path,)


def next_sub_path(inputs):
    # NOTE: only handles inputs along one lineage in the tree. no sisters
    # or cousins allowed
    sub_path = set([input[0] for input in inputs])
    if len(sub_path) > 1:
        raise ValueError('no sisters!')
    elif len(sub_path) == 1:
        return sub_path.pop()


def result_set_apply_transform(data, fn, inputs, outputs, cardinality,
                               scope={}):
    new_data = []
    for result in data:
        new_data.extend(
            result_apply_transform(
                result, fn, inputs, outputs, cardinality, scope
            )
        )
    return new_data


def apply_function(data, fn, outputs, cardinality, scope):
    ret = fn(**scope)

    if cardinality == 'one':
        if len(outputs) == 1:
            values = [ret]
        else:
            values = ret

        for output, value in zip(outputs, values):
            data[output[0]] = value

        return [data]
    elif cardinality == 'many':
        if len(outputs) == 1:
            values_set = [(value,) for value in ret]
        else:
            values_set = ret

        new_datas = []
        for values in values_set:
            new_data = data.copy()
            for output, value in zip(outputs, values):
                new_data[output[0]] = value
            new_datas.append(new_data)

        return new_datas
    else:
        raise ValueError('cardinality must be one or many')


def result_apply_transform(data, fn, inputs, outputs, cardinality, scope={}):
    # collect inputs at this level
    for input in inputs:
        if len(input) == 1:
            scope[input[0]] = data[input[0]]

    # outputs must all be at the same depth and must not depend on inputs which
    # are deeper
    if len(outputs[0]) == 1:
        return apply_function(data, fn, outputs, cardinality, scope)
    else:
        # recur down to the next level of the data
        inputs = [input for input in inputs if len(input) > 1]

        sub_path = next_sub_path(inputs)

        # remove left most part from input and output
        new_inputs = [input[1:] for input in inputs]
        new_outputs = [output[1:] for output in outputs]

        # a copy may not be strictly necessary ...
        data[sub_path] = result_set_apply_transform(
            data[sub_path], fn, new_inputs, new_outputs, cardinality, scope
        )

        # return a list boxing the data so the return value is the same as
        # cardinality many
        return [data]

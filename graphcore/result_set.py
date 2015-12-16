import six
from six.moves import zip
from collections import defaultdict

from .equality_mixin import EqualityMixin
from .path import Path
from .rule import Cardinality


def shape_path(path, query_shape):
    """ return a tuple of subpaths which add together to path, but are split
    in the same way as the data result_set.

    shape_path([{'a.x': [{}]}], 'a.x.y.z') == ('a.x', 'y.z')
    shape_path([{'a.x': [{}]}], 'x.y.z') == ('x.y.z',)
    """
    if isinstance(path, tuple):
        return path

    if isinstance(query_shape, (list, tuple)):
        if len(query_shape) == 0:
            return (path,)
        else:
            return shape_path(path, query_shape[0])
    elif isinstance(query_shape, dict):
        for prefix, subpath in _subpaths(path):
            sub_data = query_shape.get(str(prefix))
            if sub_data:
                return (prefix,) + shape_path(subpath, sub_data)

        return (path,)
    else:
        return (path,)


def _subpaths(path):
    path = Path(path)

    for i in range(len(path.parts)):
        yield Path(path.parts[:i]), Path(path.parts[i:])


class Result(EqualityMixin):

    def __init__(self, result=None):
        if isinstance(result, Result):
            self.result = result.result.copy()
        elif isinstance(result, dict):
            # set each individually to ensure keys are mapped to strings
            self.result = {}
            for k, v in result.items():
                self[k] = v
        else:
            self.result = {}

    def get(self, path, default=None):
        return self.result.get(str(path), default)

    def to_json(self):
        return self.result

    def extract_json(self, paths):
        """ return the json representing paths.

        paths must already shaped like the ResultSet"""

        # group paths by their first part.  If there are multiple
        # paths with the same sub_path, we only need to make one
        # recursive call
        sub_paths = defaultdict(list)
        for path in paths:
            sub_paths[str(path[0])].append(path[1:])

        ret = {}
        for sub_path, paths in sub_paths.items():
            value = self.get(sub_path)

            if isinstance(value, ResultSet):
                ret[sub_path] = value.extract_json(paths)
            else:
                assert paths == [()]
                ret[sub_path] = value

        return ret

    def deepcopy(self):
        new_result = {}
        for k, v in self.result.items():
            if isinstance(v, ResultSet):
                v = v.deepcopy()

            new_result[k] = v

        return Result(new_result)

    def __getitem__(self, k):
        return self.result[str(k)]

    def __setitem__(self, k, v):
        self.result[str(k)] = v

    def __repr__(self):
        return '<Result {result}>'.format(result=repr(self.result))

    def __eq__(self, other):
        """Override the default Equals behavior"""
        if isinstance(other, Result):
            return self.result == other.result
        elif isinstance(other, dict):
            return self.result == other
        return NotImplemented


class ResultSet(EqualityMixin):
    """ The ResultSet holds the state of the query as it is executed. """

    def __init__(self, init=None, query_shape=None):
        """
        query_shape should be a json object with the same shape as the desired
        ResultSet.  for example:

            [{'x': [{'y': None}], 'z': None}]

        in the case of a dictionary, the value doesn't matter

        NOTE: requiring a query_shape here doesn't feel clean, but as it
        stands, I'm not sure where else this transformation should go.
        """

        if isinstance(init, ResultSet):
            self.results = init.results
        elif isinstance(init, dict):
            self.results = [Result(init)]
        elif isinstance(init, list):
            self.results = init
        else:
            self.results = []

        if query_shape is None:
            self.query_shape = [{}]
        else:
            self.query_shape = query_shape

    def to_json(self):
        return [
            result.to_json() for result in self.results
        ]

    def extract_json(self, paths):
        paths = self.shape_paths(paths)
        return [
            result.extract_json(paths) for result in self.results
        ]

    def filter(self, path, relation):
        if isinstance(path, (six.string_types, Path)):
            path = self.shape_path(path)

        # if this is the leaf, just filter on this result set
        if len(path) == 1:
            self.results = [
                result for result in self.results
                if relation(result[path[0]])
            ]
        # if this is a nested filter, recur down into the next level
        else:
            for result in self.results:
                result[path[0]].filter(
                    path[1:], relation
                )

    def limit(self, limit):
        """ naive limit for now.  won't limit sub results """
        self.results = self.results[:limit]

    def deepcopy(self):
        new_results = []
        for result in self.results:
            if isinstance(result, Result):
                result = result.deepcopy()

            new_results.append(result)

        return ResultSet(new_results)

    def __repr__(self):
        return '<ResultSet {str}>'.format(str=str(self))

    def __str__(self):
        return str(self.to_json())

    def __iter__(self):
        return iter(self.results)

    def __eq__(self, other):
        """Override the default Equals behavior"""
        if isinstance(other, ResultSet):
            return self.results == other.results
        elif isinstance(other, list):
            return self.results == other
        return NotImplemented

    def shape_paths(self, paths):
        return [self.shape_path(path) for path in paths]

    def shape_path(self, path):
        return shape_path(path, self.query_shape)


def result_set_apply_rule(data, fn, inputs, outputs, cardinality,
                          scope=None):
    if scope is None:
        scope = {}

    new_data = []
    for result in data:
        new_data.extend(
            result_apply_rule(
                result, fn, inputs, outputs, cardinality, scope
            )
        )

    # odd to be concerned with preserving the query_shape here, but
    # this value needs to be present in the new result_set
    return ResultSet(new_data, data.query_shape)


def result_apply_rule(data, fn, inputs, outputs, cardinality, scope):
    # collect inputs at this level
    for input in inputs:
        if len(input) == 1:
            # TODO: dont require casting here
            scope[Path(input[0]).relative.property] = data[input[0]]

    # outputs must all be at the same depth and must not depend on inputs which
    # are deeper
    if len(outputs[0]) == 1:
        return apply_rule(data, fn, outputs, cardinality, scope)
    else:
        # recur down to the next level of the data
        inputs = [input for input in inputs if len(input) > 1]

        sub_path = next_sub_path(inputs + outputs)

        # remove left most part from input and output
        new_inputs = [input[1:] for input in inputs]
        new_outputs = [output[1:] for output in outputs]

        # a copy may not be strictly necessary ...
        data[sub_path] = result_set_apply_rule(
            data.get(sub_path, ResultSet([Result()])),
            fn, new_inputs, new_outputs, cardinality, scope
        )

        # return a list boxing the data so the return value is the same as
        # cardinality many
        return ResultSet([data])


def next_sub_path(inputs):
    # NOTE: only handles inputs along one lineage in the tree. no sisters
    # or cousins allowed
    sub_path = set([input[0] for input in inputs])
    if len(sub_path) > 1:
        raise ValueError('no sisters!')
    elif len(sub_path) == 1:
        return sub_path.pop()


def apply_rule(data, fn, outputs, cardinality, scope):
    cardinality = Cardinality.cast(cardinality)

    ret = fn(**scope)

    if cardinality == Cardinality.one:
        if len(outputs) == 1:
            values = [ret]
        else:
            values = ret

        for output, value in zip(outputs, values):
            data[output[0]] = value

        return ResultSet([data])
    elif cardinality == Cardinality.many:
        if len(outputs) == 1:
            values_set = [(value,) for value in ret]
        else:
            values_set = ret

        new_datas = []
        for values in values_set:
            # deepcopy: recursively copy Result and ResultSet objects only
            new_data = data.deepcopy()
            for output, value in zip(outputs, values):
                new_data[output[0]] = value
            new_datas.append(new_data)

        return ResultSet(new_datas)
    else:
        raise ValueError('cardinality must be one or many')

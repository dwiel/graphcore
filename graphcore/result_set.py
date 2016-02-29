import six
from six.moves import zip
import sys
import traceback
from collections import defaultdict

from .equality_mixin import EqualityMixin
from .path import Path
from .rule import Cardinality


def mapper(fn, data):
    # override this if you want to implement a different distributed
    # execution model
    if len(data) > 20:
        from plotwatt.pwcloud import pwcloud

        return pwcloud.chunk_imap(fn, data, chunk_size=len(data)/8)
    else:
        return map(fn, data)


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


def input_mapping(keys, parts=1):
    """ given a list of paths, return a dictionary of {path: shortened_path}
    where shortened_path can be used as the argument name when calling a
    function with `paths` inputs.

    The algorithm is to use only the right most part of the path if it is
    unique.  If not, it uses the right 2 most parts seperated by an underscore.
    Otherwise, 3, etc.
    """

    d = defaultdict(list)
    for k in keys:
        d[str(Path(k)[-parts:]).replace('.', '_')].append(k)

    mapping = {}
    for short, _keys in d.items():
        if len(_keys) == 1:
            mapping[_keys[0]] = short
        else:
            mapping.update(input_mapping(_keys, parts+1))

    return mapping


class RuleApplicationException(Exception):
    def __init__(self, fn, scope, exception, traceback):
        super(RuleApplicationException, self).__init__(
            fn, scope, exception, traceback
        )

        self.fn = fn
        self.scope = scope
        self.exception = exception
        self.traceback = traceback

    def __str__(self):
        return (
            'Exception {e} raised while evaluating {fn} with '
            'params {scope}.  \n{traceback}\n\nquery_plan:\n{query_plan}'
            '\n\nin node:\n{node}'
        ).format(
            e=self.exception,
            fn=self.fn.__name__,
            scope=repr(self.scope),
            traceback=''.join(self.traceback),
            query_plan='\n'.join(map(str, self.query_plan.nodes)),
            node=self.node
        )


class NoResult(Exception):
    """ rules should raise this exception if there is no result given the
    inputs provided.  This exception will remove the Result which was passed
    in as if there were a filter applied to the ResultSet """
    pass


class Result(EqualityMixin):

    def __init__(self, result=None, mapper=map):
        self.mapper = mapper
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

        return Result(new_result, mapper=self.mapper)

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

    def apply_rule(self, fn, inputs, outputs, cardinality, scope):
        # collect inputs at this level
        for input in inputs:
            if len(input) == 1:
                # TODO: dont require casting here
                # scope[Path(input[0]).relative.property] = self[input[0]]
                scope[str(input[0])] = self[input[0]]

        # outputs must all be at the same depth and must not depend on inputs
        # which are deeper
        if len(outputs[0]) == 1:
            return self._apply_rule(fn, outputs, cardinality, scope)
        else:
            # recur down to the next level of the data
            inputs = [input for input in inputs if len(input) > 1]

            sub_path = next_sub_path(inputs + outputs)

            # remove left most part from input and output
            new_inputs = [input[1:] for input in inputs]
            new_outputs = [output[1:] for output in outputs]

            default = ResultSet(
                [Result(mapper=self.mapper)], mapper=self.mapper
            )
            existing_result_set = self.get(sub_path, default)
            self[sub_path] = existing_result_set.apply_rule(
                fn, new_inputs, new_outputs, cardinality, scope
            )

            # return a list boxing the data so the return value is the same as
            # cardinality many
            return ResultSet([self], mapper=self.mapper)

    def _simplify_scope(self, scope):
        mapping = input_mapping(scope.keys())
        return {mapping[k]: v for k, v in scope.items()}

    def _apply_rule(self, fn, outputs, cardinality, scope):
        """ this one finally calls `fn` """
        cardinality = Cardinality.cast(cardinality)

        try:
            ret = fn(**self._simplify_scope(scope))
        except NoResult:
            # this scope has no value for these outputs, filter this result
            # from the ResultSet
            return ResultSet([], mapper=self.mapper)
        except (ValueError, TypeError, KeyError, ArithmeticError) as e:
            raise RuleApplicationException(
                fn, scope, e, traceback.format_exception(*sys.exc_info())
            )

        if cardinality == Cardinality.one:
            if len(outputs) == 1:
                values = [ret]
            else:
                values = ret

            for output, value in zip(outputs, values):
                self[output[0]] = value

            return ResultSet([self], mapper=self.mapper)
        elif cardinality == Cardinality.many:
            if len(outputs) == 1:
                values_set = [(value,) for value in ret]
            else:
                values_set = ret

            new_datas = []
            for values in values_set:
                # deepcopy: recursively copy Result and ResultSet objects only
                new_data = self.deepcopy()
                for output, value in zip(outputs, values):
                    new_data[output[0]] = value
                new_datas.append(new_data)

            return ResultSet(new_datas, mapper=self.mapper)
        else:
            raise ValueError('cardinality must be one or many')


class ResultSet(EqualityMixin):
    """ The ResultSet holds the state of the query as it is executed. """

    def __init__(self, init=None, query_shape=None, mapper=map):
        """
        query_shape should be a json object with the same shape as the desired
        ResultSet.  for example:

            [{'x': [{'y': None}], 'z': None}]

        in the case of a dictionary, the value doesn't matter

        NOTE: requiring a query_shape here doesn't feel clean, but as it
        stands, I'm not sure where else this transformation should go.
        """

        self.mapper = mapper

        if isinstance(init, ResultSet):
            self.results = init.results
        elif isinstance(init, dict):
            self.results = [Result(init, mapper=self.mapper)]
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

        return ResultSet(new_results, mapper=self.mapper)

    def __repr__(self):
        return '<ResultSet {str}>'.format(str=str(self))

    def __str__(self):
        return str(self.to_json())

    def __iter__(self):
        return iter(self.results)

    def __len__(self):
        return len(self.results)

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

    def apply_rule(self, fn, inputs, outputs, cardinality,
                   scope=None):
        if scope is None:
            scope = {}

        # only use custom mapper when were actually doing the map over data. In
        # some applications of this function we're recursively navigating the
        # tree of ResultSets and that task shouldnt be distributed
        if len(outputs[0]) == 1:
            mapper = self.mapper
        else:
            mapper = map

        def wrapped_fn(result):
            return result.apply_rule(
                fn, inputs, outputs, cardinality, scope
            )

        wrapped_fn.__name__ = fn.__name__

        # map across self
        ret = mapper(wrapped_fn, self)

        # merge results
        new_result_set = []
        for row in ret:
            new_result_set.extend(row)

        # odd to be concerned with preserving the query_shape here, but
        # this value needs to be present in the new result_set
        return ResultSet(new_result_set, self.query_shape, mapper=self.mapper)


def next_sub_path(paths):
    # NOTE: only handles inputs along one lineage in the tree. no sisters
    # or cousins allowed
    sub_path = set([path[0] for path in paths])
    if len(sub_path) > 1:
        raise ValueError(
            'currently dont allow inputs/outputs from multiple '
            'levels, got: {}'.format(
                ', '.join(map(str, paths))
            )
        )
    elif len(sub_path) == 1:
        return sub_path.pop()

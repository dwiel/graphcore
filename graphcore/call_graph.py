"""
Node := [Apply|Path]
Apply := {'paths': Path|[Path]|{str: Path}, 'call': Call|None}
Call := {'function': function, 'args': Node, 'out': bool}

### Apply.paths options

- `Path`: return value of `Call` is stored in path

- `[Path]`: return value of the `Call` is should be an iterable.  The
    first element in the iterator will be stored in the first `Path`,
    and so on.

- `{str: Path}` return value of the `Call` should be a dictionary.
    The value of each `Path` will be set to the value in the
    dictionary at `str`

Note: only one of [Path] or {str: Path} is actually required.  The other is
optional sugar

### FAQ:

Q: why art there multiple retrun paths from a call if all calls must
only have a single return value?

A: The single return value ast works fine with the assumption that
each call only has a single return path.  This is a necessary
assumption while generating the call graph, but it doesn't need to
hold during the QueryOptimization phase.  In some cases, you may want
to replace two 'small' functions with a larger more optimal one.  This
is especially true when the functions are hitting an external resource
and you don't want a large number of round trips.

Node: {
    'incoming_edges': {Edge},
    'outgoing_edges': {Edge},
    'function': function,
    'cardinality': One|Many,
    'realtions': Relation,
}

Relation: {
    'operation': '<'|'>'|...,
    'value': Any,
}

# This is really a glorified Path.
Edge: {
    'path': Path,
    'getters': {Node},
    'setter': Node|None,
}

the order of the in_paths is irrelevant (set)
the order of the out paths, coresponds to the order of the returned iterable.
TODO: out_paths: {key: (Path, Node), ...}

"""

from .path import Path
from .rule import Cardinality
from .relation import Relation


class Node(object):

    def __init__(self, call_graph, incoming_paths, outgoing_paths, function,
                 cardinality, relations=None):
        self.call_graph = call_graph
        self.incoming_paths = tuple(sorted(map(Path, incoming_paths)))
        self.outgoing_paths = tuple(map(Path, outgoing_paths))
        self.function = function
        self.cardinality = Cardinality.cast(cardinality)
        if relations is None:
            self.relations = tuple([None for _ in outgoing_paths])
        else:
            assert len(relations) == len(outgoing_paths)
            self.relations = tuple(relations)

        # this is useful for QueryPlanner to iterate over CallGraph
        self._visited = False

    def incoming_edges(self):
        return [self.call_graph.edge(path) for path in self.incoming_paths]

    def incoming_nodes(self):
        return [edge.setter for edge in self.incoming_edges()
                if edge.setter is not None]

    def input_path_by_property(self, property):
        for path in self.incoming_paths:
            if path.property == property:
                return path

    def __hash__(self):
        return hash(self.__key())

    def __key(self):
        return (
            self.incoming_paths,
            self.outgoing_paths,
            self.function,
            self.cardinality,
            self.relations
        )

    def __eq__(self, other):
        return self.__key() == other.__key()

    def explain(self):
        string = ''
        string += '{outgoing_paths} = {name}({incoming_paths}) '

        if self.cardinality is not Cardinality.one:
            string += '{cardinality} '

        for relation, outgoing_path in zip(
            self.relations, self.outgoing_paths
        ):
            if relation is None:
                continue

            for op, value in zip(*Relation._tuplify(relation)):
                string += '\n    {outgoing_path} {op} {value}'.format(
                    outgoing_path=outgoing_path,
                    op=op,
                    value=value
                )

        return string.format(
            outgoing_paths=', '.join(map(str, self.outgoing_paths)),
            incoming_paths=', '.join(map(str, self.incoming_paths)),
            name=self.name,
            cardinality=self.cardinality,
            realtions=self.relations
        )

    def __repr__(self):
        return '<Node {}>'.format(self.explain())

    @property
    def name(self):
        if hasattr(self.function, '__name__'):
            return self.function.__name__
        else:
            return str(self.function)


class Edge(object):
    """
    out: bool - True if is this path used in the final ResultSet, False
        if it is an intermediate value
    """

    def __init__(self, path, getters, setter, out):
        self.path = path
        self.getters = set(getters)
        self.setter = setter
        # TODO: rename out
        self.out = out

    def __hash__(self):
        return hash(self.path)

    def __repr__(self):
        return '<Edge {path}>'.format(**self.__dict__)

    def __eq__(self, other):
        return self.path == other.path

    def __ne__(self, other):
        return not self == other


class CallGraph(object):
    # TODO: Edge objects seem a bit heavy-handed, perhaps the CallGraph
    # object should just provide helpers to get at edge.incoming_nodes, etc
    # instead of trying to keep them up to date on those objects all the time

    def __init__(self):
        self.nodes = []
        self.edges = {}

    def add_node(self, incoming_paths, outgoing_paths, function, cardinality,
                 relations=None):
        # build a node
        node = Node(
            self, incoming_paths, outgoing_paths, function, cardinality,
            relations
        )
        self.nodes.append(node)

        # add the node to the edges
        for outgoing_path in outgoing_paths:
            self.edge(outgoing_path).setter = node

        for incoming_path in incoming_paths:
            self.edge(incoming_path).getters.add(node)

        return node

    def remove_node(self, node):
        self.nodes.remove(node)

        for path in node.incoming_paths:
            self.edge(path).getters.remove(node)

        for path in node.outgoing_paths:
            self.edge(path).setter = None

    def edge(self, path):
        path = Path(path)

        if path in self.edges:
            return self.edges[path]
        else:
            return self.edges.setdefault(path, Edge(path, [], None, False))

    def output_paths(self):
        return [edge.path for edge in self.edges.values() if edge.out]

    def nodes_depending_on_path(self, path):
        """ return a list of nodes which depend on path.

        This is helpful for debugging when a match isn't found and you
        want to know where a clase came from.
        """

        edge = self.edges.get(path)
        if edge is None:
            return []
        else:
            return edge.getters

    def __repr__(self):
        return '<CallGraph nodes=[{nodes}\n] edges={{{edges}\n}}>'.format(
            nodes=''.join('\n  ' + str(node) for node in self.nodes),
            edges=''.join(
                '\n  ' + str(k) + ': ' + str(v)
                for k, v in self.edges.items()
            ),
        )
    __str__ = __repr__

    def explain(self):
        return '\n'.join(node.explain() for node in self.nodes)

    def __key(self):
        return (
            self.nodes,
            self.edges,
        )

    def __eq__(self, other):
        return self.__key() == other.__key()

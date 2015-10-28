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
    'outgoing_edges': Edge|[Edge]|{str: Edge},
    'rule': Rule,
    'filter': Filter
}

Filter: {
    'operation': '<'|'>'|...,
    'value': Any,
}

# This is really a glorified Path.
Edge: {
    'path': Path,
    'getters': {Node},
    'setter': Node,
}

the order of the in_paths is irrelevant (set)
the order of the out paths, coresponds to the order of the returned iterable.
TODO: out_paths: {key: (Path, Node), ...}

"""

from .path import Path
from .equality_mixin import EqualityMixin


class Node(EqualityMixin):
    def __init__(self, incoming_edges, outgoing_edges, rule, filter=None):
        self.incoming_edges = list(incoming_edges)
        self.outgoing_edges = list(outgoing_edges)
        self.rule = rule
        self.filter = filter

        # this is useful for QueryPlanner to iterate over CallGraph
        self._visited = False

    def incoming_nodes(self):
        return [edge.setter for edge in self.incoming_edges
                if edge.setter is not None]

    def incoming_paths(self):
        return [edge.path for edge in self.incoming_edges]

    def outgoing_paths(self):
        return [edge.path for edge in self.outgoing_edges]

    def __hash__(self):
        """ a custom hash is required because the data structure is recursive.

        edges are expressed in the hash as their paths only.  A node will be
        considered equal if it has the same rule, filter and paths it is
        connected to regardless of what else is happening in the CallGraph
        """

        return hash((
            tuple(edge.path for edge in self.incoming_edges),
            tuple(edge.path for edge in self.outgoing_edges),
            self.rule,
            self.filter
        ))

    def _shallow(self):
        return (
            tuple(edge.path for edge in self.incoming_edges),
            tuple(edge.path for edge in self.outgoing_edges),
            self.rule,
            self.filter
        )

    def __eq__(self, other):
        return self._shallow() == other._shallow()

    def __repr__(self):
        string='<Node '
        string+='{outgoing_paths} = {name}({incoming_paths}) '
        string+='filter={filter}'
        string+='>'
        return (string.format(
                outgoing_paths=', '.join(
                    str(edge.path) for edge in self.outgoing_edges
                ),
                name=self.name,
                incoming_paths=', '.join(
                    str(edge.path) for edge in self.incoming_edges
                ),
                filter=self.filter
            )
        )

    @property
    def name(self):
        return self.rule.function.__name__

class Filter(EqualityMixin):
    def __init__(self, operation, value):
        self.operation = operation
        self.value = value

class Edge(object):
    def __init__(self, path, getters, setter, out):
        self.path = path
        self.getters = set(getters)
        self.setter = setter
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

    def add_node(self, incoming_paths, outgoing_paths, rule, filter=None):
        # lookup or create edges for all of the paths
        incoming_edges = {
            self.edge(path) for path in incoming_paths
        }

        # grab outgoing_edge and set it's out if this is an output computation
        outgoing_edges = {
            self.edge(path) for path in outgoing_paths
        }

        # build a node
        node = Node(incoming_edges, outgoing_edges, rule, filter)
        self.nodes.append(node)

        # add the node to the edges
        for outgoing_edge in outgoing_edges:
            outgoing_edge.setter = node

        for edge in incoming_edges:
            edge.getters.add(node)

    def remove_node(self, node):
        self.nodes.remove(node)

        for edge in node.incoming_edges:
            edge.getters.remove(node)

        for edge in node.outgoing_edges:
            edge.setter = None

    def edge(self, path):
        path = Path(path)

        if path in self.edges:
            return self.edges[path]
        else:
            return self.edges.setdefault(path, Edge(path, [], None, False))

    def output_paths(self):
        return [edge.path for edge in self.edges.values() if edge.out]

    def __repr__(self):
        return '<CallGraph nodes=[{nodes}\n] edges={{{edges}\n}}>'.format(
                nodes=''.join('\n  '+str(node) for node in self.nodes),
                edges=''.join(
                    '\n  '+str(k)+': '+str(v)
                    for k, v in self.edges.items()
                ),
        )
    __str__ = __repr__


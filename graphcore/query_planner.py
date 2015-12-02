"""
This QueryPlanner will be very nieve.  Its role is to convert a CallGraph into
a QueryPlan
"""

from .query_plan import QueryPlan
from .result_set import ResultSet, Result


class CallGraphIterator(object):
    # TODO: this iterator could only check nodes for grounded ness if
    # one of its incoming_nodes changed groundedness

    def __init__(self, call_graph):
        self._call_graph = call_graph

        # contains the python object id of nodes which have been grounded
        self._grounded = set()

    def _is_grounded(self, node):
        """ Retursn true if node is in _grounded or if all incoming nodes
        are """

        if id(node) in self._grounded:
            return True

        nodes = node.incoming_nodes()
        if len(nodes) == 0:
            return True
        else:
            return all(id(n) in self._grounded for n in nodes)

    def _ground(self, node):
        """ Add node to the _grounded set """
        self._grounded.add(id(node))

    def __iter__(self):
        # local copy of set that we can modify
        nodes = list(self._call_graph.nodes)

        # if a node is grounded, add it to the plan
        # iterate over a copy so that we can remove while we go
        while len(nodes):
            grounded_node = False
            for node in list(nodes):
                if self._is_grounded(node):
                    grounded_node = True
                    yield node
                    nodes.remove(node)
                    self._ground(node)

            if not grounded_node:
                raise ValueError(
                    ('CallGraphIterator never saw some nodes: {nodes}.  '
                     'Did see these nodes: {grounded_nodes}').format(
                        nodes=nodes,
                        grounded_nodes=set(
                            self._call_graph.nodes.copy()) - nodes,
                    )
                )


class QueryPlanner(object):

    def __init__(self, call_graph, query, query_shape):
        """
        query is necessary becuase the QueryPlan execution uses it to seed the
        state of the ResultSet object.
        """
        self.call_graph = call_graph

        initial_bindings = self._extract_initial_bindings_from_query(
            query, query_shape
        )
        if not isinstance(initial_bindings, ResultSet):
            initial_bindings = ResultSet([initial_bindings])

        self.plan = QueryPlan(
            initial_bindings,
            call_graph.output_paths(),
            query_shape
        )

    def _extract_initial_bindings_from_query(self, query, query_shape):
        """ convert a regular json query_shape into a nested structure of
        ResultSets and Results.

        WARNING: this wont work with list values like in a |= clause.  It
        would be ideal if the query object could be useful since it already
        knows these things.  Unfortunately it is the wrong shape though ...
        """

        if isinstance(query_shape, (list, tuple)):
            assert len(query_shape) == 1

            return ResultSet([
                self._extract_initial_bindings_from_query(q, qs)
                for q, qs in zip([query], query_shape)
            ])
        elif isinstance(query_shape, dict):
            initial_bindings = {}
            for k, v in query_shape.items():
                # if the query shape has a list on the right hand side, we
                # assume it is a nested resultset.
                if isinstance(v, list):
                    subquery = query.subquery(k)

                    v = self._extract_initial_bindings_from_query(subquery, v)
                    initial_bindings[k] = v
                else:
                    # otherwise, look in the query to see what value it has
                    for clause in query:
                        if clause.lhs == k:
                            initial_bindings[k] = v

            return Result(initial_bindings)

    def plan_query(self):
        for node in CallGraphIterator(self.call_graph):
            self.plan.append(node)

        return self.plan

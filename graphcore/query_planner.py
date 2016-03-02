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

    def _grounded_nodes(self, nodes):
        nodes_with_no_relations = []
        for node in list(nodes):
            if self._is_grounded(node):
                # put nodes with relations first so we can filter result set
                # before running unnecessary computation
                if node.relations != (None,):
                    yield node
                else:
                    nodes_with_no_relations.append(node)

        # we could use above algorithm and yield all nodes we know are ground
        # but have no relations, or we could just pick one to yield and then
        # see if that happens to ground any new nodes with relations before
        # running all of the others
        # There should be a smarter way to chose this search so as to optimally
        # hit nodes with relations as soon as possible
        if len(nodes_with_no_relations) > 0:
            yield nodes_with_no_relations[0]

    def __iter__(self):
        # local copy of set that we can modify
        nodes = list(self._call_graph.nodes)

        # if a node is grounded, add it to the plan
        # iterate over a copy so that we can remove while we go
        while len(nodes):
            grounded_node = False
            for node in self._grounded_nodes(nodes):
                grounded_node = True
                yield node
                nodes.remove(node)
                self._ground(node)

            # if we get here it means we made it through the entire list of
            # nodes and didnt find a grounded_node at all
            if not grounded_node:
                raise ValueError(
                    ('CallGraphIterator never saw some nodes: {nodes}.  '
                     'Did see these nodes: {grounded_nodes}').format(
                        nodes=nodes,
                        grounded_nodes=set(self._call_graph.nodes) - nodes,
                    )
                )


class QueryPlanner(object):

    def __init__(self, call_graph, query, query_shape, mapper):
        """
        query is necessary becuase the QueryPlan execution uses it to seed the
        state of the ResultSet object.
        """
        self.mapper = mapper
        self.call_graph = call_graph

        initial_bindings = self._extract_initial_bindings_from_query(
            query, query_shape
        )

        # attach query_shape to ResultSet
        if isinstance(initial_bindings, ResultSet):
            result_set = ResultSet(
                initial_bindings, query_shape, mapper=self.mapper
            )
        else:
            result_set = ResultSet(
                [initial_bindings], query_shape, mapper=self.mapper
            )

        self.plan = QueryPlan(
            result_set,
            call_graph.output_paths(),
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
            ], mapper=self.mapper)
        elif isinstance(query_shape, dict):
            initial_bindings = {}
            for k, v in query_shape.items():
                # if the query shape has a list on the right hand side, we
                # assume it is a nested resultset.
                if isinstance(v, list) and k[-2:] != '|=':
                    subquery = query.subquery(k)

                    v = self._extract_initial_bindings_from_query(subquery, v)
                    initial_bindings[k] = v
                else:
                    # otherwise, look in the query to see what value it has
                    for clause in query:
                        if clause.lhs == k:
                            initial_bindings[k] = v

            return Result(initial_bindings, mapper=self.mapper)

    def plan_query(self):
        for node in CallGraphIterator(self.call_graph):
            self.plan.append(node)

        return self.plan

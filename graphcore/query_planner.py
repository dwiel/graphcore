"""
This QueryPlanner will be very nieve.  Its role is to convert a CallGraph into
a QueryPlan
"""

from .query_plan import QueryPlan


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

    def __init__(self, call_graph, query):
        """
        query is necessary becuase the QueryPlan execution uses it to seed the
        state of the ResultSet object.
        """
        self.call_graph = call_graph
        self.plan = QueryPlan(
            self._extract_initial_bindings_rom_query(query),
            call_graph.output_paths()
        )

    def _extract_initial_bindings_rom_query(self, query):
        initial_bindings = {}
        for clause in query:
            if clause.value:
                initial_bindings[clause.lhs] = clause.value
        return initial_bindings

    def plan_query(self):
        for node in CallGraphIterator(self.call_graph):
            self.plan.append(node)

        return self.plan

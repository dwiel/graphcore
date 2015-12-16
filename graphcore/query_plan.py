"""
The query plan is a sequential list of rules to apply.  Other QueryPlans may in
the future also handle parallel execution.
"""

from .result_set import ResultSet, result_set_apply_rule


class QueryPlan(object):
    """ Execute a sequential list of nodes. """

    def __init__(self, initial_bindings, output_paths, query_shape):
        """
        query is necessary becuase the QueryPlan execution uses it to seed the
        state of the ResultSet object.
        """
        self.output_paths = output_paths

        self.nodes = []
        self.result_set = ResultSet(initial_bindings, query_shape)

    def append(self, node):
        self.nodes.append(node)

    def forward(self, limit=None):
        for node in self.nodes:
            self.result_set = result_set_apply_rule(
                self.result_set, node.function,
                self.result_set.shape_paths(node.incoming_paths),
                self.result_set.shape_paths(node.outgoing_paths),
                node.cardinality
            )

            for outgoing_path, relation in zip(
                node.outgoing_paths, node.relations
            ):
                if relation:
                    self.result_set.filter(outgoing_path, relation)

            if limit:
                self.result_set.limit(limit)

    def outputs(self):
        return self.result_set.extract_json(self.output_paths)

    def execute(self, limit=None):
        self.forward(limit=limit)

        return self.outputs()

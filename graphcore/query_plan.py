"""
The query plan is a sequential list of rules to apply.  Other QueryPlans may in
the future also handle parallel execution.
"""

from .result_set import ResultSet, result_set_apply_rule


class QueryPlan(object):

    def __init__(self, initial_bindings, output_paths):
        """
        query is necessary becuase the QueryPlan execution uses it to seed the
        state of the ResultSet object.
        """
        self.output_paths = output_paths

        self.nodes = []
        self.result_set = ResultSet(initial_bindings)

    def append(self, node):
        self.nodes.append(node)

    def forward(self):
        for node in self.nodes:
            self.result_set = result_set_apply_rule(
                self.result_set, node.rule.function,
                self.result_set.shape_paths(node.incoming_paths),
                self.result_set.shape_paths(node.outgoing_paths),
                node.rule.cardinality
            )

            if node.relation:
                self.result_set.filter(node.outgoing_paths[0], node.relation)

    def outputs(self):
        return self.result_set.extract_json(self.output_paths)

    def execute(self):
        self.forward()

        return self.outputs()

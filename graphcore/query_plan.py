"""
The query plan is a sequential list of rules to apply.  Other QueryPlans may in
the future also handle parallel execution.
"""

from .result_set import RuleApplicationException
from .result_set import default_exception_handler


class QueryPlan(object):
    """ Execute a sequential list of nodes. """

    def __init__(self, result_set, output_paths):
        """
        query is necessary becuase the QueryPlan execution uses it to seed the
        state of the ResultSet object.
        """
        self.result_set = result_set
        self.output_paths = output_paths

        self.nodes = []

    def append(self, node):
        self.nodes.append(node)

    def forward(self, exception_handler, limit=None):
        for node in self.nodes:
            try:
                self.result_set = self.result_set.apply_rule(
                    node.function,
                    self.result_set.shape_paths(node.incoming_paths),
                    self.result_set.shape_paths(node.outgoing_paths),
                    node.cardinality,
                    exception_handler=exception_handler
                )
            except RuleApplicationException as e:
                e.query_plan = self
                e.node = node
                raise

            for outgoing_path, relation in zip(
                node.outgoing_paths, node.relations
            ):
                if relation:
                    self.result_set.filter(outgoing_path, relation)

            if limit:
                self.result_set.limit(limit)

    def outputs(self):
        return self.result_set.extract_json(self.output_paths)

    def execute(self, exception_handler=default_exception_handler, limit=None):
        self.forward(exception_handler, limit=limit)

        return self.outputs()

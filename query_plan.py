"""
The query plan is a sequential list of rules to apply.  Other QueryPlans may in
the future also handle parallel execution.
"""

from .result_set import ResultSet

class QueryPlan(object):
    def __init__(self, query, output_paths):
        """
        query is necessary becuase the QueryPlan execution uses it to seed the
        state of the ResultSet object.
        """
        self.query = query
        self.output_paths = output_paths

        self.nodes = []
        self.result_set = ResultSet()
        self.result_set.extract_from_query(query)

    def append(self, node):
        self.nodes.append(node)

    def forward(self):
        # for input_clauses, output_clause, rule in reversed(self.nodes):
        for node in self.nodes:
            # TODO: only copy for cardinality 'many' where result_set size
            # changes.
            # must copy result set iterator since we are mutating it while we
            # iterate and don't want to iterate over the new result_set
            for result in self.result_set.copy():
                ret = node.rule.function(**{
                    path.relative.property: result.get(path)
                    for path in node.incoming_paths()
                    })

                # if the result of the rule is one value, just set the value,
                # otherwise, if there are many, explode out the result set
                if node.rule.cardinality == 'one':
                    result.set(node.outgoing_paths()[0], ret)
                elif node.rule.cardinality == 'many':
                    self.result_set.explode(result, node.outgoing_paths()[0], ret)
                else:
                    raise TypeError()

    def outputs(self):
        return self.result_set.extract_json(self.output_paths)

    def execute(self):
        self.forward()

        return self.outputs()

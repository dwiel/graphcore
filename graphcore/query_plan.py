"""
The query plan is a sequential list of rules to apply.  Other QueryPlans may in
the future also handle parallel execution.
"""

from .rule import Cardinality
from .result_set import ResultSet


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

    def apply(self, node, result):
        return node.rule.function(**{
            path.relative.property: result.get(path)
            for path in node.incoming_paths
        })

    def forward(self):
        for node in self.nodes:
            # TODO: only copy for cardinality 'many' where result_set size
            # changes.
            # must copy result set iterator since we are mutating it while we
            # iterate and don't want to iterate over the new result_set

            # if the result of the rule is one value, just set the value,
            # otherwise, if there are many, explode out the result set
            if node.rule.cardinality == Cardinality.one:
                for result in self.result_set:
                    ret = self.apply(node, result)

                    if len(node.rule.outputs) > 1:
                        for path, output in zip(node.outgoing_paths, ret):
                            result.set(path, output)
                    else:
                        result.set(node.outgoing_paths[0], ret)

            elif node.rule.cardinality == Cardinality.many:
                if len(node.rule.outputs) > 1:
                    raise NotImplementedError(
                        'cardinality.many and multiple outputs are'
                        'not yet supported'
                    )

                new_result_set = ResultSet()
                for result in self.result_set:
                    new_result_set.extend(
                        result.explode(
                            node.outgoing_paths[0], self.apply(node, result)
                        )
                    )
                self.result_set = new_result_set

            print(self.result_set)

            if node.relation:
                self.result_set.filter(node.outgoing_paths[0], node.relation)

    def outputs(self):
        return self.result_set.extract_json(self.output_paths)

    def execute(self):
        self.forward()

        return self.outputs()

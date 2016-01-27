from .sql_query import SQLQuery


def constrain_sql_queries(call_graph):
    """ Move relations on SQLQuery nodes out of graphcore relations and into
    the where clause of the SQLQuery
    """
    for node in call_graph.nodes:
        if isinstance(node.function, SQLQuery):
            new_relations = []
            for select, relation in zip(node.function.selects, node.relations):
                if relation is not None:
                    # we don't want to modify this function for all future
                    # queries, just this one.
                    node.function = node.function.copy()

                    if relation.operation == '==':
                        key = select
                    else:
                        key = select + relation.operation

                    node.function.where[key] = relation.value

                    relation = None

                new_relations.append(relation)
            node.relations = new_relations

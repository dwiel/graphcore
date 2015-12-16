from .rule import Rule, Cardinality
from .path import Path
from .query import Query
from .clause import Clause, Var, OutVar, TempVar
from . import call_graph
from .query_planner import QueryPlanner
from .equality_mixin import HashMixin, EqualityMixin


class QuerySearchIterator(object):

    def __init__(self, query):
        self.query = query

    def __iter__(self):
        return self

    def __next__(self):
        clause = self.query.clause_with_unbound_outvar()
        if clause:
            return clause
        else:
            raise StopIteration

    # python2 support
    next = __next__


class QuerySearch(object):
    """
    The QuerySearch object takes a Graphcore and a Query and generates a
    CallGraph.
    """

    def __init__(self, graphcore, query):
        # TODO: basic query validation
        self.query = Query(query)

        self.graphcore = graphcore

        self.call_graph = call_graph.CallGraph()

        # a set of paths which have been grounded in the course of the query
        # search
        self._grounded_paths = set()

        # a set of visited paths so that at the end of the search we can ensure
        # that all of the clauses were used to inform or constrain the query
        self._visited_paths = set()

    def _grounded(self, clause):
        return clause.lhs in self._grounded_paths

    def _ground(self, clause):
        self._grounded_paths.add(clause.lhs)

    def _visit(self, clause):
        self._visited_paths.add(clause.lhs)

    def clauses_with_unbound_outvar(self):
        return QuerySearchIterator(self)

    def clause_with_unbound_outvar(self):
        """ return a clause with a variable rhs which hasnt been grounded """
        for clause in self.query:
            if isinstance(clause.rhs, Var):
                if not self._grounded(clause):
                    return clause

    def apply_rule_backwards(self, output_clause, prefix, rule):
        """bind the output of rule to output_clause from the query"""

        # add input/unify clauses of function to query
        input_clauses = []
        for input in rule.inputs:
            # TODO: this is almost certainly an edge case handling rather than
            # handling the general case

            absolute_path = prefix + input[1:]

            # self.query.append is conditional on there not already
            # being a clause with this absolute_path
            input_clauses.append(
                self.query.append(Clause(absolute_path, TempVar()))
            )

        self.call_graph.add_node(
            [clause.lhs for clause in input_clauses],
            [output_clause.lhs],
            rule.function,
            rule.cardinality,
            relations=[output_clause.relation],
        )

        if isinstance(output_clause.rhs, OutVar):
            self.call_graph.edge(output_clause.lhs).out = True

        # this output clause is now grounded since it has a value
        self._ground(output_clause)

        for input_clause in input_clauses:
            self._visit(input_clause)

    def backward(self):
        """apply rules in reverse looking for the call chain that will be
        necessary to complete the query.

        we can pick any old clause off the stack since the order that rules are
        resolved, at this point in the search is unimportant.  We can always
        optimize the call graph later, one we have one.
        """
        try:
            for clause in self.clauses_with_unbound_outvar():
                self.apply_rule_backwards(
                    clause, *self.graphcore.lookup_rule(clause.lhs)
                )
        except PathNotFound as e:
            e.dependent_nodes = self.call_graph.nodes_depending_on_path(e.path)
            raise

        # all nodes should be either ground, or visited
        used_paths = self._grounded_paths | self._visited_paths
        if len(used_paths) != len(self.query):
            # find clauses which aren't in these sets and convert them to a
            # relation, instead of a ground value
            for clause in self.query:
                if clause.lhs not in used_paths:
                    clause.convert_to_constraint()

            # rerun with new constraints
            self.backward()


class PropertyType(HashMixin, EqualityMixin):

    def __init__(self, base_type, property, other_type):
        self.base_type = base_type
        self.property = property
        self.other_type = other_type

    def __repr__(self):
        return (
            '<PropertyType {base_type}.{property} is '
            'type {other_type}>'.format(**self.__dict__)
        )


class Schema(object):

    def __init__(self):
        self.property_types = []

    def append(self, property_type):
        self.property_types.append(property_type)

    def __str__(self):
        return repr(self.property_types)

    def __repr__(self):
        return '<Schema {str}>'.format(str=str(self))

    def base_type_and_property_of_path(self, path):
        for relation in self.property_types:
            if path[0] == relation.base_type:
                if path[1] == relation.property:
                    # TODO: this return type prefix, rule is kinda nasty ...
                    return (
                        path[:2],
                        relation.other_type + path[2:],
                    )

        return Path([]), path


class PathNotFound(Exception):
    def __init__(self, path):
        self.path = path
        self.dependent_nodes = []

    def __str__(self):
        if self.dependent_nodes:
            return (
                (
                    '{path} not found.  nodes depending on this '
                    'path: {nodes}'
                ).format(
                    path=self.path,
                    nodes=', '.join(node.name for node in self.dependent_nodes)
                )
            )
        else:
            return (
                (
                    '{path} not found.  {path} is not depended on by any '
                    'node'
                ).format(
                    path=self.path,
                )
            )


class Graphcore(object):

    def __init__(self):
        # rules are indexed by the Path of thier output
        self.rules = []
        self.schema = Schema()

    def property_type(self, base_type, property, other_type):
        self.schema.append(
            PropertyType(base_type, property, other_type)
        )

    def register_rule(self, inputs, output,
                      cardinality=Cardinality.one,
                      function=None):
        self.rules.append(Rule(
            function, inputs, output, cardinality
        ))

    def rule(self, inputs, output, cardinality=Cardinality.one):
        def decorator(fn):
            self.rules.append(Rule(
                fn, inputs, output, cardinality
            ))
            return fn
        return decorator

    def available_rules_string(self):
        return ', '.join(
            ', '.join(map(str, rule.outputs)) for rule in self.rules
        )

    def lookup_rule(self, path):
        """ Given a clause, return a prefix and a rule which match the
        clause.

        The prefix will be a list of parts of the lhs of the clause which
        the rule is applied to.  For example if there is a rule which maps
        from book.id to book.name and the query has a user.book.id then
        this function will return ['user.'], Rule(book.id -> book.name).
        """

        for prefix, subpath in path.subpaths():
            # if there is a non empty prefix, only apply rules with more than 0
            # inputs.  0 input rules can only be applied to the root.  see
            # https://github.com/dwiel/graphcore/issues/17
            if len(prefix) != 1:
                rules = [rule for rule in self.rules if len(rule.inputs) > 0]
            else:
                rules = self.rules

            # first try finding a match direct on the root
            for rule in rules:
                if subpath in rule.outputs:
                    return prefix, rule

            # then try extracting the base type out and finding a prefix
            subprefix, subpath = self.schema.base_type_and_property_of_path(
                subpath
            )

            # because prefix and subpath overlap where they meet, remove the
            # last part from prefix so that this addition doesnt duplicate that
            # part.
            prefix = prefix[:-1] + subprefix

            for rule in rules:
                if subpath in rule.outputs:
                    return prefix, rule

        raise PathNotFound(path)

    def optimize(self, query_search):
        # optimize query.call_graph here
        from .optimize_reduce_like_parent_child import reduce_like_parent_child
        from .sql_query import SQLQuery
        query_search.call_graph = reduce_like_parent_child(
            query_search.call_graph, SQLQuery, SQLQuery.merge_parent_child
        )

    def query(self, query, limit=None):
        query_search = QuerySearch(self, query)

        query_search.backward()

        self.optimize(query_search)

        query_planner = QueryPlanner(
            query_search.call_graph, query_search.query, query
        )
        query_plan = query_planner.plan_query()

        return query_plan.execute(limit=limit)

    def explain(self, query):
        query_search = QuerySearch(self, query)

        query_search.backward()

        self.optimize(query_search)

        return query_search.call_graph.explain()

    def search_outputs(self, search="", prefix=""):
        """ return a list of outputs which contain `search` and/or begin with
        `prefix`

        useful for interactive exploration and debugging.
        """
        ret = []

        for rule in self.rules:
            for output in rule.outputs:
                if str(output).find(prefix) == 0:
                    if search in str(output):
                        ret.append(str(output))

        return ret

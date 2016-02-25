import six

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
            e.call_graph = self.call_graph
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

    def _lookup(self, base_type, property):
        # TODO: use dict
        for property_type in self.property_types:
            if base_type == property_type.base_type:
                if property == property_type.property:
                    return property_type.other_type

    def resolve_type(self, path, pos=-1):
        """ given a full path and an index into that path, return the type of
        the value of the property at that index """

        # this is the root so no way for it to have a different type
        if abs(pos) == len(path):
            return path[pos]

        return self._lookup(
            self.resolve_type(path, pos - 1), path[pos]
        ) or path[pos]


class PathNotFound(Exception):
    def __init__(self, path, gc):
        self.gc = gc
        self.path = path
        self.dependent_nodes = []
        self.call_graph = None

    def __str__(self):
        property_name = str(self.path[-1])
        if property_name == 'id':
            property_name = str(self.path[-2:])

        details = ''

        if self.call_graph:
            details += 'call_graph so far:\n'
            details += self.call_graph.explain()

        details += '\n\n{} found in the following outputs:'.format(
            property_name
        )
        for output in self.gc.search_outputs(property_name)[:30]:
            if output[-len(property_name):] == property_name:
                details += '\n    ' + output

        if self.dependent_nodes:
            return (
                (
                    '{path} not found.  nodes depending on this '
                    'path: {nodes}\n\n{details}'
                ).format(
                    path=self.path,
                    nodes=', '.join(
                        node.name for node in self.dependent_nodes
                    ),
                    details=details,
                )
            )
        else:
            return (
                (
                    '{path} not found.  {path} is not depended on by any '
                    'node\n\n{details}'
                ).format(
                    path=self.path,
                    details=details,
                )
            )


class BaseTypeNotFound(PathNotFound):
    def __init__(self, subpath, path):
        self.subpath = subpath
        self.path = path

    def __str__(self):
        return (
            '{subpath} type not found.  occurred in {path}'.format(
                **self.__dict__
            )
        )


class DefineTypeContext(object):
    def __init__(self, gc, type_name):
        self.gc = gc
        self.type_name = type_name

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def module(self, module):
        from .reflect_module import ModuleReflector
        ModuleReflector(self.gc, module, self.type_name)

    def reflect_class(self, cls, type_name=None):
        from .reflect_class import reflect_class
        reflect_class(self.gc, cls, type_name)

    def property_type(self, property_name, property_type=None):
        if property_type is None:
            property_type = property_name

        self.gc.property_type(self.type_name, property_name, property_type)

    def direct_map(self, input, output):
        if isinstance(output, six.string_types):
            outputs = [output]
        else:
            outputs = output

        input = self.type_name + '.' + input

        for output in outputs:
            output = self.type_name + '.' + output
            self.gc.direct_map(input, output)


class Rules(object):
    def __init__(self):
        self.rules = []
        self.require_input_rules = []

        self.rules_by_output_path = {}
        self.require_input_rules_by_output_path = {}

    def append(self, rule):
        self.rules.append(rule)
        for output in rule.outputs:
            self.rules_by_output_path[str(output)] = rule

        if len(rule.inputs) > 0:
            self.require_input_rules.append(rule)
            for output in rule.outputs:
                self.require_input_rules_by_output_path[str(output)] = rule

    def lookup(self, path, require_input):
        if require_input:
            return self.require_input_rules_by_output_path.get(str(path))
        else:
            return self.rules_by_output_path.get(str(path))

    def __iter__(self):
        return iter(self.rules)

    def __len__(self):
        return len(self.rules)


class Graphcore(object):

    def __init__(self, mapper=map):
        # rules are indexed by the Path of thier output
        self.rules = Rules()
        self.schema = Schema()
        self.mapper = mapper

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

    def direct_map(self, input, output):
        def mapper(**kwargs):
            return next(iter(kwargs.values()))
        mapper.__name__ = ''
        self.register_rule([input], output, function=mapper)

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
        this function will return ['user.book'], Rule(book.id -> book.name).
        """

        # check for rules matching longer subpaths first as they are more
        # specific.  for example:
        #     person.id might match on a [] -> person.id rule
        #     github_account.person.id might match on a more specific rule
        for prefix, subpath in reversed(list(path.subpaths())):
            # if there is a non empty prefix, only apply rules with more than 0
            # inputs.  0 input rules can only be applied to the root.  see
            # https://github.com/dwiel/graphcore/issues/17
            require_input = len(prefix) != 1

            # fix type of left most part of subpath
            base_type = self.schema.resolve_type(prefix)
            subpath = base_type + subpath[1:]

            # first try finding a match direct on the root
            rule = self.rules.lookup(subpath, require_input)
            if rule is not None:
                return prefix, rule

        for subpath in path[:-1]:
            if str(subpath) not in self.base_types():
                raise BaseTypeNotFound(subpath, path)

        raise PathNotFound(path, self)

    def optimize(self, query_search):
        # optimize query.call_graph here
        from .optimize_reduce_like_parent_child import reduce_like_parent_child
        from .sql_query import SQLQuery
        query_search.call_graph = reduce_like_parent_child(
            query_search.call_graph, SQLQuery, SQLQuery.merge_parent_child
        )

        from .optimize_constrain_sql_queries import constrain_sql_queries
        constrain_sql_queries(query_search.call_graph)

    def query(self, query, limit=None):
        query_search = QuerySearch(self, query)

        query_search.backward()

        self.optimize(query_search)

        query_planner = QueryPlanner(
            query_search.call_graph, query_search.query, query,
            mapper=self.mapper
        )
        query_plan = query_planner.plan_query()

        return query_plan.execute(limit=limit)

    def explain(self, query):
        query_search = QuerySearch(self, query)

        query_search.backward()

        self.optimize(query_search)

        return query_search.call_graph.explain()

    def base_types(self):
        ret = set()
        for rule in self.rules:
            for output in rule.outputs:
                for subpath in Path(output)[:-1]:
                    ret.add(str(subpath))
        return sorted(ret)

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

    def define_type(self, type_name):
        return DefineTypeContext(self, type_name)

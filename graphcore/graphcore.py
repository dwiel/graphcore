from .relation import Relation
from .rule import Rule, Cardinality
from .path import Path
from . import call_graph
from .query_planner import QueryPlanner
from .equality_mixin import HashMixin, EqualityMixin


class Var(object):
    pass


class OutVar(Var):
    pass


class TempVar(Var):
    pass


class Clause(object):

    def __init__(self, key, value):
        self.lhs, self.rhs, self.relation = self._parse_clause(key, value)

        # TODO: document what self.value is
        if isinstance(self.rhs, Var):
            self.value = None
        else:
            self.value = value

    def _parse_clause(self, lhs, rhs):
        if str(lhs)[-1] == '?':
            return Path(lhs[:-1]), OutVar(), None

        # relational clauses get a TempVar rhs to signify that we need to
        # compute their value, but the consumer of the query isn't interested
        # in getting the value in the output
        if len(lhs) >= 2:
            if str(lhs)[-2:] == '!=':
                return Path(lhs[:-2]), TempVar(), Relation('!=', rhs)
            elif str(lhs)[-2:] == '<=':
                return Path(lhs[:-2]), TempVar(), Relation('<=', rhs)
            elif str(lhs)[-2:] == '>=':
                return Path(lhs[:-2]), TempVar(), Relation('>=', rhs)
            elif str(lhs)[-2:] == '|=':
                return Path(lhs[:-2]), TempVar(), Relation('|=', rhs)

        if str(lhs)[-1] == '<':
            return Path(lhs[:-1]), TempVar(), Relation('<', rhs)
        elif str(lhs)[-1] == '>':
            return Path(lhs[:-1]), TempVar(), Relation('>', rhs)
        else:
            return Path(lhs), rhs, None

    def merge(self, other):
        """ Combine other clause into self by mutating self

        This happens when we get additional constraints in a clause:

            'x?': None,
            'x>': 1,

        or when a query search is taking place and it wants to ensure
        that a TempVar is marked on a path that it depends on.  This
        may happen if there is a relational constraint on a path that
        another cause depends on as an input.
        """
        if self.relation and other.relation:
            # In theory, this may be possible
            raise NotImplementedError
        else:
            self.relation = self.relation or other.relation

        if isinstance(self.rhs, TempVar):
            self.rhs = other.rhs
        else:
            if not isinstance(other.rhs, TempVar):
                raise ValueError(
                    'both clauses cant have a non-TempVar '
                    'rhs: {rhs}, {other_rhs}'.format(
                        rhs=self.rhs, other_rhs=other.rhs
                    )
                )

    def __str__(self):
        return '{lhs} {rhs}'.format(**self.__dict__)

    def __repr__(self):
        return '<Clause ({lhs}) ({rhs}) ({relation})>'.format(
            **self.__dict__
        )


class Query(object):

    def __init__(self, query):
        self.clauses = []
        self.clause_map = {}

        self.extend(query)

    def extend(self, query, prefix=''):
        """ extend this Query with the query parameter type dict

        if a prefix is provided, it will be prepended to all key names
        """

        for key, value in query.items():
            if isinstance(value, list):
                # TODO: check if value should be list
                self.extend(value[0], prefix=key+'.')
            else:
                self.append(Clause(prefix+key, value))

    def append(self, clause):
        if clause.lhs not in self.clause_map:
            self.clauses.append(clause)
            self.clause_map[clause.lhs] = clause
        else:
            self.clause_map[clause.lhs].merge(clause)

        return self.clause_map[clause.lhs]

    def __iter__(self):
        return iter(self.clauses)

    def __getitem__(self, index):
        return self.clauses[index]

    def __str__(self):
        return '[\n%s]' % ''.join(
            '  ' + str(clause) + '\n' for clause in self.clauses
        )


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

    def _grounded(self, clause):
        return clause.lhs in self._grounded_paths

    def _ground(self, clause):
        self._grounded_paths.add(clause.lhs)

    def clauses_with_unbound_outvar(self):
        return QuerySearchIterator(self)

    def clause_with_unbound_outvar(self):
        """ return a caluse with a variable rhs which hasnt been grounded """
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

            if len(prefix):
                absolute_path = prefix + input[1:]
            else:
                absolute_path = input

            # self.query.append is conditional on there not already
            # being a clause with this absolute_path
            input_clauses.append(
                self.query.append(Clause(absolute_path, TempVar()))
            )

        self.call_graph.add_node(
            [clause.lhs for clause in input_clauses],
            [output_clause.lhs],
            rule,
            relation=output_clause.relation
        )

        if isinstance(output_clause.rhs, OutVar):
            self.call_graph.edge(output_clause.lhs).out = True

        # this output clause is now grounded since it has a value
        self._ground(output_clause)

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
                        Path(path[:2]),
                        Path((relation.other_type,) + path[2:]),
                    )

        return [], path


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
            prefix, subpath = self.schema.base_type_and_property_of_path(
                subpath
            )

            for rule in rules:
                if subpath in rule.outputs:
                    return prefix, rule

        raise PathNotFound(path)

    def query(self, query):
        query = QuerySearch(self, query)

        query.backward()

        # optimize query.call_graph here

        query_planner = QueryPlanner(query.call_graph, query.query)
        query_plan = query_planner.plan_query()

        return query_plan.execute()

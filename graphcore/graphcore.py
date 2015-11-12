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

        if isinstance(self.rhs, Var):
            self.grounded = False
            self.value = None
        else:
            self.grounded = True
            self.value = value

    def _parse_clause(self, lhs, rhs):
        if str(lhs)[-1] == '?':
            return Path(lhs[:-1]), OutVar(), None
        if len(lhs) >= 2:
            if str(lhs)[-2:] == '!=':
                return Path(lhs[:-2]), OutVar(), Relation('!=', rhs)
            elif str(lhs)[-2:] == '<=':
                return Path(lhs[:-2]), OutVar(), Relation('<=', rhs)
            elif str(lhs)[-2:] == '>=':
                return Path(lhs[:-2]), OutVar(), Relation('>=', rhs)
        if str(lhs)[-1] == '<':
            return Path(lhs[:-1]), OutVar(), Relation('<', rhs)
        elif str(lhs)[-1] == '>':
            return Path(lhs[:-1]), OutVar(), Relation('>', rhs)
        else:
            return Path(lhs), rhs, None

    def has_unbound_outvar(self):
        if isinstance(self.rhs, Var):
            if not self.grounded:
                return True
        return False

    def ground(self):
        self.grounded = True

    def __str__(self):
        return '{lhs} {rhs}'.format(**self.__dict__)

    def __repr__(self):
        return '<Clause ({lhs}) ({rhs}) grounded={grounded}>'.format(
            **self.__dict__
        )


class Query(object):

    def __init__(self, query):
        self.clauses = []
        self.clause_map = {}

        for key, value in query.items():
            self.append(Clause(key, value))

    def append(self, clause):
        if clause.lhs not in self.clause_map:
            self.clauses.append(clause)
            self.clause_map[clause.lhs] = clause

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

    def clauses_with_unbound_outvar(self):
        return QuerySearchIterator(self)

    def clause_with_unbound_outvar(self):
        for clause in self.query:
            if clause.has_unbound_outvar():
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

        output_clause.ground()

    def backward(self):
        """apply rules in reverse looking for the call chain that will be
        necessary to complete the query.

        we can pick any old clause off the stack since the order that rules are
        resolved, at this point in the search is unimportant.  We can always
        optimize the call graph later, one we have one.
        """
        for clause in self.clauses_with_unbound_outvar():
            self.apply_rule_backwards(
                clause, *self.graphcore.lookup_rule_for_clause(clause)
            )


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

    def lookup_rule_for_clause(self, clause):
        for prefix, path in clause.lhs.subpaths():
            # TODO: this will almost certainly become a loop looking for
            # possible matches

            # first try finding a match direct on the root
            for rule in self.rules:
                if path in rule.outputs:
                    return prefix, rule

            # then try extracting the base type out and finding a prefix
            prefix, path = self.schema.base_type_and_property_of_path(path)

            for rule in self.rules:
                if path in rule.outputs:
                    return prefix, rule

        raise IndexError(
            '{path} not found in available rules: {rules}'.format(
                path=path,
                rules=self.available_rules_string(),
            )
        )

    def query(self, query):
        query = QuerySearch(self, query)

        query.backward()

        # optimize query.call_graph here

        query_planner = QueryPlanner(query.call_graph, query.query)
        query_plan = query_planner.plan_query()

        return query_plan.execute()

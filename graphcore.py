class Var(object):
    pass


class OutVar(Var):
    pass


class TempVar(Var):
    pass


class Path(object):
    def __init__(self, init):
        if isinstance(init, basestring):
            self.parts = tuple(init.split('.'))
        elif isinstance(init, Path):
            self.parts = tuple(init.parts)
        elif isinstance(init, (tuple, list)):
            self.parts = tuple(init)
        else:
            raise TypeError()

    @property
    def relative(self):
        return Path(self.parts[-2:])

    @property
    def property(self):
        return self.parts[-1]

    def reroot_path(self, other):
        # TODO: assert that self.parts[:-1] is same type as other.parts[0]
        return Path(self.parts[:-1] + other.parts[-1:])

    def subpaths(self):
        for i in range(-2, -len(self.parts) - 1, -1):
            yield Path(self.parts[i:])

    def __repr__(self):
        return '<Path {str}>'.format(str=str(self))

    def __str__(self):
        return '.'.join(self.parts)

    def __hash__(self):
        return hash(self.parts)

    def __eq__(self, other):
        return self.parts == other.parts


class Clause(object):
    def __init__(self, key, value):
        self.lhs, self.rhs = self._parse_clause(key, value)

        if isinstance(self.rhs, Var):
            self.grounded = False
            self.value = None
        else:
            self.grounded = True
            self.value = value

    def _parse_clause(self, lhs, rhs):
        if str(lhs)[-1] == '?':
            return Path(lhs[:-1]), OutVar()
        else:
            return Path(lhs), rhs

    def has_unbound_outvar(self):
        if isinstance(self.rhs, Var):
            if not self.grounded:
                return True
        return False

    def ground(self):
        self.grounded = True

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

    def output_paths(self):
        return [
            clause.lhs for clause in self.clauses
            if isinstance(clause.rhs, OutVar)
        ]

    def __iter__(self):
        return iter(self.clauses)

    def __getitem__(self, index):
        return self.clauses[index]


class QueryPlanIterator(object):
    def __init__(self, query):
        self.query = query

    def __iter__(self):
        return self

    def next(self):
        clause = self.query.clause_with_unbound_outvar()
        if clause:
            return clause
        else:
            raise StopIteration


class Result(object):
    def __init__(self, result=None):
        if isinstance(result, Result):
            self.result = result.result.copy()
        else:
            self.result = {}

    def set(self, path, value):
        print 'set', self, path, value
        self.result[str(path)] = value

    def get(self, path):
        print 'Result.get'
        print '  self:', self
        print '  path:', path
        return self.result[str(path)]

    def to_json(self):
        return self.result

    def extract_json(self, paths):
        return {
            str(path): self.get(path) for path in paths
        }

    def __repr__(self):
        return '<Result {result}>'.format(result=repr(self.result))


class ResultSet(object):
    def __init__(self):
        # TODO handle more complex result set toplogies
        self.results = [Result()]

    def set(self, path, value):
        if isinstance(value, list):
            # similar to self.results *= len(values), but with better handling
            # of copies of results
            print 'set many'
            print '  path:', path
            print '  value:', value
            self.results = [
                Result(result)
                for _ in range(len(value))
                for result in self.results
            ]

            for result, subvalue in zip(self.results, value):
                result.set(path, subvalue)
        else:
            print 'set single'
            print '  path:', path
            print '  value:', value
            for result in self.results:
                result.set(path, value)

    def get(self, path):
        # TODO: this is definitely wrong
        print 'get'
        print '  self:', self
        print '  path:', path
        ret = self.results[0].get(path)
        print '  ret:', ret
        return ret

    def extract_from_query(self, query):
        for clause in query:
            if clause.value:
                self.set(clause.lhs, clause.value)

    def to_json(self):
        return [
            result.to_json() for result in self.results
        ]

    def extract_json(self, paths):
        return [
            result.extract_json(paths) for result in self.results
        ]

    def __repr__(self):
        return '<ResultSet {str}>'.format(str=str(self))

    def __str__(self):
        return str(self.to_json())


class QueryPlan(object):
    def __init__(self, graphcore, query):
        # TODO: basic query validation
        self.query = Query(query)
        self.result_set = ResultSet()
        self.result_set.extract_from_query(self.query)

        self.graphcore = graphcore
        self.rules = []

    def clauses_with_unbound_outvar(self):
        return QueryPlanIterator(self)

    def clause_with_unbound_outvar(self):
        for clause in self.query:
            if clause.has_unbound_outvar():
                return clause

    def apply_rule(self, output_clause, rule):
        """bind the output of rule to output_clause from the query"""

        # add input/unify clauses of function to query
        input_clauses = []
        for input in rule.inputs:
            # what is here now is not correct, but no tests will fail it yet. :)
            # it will need to be something like one of these two:
            #     absolute_path = output_clause.lhs.reroot_path(input)
            #     absolute_path = input.reroot_path(output_clause.lhs)
            absolute_path = input
            print 'reroot_path'
            print '  output_clause.lhs:', output_clause.lhs
            print '  rule.input:', input
            print '  absolute_path:', absolute_path

            # this append is conditional on there not already being a clause
            # with this absolute_path
            input_clauses.append(
                self.query.append(Clause(absolute_path, TempVar()))
            )

        print 'apply_rule_backward'
        print '  input_clauses:', input_clauses
        print '  output_clause:', output_clause
        print '  rule:', rule
        self.rules.append((input_clauses, output_clause, rule))

        output_clause.ground()

    def backward(self):
        for clause in self.clauses_with_unbound_outvar():
            self.apply_rule(
                clause, self.graphcore.lookup_rule_for_clause(clause)
            )

    def forward(self):
        # TODO: somehow make this work for more than single object output
        for input_clauses, output_clause, rule in reversed(self.rules):
            print 'forward', input_clauses, output_clause, rule
            self.result_set.set(output_clause.lhs, rule.function(**dict(
                (clause.lhs.relative.property, self.result_set.get(clause.lhs))
                for clause in input_clauses
            )))

    def outputs(self):
        return self.result_set.extract_json(self.query.output_paths())

    def outputs_(self):
        # TODO: allow ret to be more complex than single object
        ret = {}
        for clause in self.query:
            if isinstance(clause.rhs, OutVar):
                ret[str(clause.lhs)] = clause.value

        return ret


class Rule(object):
    def __init__(self, function, inputs, output):
        self.function = function
        self.inputs = [Path(input) for input in inputs]
        self.output = Path(output)


class Relationship(object):
    def __init__(self, base_type, kind, property, other_type):
        self.base_type = base_type
        self.kind = kind
        self.property = property
        self.other_type = other_type


class Schema(object):
    def __init__(self):
        self.relationships = []

    def append(self, relationship):
        self.relationships.append(relationship)


class Graphcore(object):
    def __init__(self):
        # rules are indexed by the Path of thier output
        self.rules = {}
        self.schema = Schema()

    def has_many(self, base_type, property, other_type):
        self.schema.append(
            Relationship(base_type, 'has_many', property, other_type)
        )

    def rule(self, inputs, output):
        def decorator(fn):
            self.rules[Path(output)] = Rule(
                fn, inputs, output
            )
            return fn
        return decorator

    def outvar(self):
        return OutVar()

    def available_rules_string(self):
        return ', '.join(
            str(rule.output) for rule in self.rules.itervalues()
        )

    def lookup_rule_for_clause(self, clause):
        for path in clause.lhs.subpaths():
            print path
            if path in self.rules:
                return self.rules[path]

        raise IndexError(
            '{path} not found in available rules: {rules}'.format(
                path=path,
                rules=self.available_rules_string(),
            )
        )

    def apply_macros(self):
        pass

    def query(self, query):
        query = QueryPlan(self, query)

        self.apply_macros()

        # TODO: move backward/forward/outputs call to QueryPlan
        query.backward()

        query.forward()

        return query.outputs()

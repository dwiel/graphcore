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


class QueryPlan(object):
    def __init__(self, graphcore, query):
        # TODO: basic query validation
        self.query = Query(query)

        self.graphcore = graphcore
        self.rules = []

    def clauses_with_unbound_outvar(self):
        return QueryPlanIterator(self)

    def clause_with_unbound_outvar(self):
        for clause in self.query:
            if clause.has_unbound_outvar():
                return clause

    def apply_rule(self, output_clause, rule):
        # add input/unify clauses of function to query
        input_clauses = []
        for input in rule.inputs:
            absolute_path = output_clause.lhs.reroot_path(input)

            # this append is conditional on there not already being a clause
            # with this absolute_path
            input_clauses.append(
                self.query.append(Clause(absolute_path, TempVar()))
            )

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
            output_clause.value = rule.function(**dict(
                (clause.lhs.relative.property, clause.value)
                for clause in input_clauses
            ))

    def outputs(self):
        # TODO: allow ret to be more complex than single object
        ret = {}
        for clause in self.query:
            if isinstance(clause.rhs, OutVar):
                ret[str(clause.lhs)] = clause.value

        return ret


class Rule(object):
    def __init__(self, function, inputs, output):
        self.function = function
        self.inputs = inputs
        self.output = output


class Graphcore(object):
    def __init__(self):
        self.rules = {}

    def rule(self, inputs, output):
        def decorator(fn):
            self.rules[Path(output)] = Rule(
                fn, map(Path, inputs), Path(output)
            )
            return fn
        return decorator

    def outvar(self):
        return OutVar()

    def lookup_rule_for_clause(self, clause):
        relative_path = clause.lhs.relative
        if relative_path not in self.rules:
            raise IndexError(
                '{relative_path} not found in rules {rules}'.format(
                    relative_path=relative_path,
                    rules=self.rules,
                )
            )
        else:
            return self.rules[relative_path]

    def apply_macros(self):
        pass

    def query(self, query):
        query = QueryPlan(self, query)

        self.apply_macros()

        # TODO: move backward/forward/outputs call to QueryPlan
        query.backward()

        query.forward()

        return query.outputs()

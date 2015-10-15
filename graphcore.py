class OutVar(object):
    pass


class TempVar(OutVar):
    pass


class RelativePath(object):
    def __init__(self, init):
        if isinstance(init, basestring):
            split = init.split('.')
            if len(split) != 2:
                raise ValueError('RelativePath must be something.something')
            self.type, self.property = split
        elif isinstance(init, (list, tuple)):
            if len(init) != 2:
                raise ValueError(
                    'RelativePath can take in a tuple of length 2 only'
                )
            self.type, self.property = init
        else:
            raise ValueError(
                'RelativePath can take in only a tuple or a string, '
                'got a {type}'.format(type=type(init))
            )

    def __hash__(self):
        return hash((self.type, self.property))

    def __str__(self):
        return '{type}.{property}'.format(**self.__dict__)

    __repr__ = __str__

    def __eq__(self, other):
        return self.type == other.type and self.property == other.property


class AbsolutePath(object):
    def __init__(self, string):
        if isinstance(string, basestring):
            split = string.split('.')
            if len(split) < 2:
                raise ValueError(
                    'AbsolutePath must have atleast one . in the strong'
                )

            self.root = '.'.join(split[:-2])
            self.relative = RelativePath(split[-2:])
        elif isinstance(string, AbsolutePath):
            self.root = string.root
            self.relative = string.relative
        else:
            raise ValueError(
                'AbsolutePath takes only a string as input, '
                'got a {type}'.format(type=type(string))
            )

    def root_relative_path(self, relative):
        """returns an absolute path representive absolute+relative"""

        return AbsolutePath(self.root + '.' + str(relative))

    def __repr__(self):
        return '<AbsolutePath {str}>'.format(str=str(self))

    def __str__(self):
        if self.root:
            return '{root}.{relative}'.format(**self.__dict__)
        else:
            return '{relative}'.format(**self.__dict__)

    def __hash__(self):
        return hash((self.root, self.relative))

    def __eq__(self, other):
        return self.root == other.root and self.relative == other.relative


class Clause(object):
    def __init__(self, key, value):
        self.lhs = AbsolutePath(key)
        self.rhs = value

        if isinstance(self.rhs, OutVar):
            self.grounded = False
            self.value = None
        else:
            self.grounded = True
            self.value = value

    def has_unbound_outvar(self):
        if isinstance(self.rhs, OutVar):
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
            absolute_path = output_clause.lhs.root_relative_path(input)

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
        for input_clauses, output_clause, rule in self.rules:
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

    def input(self, inputs):
        def decorator(fn):
            self.rules[RelativePath(fn._output)] = Rule(
                fn, map(RelativePath, inputs), RelativePath(fn._output)
            )
            return fn

        return decorator

    def output(self, output):
        def decorator(fn):
            fn._output = output
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

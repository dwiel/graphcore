import six


class Var(object):
    pass


class OutVar(Var):
    pass


class TempVar(Var):
    pass


class Path(object):
    def __init__(self, init):
        if isinstance(init, six.string_types):
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

    def __getitem__(self, index):
        return self.parts[index]

    def __len__(self):
        return len(self.parts)

    def __add__(self, other):
        if isinstance(other, tuple):
            return Path(self.parts + other)
        else:
            return Path(self.parts + other.parts)


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

    def output_paths(self):
        return [
            clause.lhs for clause in self.clauses
            if isinstance(clause.rhs, OutVar)
        ]

    def __iter__(self):
        return iter(self.clauses)

    def __getitem__(self, index):
        return self.clauses[index]

    def __str__(self):
        return '[\n%s]' % ''.join(
            '  ' + str(clause) + '\n' for clause in self.clauses
        )


class QueryPlanIterator(object):
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


class Result(object):
    def __init__(self, result=None):
        if isinstance(result, Result):
            self.result = result.result.copy()
        else:
            self.result = {}

    def set(self, path, value):
        self.result[str(path)] = value

    def get(self, path):
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
    def __init__(self, init=None):
        # TODO handle more complex result set toplogies
        if isinstance(init, ResultSet):
            self.results = init.results.copy()
        else:
            self.results = {Result()}

    def set(self, path, value):
        for result in self.results:
            result.set(path, value)

    def explode(self, existing_result, path, values):
        new_results = {
            Result(existing_result)
            for _ in range(len(values))
        }

        for result, value in zip(new_results, values):
            result.set(path, value)

        self.results.remove(existing_result)
        self.results.update(new_results)

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

    def __iter__(self):
        return iter(self.results)

    def copy(self):
        return ResultSet(self)


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

            # this append is conditional on there not already being a clause
            # with this absolute_path
            input_clauses.append(
                self.query.append(Clause(absolute_path, TempVar()))
            )

        self.rules.append((input_clauses, output_clause, rule))

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

    def forward(self):
        for input_clauses, output_clause, rule in reversed(self.rules):
            # must copy result set iterator since we are mutating it while we
            # iterate and don't want to iterate over the new result_set
            for result in self.result_set.copy():
                ret = rule.function(**dict(
                    (clause.lhs.relative.property, result.get(clause.lhs))
                    for clause in input_clauses
                ))

                # if the result of the rule is one value, just set the value,
                # otherwise, if there are many, explode out the result set
                if rule.cardinality == 'one':
                    result.set(output_clause.lhs, ret)
                elif rule.cardinality == 'many':
                    self.result_set.explode(result, output_clause.lhs, ret)
                else:
                    raise TypeError()

    def outputs(self):
        return self.result_set.extract_json(self.query.output_paths())

    def apply_macros(self):
        pass

    def execute(self):
        self.apply_macros()

        self.backward()

        self.forward()

        return self.outputs()


class Rule(object):
    def __init__(self, function, inputs, output, cardinality):
        self.function = function
        self.inputs = [Path(input) for input in inputs]
        self.output = Path(output)
        self.cardinality = cardinality


class Relationship(object):
    def __init__(self, base_type, kind, property, other_type):
        self.base_type = base_type
        self.kind = kind
        self.property = property
        self.other_type = other_type

    def __repr__(self):
        return (
            '<Relationship {base_type} {kind} {property} of '
            'type {other_type}>'.format(**self.__dict__)
        )


class Schema(object):
    def __init__(self):
        self.relationships = []

    def append(self, relationship):
        self.relationships.append(relationship)

    def __str__(self):
        return repr(self.relationships)

    def __repr__(self):
        return '<Schema {str}>'.format(str=str(self))

    def __iter__(self):
        return iter(self.relationships)

    def base_type_and_property_of_path(self, path):
        for relation in self.relationships:
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

    def has_many(self, base_type, property, other_type):
        self.schema.append(
            Relationship(base_type, 'has_many', property, other_type)
        )

    def rule(self, inputs, output, cardinality='one'):
        def decorator(fn):
            self.rules.append(Rule(
                fn, inputs, output, cardinality
            ))
            return fn
        return decorator

    def available_rules_string(self):
        return ', '.join(
            str(rule.output) for rule in self.rules
        )

    def lookup_rule_for_clause(self, clause):
        for path in clause.lhs.subpaths():
            # TODO: this will almost certainly become a loop looking for
            # possible matches

            # first try finding a match direct on the root
            for rule in self.rules:
                if path == rule.output:
                    return [], rule

            # then try extracting the base type out and finding a prefix
            prefix, path = self.schema.base_type_and_property_of_path(path)

            for rule in self.rules:
                if path == rule.output:
                    return prefix, rule

        raise IndexError(
            '{path} not found in available rules: {rules}'.format(
                path=path,
                rules=self.available_rules_string(),
            )
        )

    def query(self, query):
        query = QueryPlan(self, query)

        return query.execute()

from .clause import Clause


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
                # Right now, this assumes that if value is a list, it is a
                # subquery like [{'x>': 1}] and so makes a recursive call
                self.extend(value[0], prefix=prefix+key+'.')
            else:
                self.append(Clause(prefix+key, value))

    def append(self, clause):
        if clause.lhs not in self.clause_map:
            self.clauses.append(clause)
            self.clause_map[clause.lhs] = clause
        else:
            self.clause_map[clause.lhs].merge(clause)

        return self.clause_map[clause.lhs]

    def subquery(self, root):
        subquery = Query({})
        for clause in self:
            if clause.rhs is None:
                continue

            if str(clause.lhs).find(root) == 0:
                new_clause = clause.copy()
                new_clause.lhs = new_clause.lhs.subpath(root)
                subquery.append(new_clause)

        return subquery

    def __len__(self):
        return len(self.clauses)

    def __iter__(self):
        return iter(self.clauses)

    def __getitem__(self, index):
        return self.clauses[index]

    def __str__(self):
        return '[\n{0!s}]'.format(''.join(
            '  ' + str(clause) + '\n' for clause in self.clauses
        ))

    def __repr__(self):
        return '<Query {}>'.format(str(self))

from .path import Path
from .relation import Relation


class Var(object):
    @classmethod
    def __repr__(cls):
        return cls.__name__


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
            if str(lhs)[-2:] == '==':
                return Path(lhs[:-2]), TempVar(), Relation('==', rhs)
            elif str(lhs)[-2:] == '!=':
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
            self.relation = self.relation.merge(other.relation)
        else:
            self.relation = self.relation or other.relation

        if isinstance(self.rhs, TempVar):
            self.rhs = other.rhs
        else:
            if not isinstance(other.rhs, TempVar):
                raise ValueError(
                    'these two clauses can not both be present in the query:'
                    '{self}, {other}'.format(
                        self=repr(self), other=repr(other),
                    )
                )

    def convert_to_constraint(self):
        """ converts self from a ground clause with a value to an unground
        clause with a == relation """
        self.relation = Relation('==', self.rhs)
        self.rhs = TempVar()

    def copy(self):
        new = Clause('_', None)
        new.lhs = self.lhs
        new.rhs = self.rhs
        new.value = self.value
        new.relation = self.relation
        return new

    def __str__(self):
        return '{lhs} {rhs}'.format(**self.__dict__)

    def __repr__(self):
        if self.relation:
            return '<Clause {lhs} {relation} {rhs})>'.format(
                **self.__dict__
            )
        else:
            return '<Clause {lhs} {rhs})>'.format(
                **self.__dict__
            )

    def __eq__(self, other):
        if self.lhs != other.lhs:
            return False

        if isinstance(self.rhs, Var):
            # I truly don't want to do isinstance here, the types need to
            # match
            if self.rhs.__class__ != other.rhs.__class__:
                return False
        else:
            if self.rhs != other.rhs:
                return False

        if self.relation != other.relation:
            return False

        return True

    def __ne__(self, other):
        return not self == other

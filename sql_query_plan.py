import six

class mysql_col(str):
    pass


def parse_comma_seperated_set(input):
    if isinstance(input, six.string_types):
        return set(map(str.strip, input.split(',')))
    else:
        return set(input)


class SQLQuery(object):
    def __init__(self, tables, selects, where):
        self.tables = parse_comma_seperated_set(tables)
        self.selects = parse_comma_seperated_set(selects)
        self.where = where.copy()

        self.flatten()

    def _assert_flattenable(self):
        """ ensure that the query is flattenable

        flatten currently doesnt handle many common types of queries
        which is why we need to check manually
        """

        if any(' ' in table for table in self.tables):
            raise ValueError('no table names can have aliases')
        if not all('.' in select for select in self.selects):
            raise ValueError('all selects must be of form table.column')
        if not all('.' in key for key in self.where.keys()):
            raise ValueError('all left hand sides of where clauses must '
                             'be of form table.column')

    def _assert_no_overlapping_where(self, where):
        overlap = set(self.where.keys()).intersection(where.keys())
        if overlap:
            raise ValueError('where clauses had overlap: {overlap}'.format(
                overlap=', '.join(map(str, overlap))
            ))

    def flatten(self):
        """ merge any SQLQuery objects on the rhs of a where clause
        into self. """

        self._assert_flattenable()

        for k, v in self.where.copy().items():
            if isinstance(v, SQLQuery):
                v._assert_flattenable()

                self.tables.update(v.tables)

                self._assert_no_overlapping_where(v.where)

                self.where.update(v.where)
                if len(v.selects) != 1:
                    raise ValueError('SQLQuery merging is only possible when the '
                                     'embedded query has one select')
                self.where[k] = mysql_col(list(v.selects)[0])

        self.cleanup()

    def cleanup(self):
        """ remove clauses like 'users.id': mysql_col('users.id') """

        for k, v in self.where.copy().items():
            if isinstance(v, mysql_col):
                if k == v:
                    del self.where[k]

    def __call__(self):
        raise NotImplemented()

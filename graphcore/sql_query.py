import six
import sql_query_dict

from .equality_mixin import EqualityMixin, HashMixin


class mysql_col(str):
    pass


def parse_comma_seperated_set(input):
    if isinstance(input, six.string_types):
        return set(map(str.strip, input.split(',')))
    else:
        return set(input)


class SQLQuery(HashMixin, EqualityMixin):

    def __init__(self, tables, selects, where,
                 limit=None, one_column=False, first=False,
                 input_mapping=None):
        """
        tables: ['table_name_1', 'table_name_2', ...] or
                'table_name_1, table_name_2, ...'
        selects: {'table.column', ...} or
                 'table.column, table.column, ...'
        where: {
            'table_name.column': 123,
            'table_name.column2>': 10,
            ...
        }
        input_mapping: {
            'kwargs_name': 'table_name.column',
            'kwargs_name': 'table_name.column!=',
            ...
        }
            input_mapping is used to map variables passed in to the
            __call__ into where clauses

        one_column: bool
            if one_column is True, only a single value will be returned
            for each row

        first: bool
            if first is True, only returns the first result
        """

        self.tables = parse_comma_seperated_set(tables)
        self.selects = parse_comma_seperated_set(selects)
        self.where = where.copy()
        self.limit = limit
        self.one_column = one_column
        self.first = first
        if input_mapping:
            self.input_mapping = input_mapping.copy()
        else:
            self.input_mapping = {}

    @property
    def __name__(self):
        return repr(self)

    def __repr__(self):
        return (
            '<SQLQuery tables:{tables}; selects:{selects}; where:{where} '
            'input_mapping:{input_mapping}; limit:{limit}; '
            'one_column:{one_column}; first:{first}>'
        ).format(
            tables=', '.join(self.tables),
            selects=', '.join(self.selects),
            where=self.where,
            input_mapping=self.input_mapping,
            limit=self.limit,
            one_column=self.one_column,
            first=self.first,
        )

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

    def _assert_no_overlapping_input_mapping(self, input_mapping):
        column_overlap = set(self.input_mapping.values()).intersection(
            input_mapping.values()
        )
        if column_overlap:
            raise ValueError(
                'input_mapping has column overlap: {column_overlap}'.format(
                    column_overlap=', '.join(map(str, column_overlap))
                )
            )

        kwargs_overlap = set(self.input_mapping.keys()).intersection(
            input_mapping.keys()
        )
        if kwargs_overlap:
            raise ValueError(
                'input_mapping has kwargs overlap: {kwargs_overlap}'.format(
                    kwargs_overlap=', '.join(map(str, kwargs_overlap))
                )
            )

    def flatten(self):
        """ merge any SQLQuery objects on the rhs of a where clause
        into self. """

        self._assert_flattenable()

        for k, v in self.where.copy().items():
            if isinstance(v, SQLQuery):
                v._assert_flattenable()

                self.tables.update(v.tables)

                self._assert_no_overlapping_where(v.where)
                self._assert_no_overlapping_input_mapping(v.input_mapping)

                self.where.update(v.where)
                if len(v.selects) != 1:
                    raise ValueError('SQLQuery merging is only possible when '
                                     'the embedded query has one select')
                self.where[k] = mysql_col(list(v.selects)[0])

        self.cleanup()

    def cleanup(self):
        """ remove clauses like 'users.id': mysql_col('users.id') """

        for k, v in self.where.copy().items():
            if isinstance(v, mysql_col):
                if k == v:
                    del self.where[k]

    def __add__(self, other):
        where = {}
        where.update(self.where)
        where.update(other.where)

        input_mapping = {}
        input_mapping.update(self.input_mapping)
        input_mapping.update(other.input_mapping)

        return SQLQuery(
            self.tables.union(other.tables),
            self.selects.union(other.selects),
            where,
            input_mapping=input_mapping,
        )

    def __call__(self, **kwargs):
        if set(self.input_mapping.keys()) != set(kwargs.keys()):
            raise ValueError('input mapping keys != kwargs keys')

        # compose where query
        where = self.where.copy()
        for k, v in kwargs.items():
            where[self.input_mapping[k]] = v

        sql, vals = sql_query_dict.select(
            self.tables, self.selects, where, limit=self.limit
        )

        ret = self.driver(sql, vals)

        if self.one_column:
            ret = [row[0] for row in ret]

        if self.first:
            ret = ret[0]

        return ret

    def driver(self, sql, vals):
        raise NotImplementedError()

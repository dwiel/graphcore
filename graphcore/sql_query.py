import six
import sql_query_dict

from .equality_mixin import EqualityMixin, HashMixin
from .rule import Cardinality
from .call_graph import Node


def parse_comma_seperated_set(input):
    return set(parse_comma_seperated_list(input))


def parse_comma_seperated_list(input):
    if isinstance(input, six.string_types):
        return list(map(str.strip, input.split(',')))
    else:
        return input


class SQLQuery(HashMixin, EqualityMixin):

    def __init__(self, tables, selects, where,
                 limit=None, one_column=False, first=False,
                 input_mapping=None, engine=None, param_style='%s'):
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

        engine: object
            an engine can be anything which acts like a sqlalchemy engine.
            primarily it needs to implement the following interface:

                engine.connect().execute(SQL, vals)

        param_style: str
            the style the engine expects parameters to take.  MySQL expects
            %s and sqlite expects ?
        """

        self.tables = parse_comma_seperated_set(tables)
        self.selects = parse_comma_seperated_list(selects)
        self.where = where.copy()
        self.limit = limit
        self.one_column = one_column
        self.first = first
        if input_mapping:
            self.input_mapping = input_mapping.copy()
        else:
            self.input_mapping = {}
        self.engine = engine
        self.param_style = param_style

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

    def copy(self):
        return self.__class__(
            set(self.tables), list(self.selects), dict(self.where),
            limit=self.limit, one_column=self.one_column, first=self.first,
            input_mapping=dict(self.input_mapping),
            engine=self.engine,
            param_style=self.param_style,
        )

    def _assert_flattenable(self):
        """ ensure that the query is flattenable

        flatten currently doesnt handle many common types of queries
        which is why we need to check manually
        """

        for table in self.tables:
            if ' ' in table:
                raise ValueError(
                    'no table names can have aliases, found {}'.format(table)
                )

        for select in self.selects:
            if '.' not in select:
                raise ValueError((
                    'all selects must be of form table.column,'
                    'found {}'
                ).format(select))

        for key in self.where.keys():
            if '.' not in key:
                raise ValueError((
                    'all left hand sides of where clauses must '
                    'be of form table.column, found {}'
                ).format(key))

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

                self.where.update(v.where)
                if len(v.selects) != 1:
                    raise ValueError((
                        'SQLQuery merging is only possible when '
                        'the embedded query has one select.  has: {}'
                    ).format(', '.join(v.selects)))
                self.where[k] = sql_query_dict.mysql_col(v.selects[0])

                # we just did a join, so definitely not just the first
                self.first = False

        self.cleanup()

    def cleanup(self):
        """ remove clauses like 'users.id': mysql_col('users.id') """

        for k, v in self.where.copy().items():
            if isinstance(v, sql_query_dict.mysql_col):
                if k == v:
                    del self.where[k]

    def __add__(self, other):
        self._assert_no_overlapping_input_mapping(other.input_mapping)

        where = {}
        where.update(self.where)
        where.update(other.where)

        input_mapping = {}
        input_mapping.update(self.input_mapping)
        input_mapping.update(other.input_mapping)

        # can't merge sql queries backed by different databases
        assert self.engine == other.engine

        return self.__class__(
            self.tables.union(other.tables),
            self.selects + other.selects,
            where,
            input_mapping=input_mapping,
            engine=self.engine,
            param_style=self.param_style,
        )

    def __call__(self, **kwargs):
        if set(self.input_mapping.keys()) != set(kwargs.keys()):
            raise ValueError('input mapping keys {} != kwargs keys {}'.format(
                self.input_mapping.keys(), kwargs.keys()
            ))

        # compose where query
        where = self.where.copy()
        for k, v in kwargs.items():
            where[self.input_mapping[k]] = v

        sql, vals = sql_query_dict.select(
            self.tables, self.selects, where, limit=self.limit,
            param_style=self.param_style
        )

        ret = self.driver(sql, vals)

        if self.one_column:
            ret = [row[0] for row in ret]

        if self.first:
            ret = ret[0]

        return ret

    def driver(self, sql, vals):
        if self.engine is None:
            raise ValueError('can not execute SQLQueries with no engine')

        return self.engine.execute(sql, vals).fetchall()

    @staticmethod
    def merge_parent_child(child, parent):
        """ NOTE: child and parent are switched here, it makes more sense """
        parent.function._assert_flattenable()
        child.function._assert_flattenable()

        function = parent.function.copy()
        for k, v in function.input_mapping.items():
            child_function = child.function.copy()

            # simply merge these parts of the SQLQuery
            function.tables.update(child_function.tables)
            function.where.update(child_function.where)
            function.selects.extend(child_function.selects)

            # join where clause and selects
            # the connecting path is the path which is set by the child and
            # read by the parent
            connecting_path = parent.input_path_by_property(k)
            # lookup the order that this path occurrs in the outputs so we can
            # match it up with the correct select
            i = child.outgoing_paths.index(connecting_path)

            # join in the where clause
            function.where[v] = sql_query_dict.mysql_col(
                child_function.selects[i]
            )

        # remove unnecessary complexity
        function.cleanup()

        # TODO: assumes that all inputs were from SQLQuery objects
        function.input_mapping = child.function.input_mapping

        # even if there is just one column, this also works so long as
        # Cardinality.many
        function.one_column = False
        function.first = False

        inputs = child.incoming_paths
        outputs = parent.outgoing_paths + child.outgoing_paths

        relations = parent.relations + child.relations

        return Node(
            None, inputs, outputs, function, Cardinality.many, relations
        )

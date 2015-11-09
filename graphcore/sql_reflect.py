import sqlalchemy
import inflect

from .sql_query import SQLQuery

_pluralizer = inflect.engine()


def _table_to_type(table):
    """ given a table name return the graphcore type name """
    if table[-1] == 's':
        return table[:-1]
    else:
        return table


def _column_to_property(column):
    """ assumes the column name has _id postfix """
    return column[:-3]


class SQLReflector(object):

    def __init__(self, graphcore, engine, sql_query_class=SQLQuery):
        """ add rules to graphcore instance based on schema found in SQL db.

        graphcore: Graphcore instance
        engine: sqlalchemy.engine instance

        assumes all tables have a primary key id
        """
        self.graphcore = graphcore
        self.metadata = self._metadata(engine)
        self.sql_query_class = sql_query_class

        for table in self.metadata.tables.keys():
            self._sql_reflect_table(table)

    def _has_one(self, table, column_name):
        type_name = _table_to_type(table)
        property_name = _column_to_property(column_name)

        self.graphcore.property_type(
            type_name, property_name, property_name
        )

        self.graphcore.register_rule(
            ['{}.id'.format(type_name)],
            '{}.{}.id'.format(type_name, property_name),
            function=self._sql_query(table, column_name),
        )

        # backref
        self.graphcore.property_type(
            property_name, _pluralizer.plural(type_name), type_name
        )
        self.graphcore.register_rule(
            ['{}.id'.format(property_name)],
            '{}.{}.id'.format(property_name, _pluralizer.plural(type_name)),
            function=self.sql_query_class(
                [table], '{}.id'.format(table), {},
                input_mapping={
                    'id': '{}.{}'.format(table, column_name),
                }, one_column=True,
            ),
            cardinality='many'
        )

    def _property(self, table, column_name):
        type_name = _table_to_type(table)

        return self.graphcore.register_rule(
            ['{}.id'.format(type_name)],
            '{}.{}'.format(type_name, column_name),
            function=self._sql_query(table, column_name),
        )

    def _sql_query(self, table, column):
        return self.sql_query_class(
            [table], '{}.{}'.format(table, column), {},
            input_mapping={
                'id': '{}.id'.format(table),
            }, one_column=True, first=True
        )

    def sql_reflect_column(self, table, column_name):
        if column_name[-3:] == '_id':
            self._has_one(table, column_name)
        else:
            self._property(table, column_name)

    def _sql_reflect_table(self, table):
        columns = self.metadata.tables[table].columns

        for column in columns:
            if column.name == 'id':
                continue

            self.sql_reflect_column(table, column.name)

    def _metadata(self, engine):
        metadata = sqlalchemy.schema.MetaData(bind=engine)
        metadata.reflect()
        return metadata

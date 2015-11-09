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


def _has_one(graphcore, table, column_name):
    type_name = _table_to_type(table)
    property_name = _column_to_property(column_name)

    graphcore.property_type(
        type_name, property_name, property_name
    )

    graphcore.register_rule(
        ['{}.id'.format(type_name)],
        '{}.{}.id'.format(type_name, property_name),
        function=_sql_query(table, column_name),
    )

    # backref
    graphcore.property_type(
        property_name, _pluralizer.plural(type_name), type_name
    )
    graphcore.register_rule(
        ['{}.id'.format(property_name)],
        '{}.{}.id'.format(property_name, _pluralizer.plural(type_name)),
        function=SQLQuery(
            [table], '{}.id'.format(table), {},
            input_mapping={
                'id': '{}.{}'.format(table, column_name),
            }, one_column=True,
        ),
        cardinality='many'
    )


def _property(graphcore, table, column_name):
    type_name = _table_to_type(table)

    return graphcore.register_rule(
        ['{}.id'.format(type_name)],
        '{}.{}'.format(type_name, column_name),
        function=_sql_query(table, column_name),
    )


def _sql_query(table, column):
    return SQLQuery(
        [table], '{}.{}'.format(table, column), {},
        input_mapping={
            'id': '{}.id'.format(table),
        }, one_column=True, first=True
    )


def sql_reflect_column(graphcore, table, column_name):
    if column_name[-3:] == '_id':
        _has_one(graphcore, table, column_name)
    else:
        _property(graphcore, table, column_name)


def _sql_reflect_table(graphcore, metadata, table):
    columns = metadata.tables[table].columns

    for column in columns:
        if column.name == 'id':
            continue

        sql_reflect_column(graphcore, table, column.name)


def _metadata(engine):
    metadata = sqlalchemy.schema.MetaData(bind=engine)
    metadata.reflect()
    return metadata


def sql_reflect(graphcore, engine):
    """ add rules to graphcore instance based on schema found in SQL db.

    graphcore: Graphcore instance
    engine: sqlalchemy.engine instance

    assumes all tables have a primary key id
    """
    metadata = _metadata(engine)

    for table in metadata.tables.keys():
        _sql_reflect_table(graphcore, metadata, table)

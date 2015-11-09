import sqlalchemy

from .sql_query import SQLQuery


def _singular_table(table):
    if table[-1] == 's':
        return table[:-1]
    else:
        return table


def sql_reflect_column(graphcore, table, column_name):
    plural_table = table
    singular_table = _singular_table(table)

    return graphcore.register_rule(
        ['{}.id'.format(singular_table)],
        '{}.{}'.format(singular_table, column_name),
        function=SQLQuery(
            [plural_table], '{}.{}'.format(plural_table, column_name), {},
            input_mapping={
                'id': '{}.id'.format(plural_table),
            }, one_column=True, first=True
        )
    )


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
    """
    metadata = _metadata(engine)

    for table in metadata.tables.keys():
        _sql_reflect_table(graphcore, metadata, table)

import sqlalchemy

from .sql_query import SQLQuery


def sql_reflect_column(graphcore, table, column_name):
    full_column_name = '{table}.{column_name}'.format(
        table=table, column_name=column_name
    )
    full_id_name = '{table}.id'.format(table=table)

    return graphcore.register_rule(
        [full_id_name],
        full_column_name,
        function=SQLQuery(
            [table], full_column_name, {},
            input_mapping={
                'id': full_id_name
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
    metadata = _metadata(engine)

    for table in metadata.tables.keys():
        _sql_reflect_table(graphcore, metadata, table)

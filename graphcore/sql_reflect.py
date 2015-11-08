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


def sql_reflect_table(graphcore, engine, table):
    columns = engine.execute('describe {table}'.format(table=table))
    for column in columns:
        column_name = column[0]
        sql_reflect_column(graphcore, table, column_name)


def sql_reflect(graphcore, engine):
    tables = engine.execute('show tables')
    for table in tables:
        sql_reflect_table(graphcore, engine, table)

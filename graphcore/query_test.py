from .query import Query


def test_contains():
    # ensure that parsing a query with a contains operator works
    Query({
        'x.id|=': [1, 2, 3],
    })

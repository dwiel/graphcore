[![Build Status](https://travis-ci.org/dwiel/graphcore.svg?branch=master)](https://travis-ci.org/dwiel/graphcore)

# Graphcore

Graphcore is a python library which allows you to query a graph
structure with a query language similar to MQL, Falcor or GraphQL.

The graph structure can be defined by python functions or SQL
relations.  Graphcore will find an optimal way to organize the call
graph so as to group SQL queries together.

### Comparison with Falcor

In Falcor, your router must resolve each path to a function which
optionally takes parameters describing the path.  With Graphcore, your
function can depend on other parts of the graph.  This allows you to
describe the dependencies between all of the functions / paths and
allow graphcore

### Example

Here is an example of a query and the returned data structure:

```python
ret = testgraphcore.query({
    'user.id': 1,
    'user.books.name?': None,
})
assert ret == [
    {'user.books.name': 'The Giver'},
    {'user.books.name': 'REAMDE'},
    {'user.books.name': 'The Diamond Age'},
]
```

Here is the setup code used to make that query possible:

```python
import graphcore

testgraphcore = graphcore.Graphcore()


@testgraphcore.rule(['user.name'], 'user.abbreviation')
def user_abbreviation(name):
    return ''.join(part[0].upper() for part in name.split(' '))


USER_ID_TO_USER_NAME = {
    1: 'John Smith',
}


@testgraphcore.rule(['user.id'], 'user.name')
def user_name(id):
    return USER_ID_TO_USER_NAME[id]


testgraphcore.has_many('user', 'books', 'book')


@testgraphcore.rule(['user.id'], 'user.books.id', cardinality='many')
def user_books_id(id):
    # this would normally come out of a db
    return [1, 2, 3]


BOOK_ID_TO_BOOK_NAME = {
    1: 'The Giver',
    2: 'REAMDE',
    3: 'The Diamond Age',
}


@testgraphcore.rule(['book.id'], 'book.name')
def book_name(id):
    return BOOK_ID_TO_BOOK_NAME[id]

```

### More topics

- [AST](docs/ast.md)
- [TODO](docs/todo.md)

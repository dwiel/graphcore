# Graphcore
falcor + graphql + axpress

### Example

Here is an example of a query and the returned data structure:

```python
ret = testgraphcore.query({
    'user.id': 1,
    'user.books.id?': None,
})
assert ret == [
    {'user.books.id': 1},
    {'user.books.id': 2},
    {'user.books.id': 3},
]
```

Here is the setup code used to make that query possible:

```python
import graphcore

testgraphcore = graphcore.Graphcore()


@testgraphcore.rule(['user.name'], 'user.abbreviation')
def user_name_to_abbreviation(name):
    return ''.join(part[0].upper() for part in name.split(' '))


USER_ID_TO_USER_NAME = {
    1: 'John Smith',
}


@testgraphcore.rule(['user.id'], 'user.name')
def user_id_to_user_name(id):
    return USER_ID_TO_USER_NAME[id]


testgraphcore.has_many('user', 'books', 'book')


@testgraphcore.rule(['user.id'], 'user.books.id')
def user_id_to_books_id(id):
    # this would normally come out of a db
    return [1, 2, 3]


```

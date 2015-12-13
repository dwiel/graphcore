[![Build Status](https://travis-ci.org/dwiel/graphcore.svg?branch=master)](https://travis-ci.org/dwiel/graphcore) [![Coverage Status](https://coveralls.io/repos/dwiel/graphcore/badge.svg?branch=master&service=github)](https://coveralls.io/github/dwiel/graphcore?branch=master) [![Documentation Status](https://readthedocs.org/projects/graphcore/badge/?version=latest)](http://graphcore.readthedocs.org/en/latest/?badge=latest)

# Graphcore

[![Join the chat at https://gitter.im/dwiel/graphcore](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/dwiel/graphcore?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Graphcore is a python library which allows you to query a computational graph
structure with a query language similar to MQL, Falcor or GraphQL.

At the moment, the graph structure can be defined by python functions or SQL
relations.

### Example

Here is an example of a query and the returned data structure:

```python
ret = gc.query({
    'user.id': 1,
    'user.books.name?': None,
})
assert ret == [
    {'user.books.name': 'The Giver'},
    {'user.books.name': 'REAMDE'},
    {'user.books.name': 'The Diamond Age'},
]
```

Here is an example of setting up a graphcore environment with both rules
reflected from a SQL database as well as 3rd party libraries.

```python
import graphcore

# setup a graphcore environment where rules and a schema can be stored
gc = graphcore.Graphcore()

# reflect on the sql database using db_engine and SampleSQLQuery which
# inherits from the provided graphore.sql_query.SQLQuery class.
graphcore.sql_reflect.SQLReflector(gc, db_engine, SampleSQLQuery)


# defines a rule which takes as input user.email, and returns the user's
# gravatar email.  In this case it is a one to one mapping
@gc.rule(['user.email'], 'user.gravatar.email')
def user_gravatar_email(email):
    return email


# given a gravatar email, return a url to their profile picture
@gc.rule(['gravatar.email'], 'gravatar.url')
def gravatar_url(email):
    import gravatar
    return gravatar.lookup_url(email)


# user's location's zipcode is the same as the user
@gc.rule(['user.zipcode'], 'user.location.zipcode')
def user_location_zipcode(zipcode):
    return zipcode


# given a location's zipcode, return the current temperature there
@gc.rule(['location.zipcode'], 'location.current_temperature')
def location_current_temperature(zipcode):
    return weather_lib.current_temperature_by_zipcode(zipcode)
```

And now after that setup, here is a query you could make

```
gc.query({
    'user.books': [{
        'name?': None,
    }],
    'user.gravatar.url?': None,
    'user.location.current_temperature<': 30,
})
```

This query will find users whose location is currently under 30 degrees, and
return you a URL to their gravatar profile and a list of the names of the
books they have.


### Comparison with Falcor

In Falcor, your router must resolve each path to a function which optionally
takes parameters describing the path, but that is it.  In falcor, your routes
can not know anything else about other parts of the virtual json object.  With
Graphcore, your function can depend on other parts of the graph.  This allows
you to describe the dependencies between all of the functions / paths and allow
graphcore to find an optimal way to glue your backend together.  There will
also be hooks which allow you to give hints or make specific changes to the AST
and control how the query is executed if you need to.

### More topics

- [AST](docs/ast.md)

[![Build Status](https://travis-ci.org/dwiel/graphcore.svg?branch=master)](https://travis-ci.org/dwiel/graphcore) [![Coverage Status](https://coveralls.io/repos/dwiel/graphcore/badge.svg?branch=master&service=github)](https://coveralls.io/github/dwiel/graphcore?branch=master) [![Documentation Status](https://readthedocs.org/projects/graphcore/badge/?version=latest)](http://graphcore.readthedocs.org/en/latest/?badge=latest)

Hop onto gitter to chat about graphcore: [![Join the chat at https://gitter.im/dwiel/graphcore](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/dwiel/graphcore?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

# Graphcore

Graphcore is a python library which allows you to query a computational graph
structure with a query language similar to MQL, Falcor or GraphQL.

At the moment, the graph structure can be defined by python functions or SQL
relations.  This allows you to write one query which is backed by multiple SQL
databases, NoSQL databases, internal services and 3rd party services.
Graphcore's job is to determine which database or python functions to call and how to glue them
together to satisfy your query.

### Example Queries

All of the following queries assume that you have already set up your graphcore
environment and are now ready to query it.

Return user.id 1's name:

```python
ret = graphcore.query({
    'user.id': 1,
    'user.name?': None,
})
assert ret == [
    {'user.name': 'John'},
]
```

The `?` at the end of `user.name?` signifies that you want to get a user's name
in the output.  This is similar to the `SELECT users.name ...` part of a SQL
query.  `'user.id': 1` signifies that you want to restrict the results to user
objects whose id is 1.  This is similar to the where clause in SQL query.

#### Joins

In the following query we get the name of all books a user has:

```python
ret = graphcore.query({
    'user.id': 1,
    'user.books.name?': None,
})
assert ret == [
    {'user.books.name': 'The Giver'},
    {'user.books.name': 'REAMDE'},
    {'user.books.name': 'The Diamond Age'},
]
```

Note that the input query shape and the output shape is the same.

Sometimes with longer queries it is nice split it up heirarchically:

```python
graphcore.query({
    'user.id': 1,
    'user.books': [{
        'name?': None,
    }],
})


assert ret == [{
    'user.books': [{
        'name': 'The Giver',
    }, {
        'name': 'REAMDE',
    }, {
        'name': 'The Diamond Age',
    }],
}]
```

Here is the same query, but no restricting to only books by Neal Stephenson:

```python
graphcore.query({
    'user.id': 1,
    'user.books': [{
        'name?': None,
        'author': 'Neal Stephenson',
    }],
})

assert ret == [{
    'user.books': [{
        'name': 'REAMDE',
    }, {
        'name': 'The Diamond Age',
    }],
}]
```

### Relations

Relations can be expressed by adding the relation to the end of the key:

```python
graphcore.query({
    'user.id': 1,
    'user.books': [{
        'name?': None,
        'pages<': 1000,
    }],
})

assert ret == [{
    'user.books': [{
        'name': 'The Giver',
    }, {
        'name': 'The Diamond Age',
    }],
}]
```

Allowed relations are `>`, `<`, `>=`, `<=`, `!=` and `|=`.  `|=` is an `in`
operator:

```python
graphcore.query({
    'user.id': 1,
    'user.books': [{
        'name?': None,
        'author|=': ('Neal Stephenson', 'Dr. Suess'),
    }],
})

assert ret == [{
    'user.books': [{
        'name': 'REAMDE',
    }, {
        'name': 'The Diamond Age',
    }, {
        'name': 'The Cat in The Hat',
    }],
}]
```

### Example Setup

In the previous example queries, a Graphcore instance was already expected to
be set up.  A graphcore instance stores the set of rules that are available to
the query.  There are multiple ways to set one up.  You can reflect rules from
a SQL database, add custom SQL query rules or write python functions.  You can
also reflect all of the methods in a python package into graphcore.  I don't
yet have any examples of this.  

Graphcore rules map from a set of input paths to an output path.  For example,
this rule maps from a gravatar email to a gravatar url.  This function will be
called anytime a query filters on or expects a gravatar.url output.

```python
# given a gravatar email, return a url to their profile picture
@gc.rule(['gravatar.email'], 'gravatar.url')
def gravatar_url(email):
    from gravatar import Gravatar
    return Gravatar(email).thumb
```

Here is a more complete example of setting up a graphcore environment with both
rules reflected from a SQL database as well as 3rd party libraries.

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
    from gravatar import Gravatar
    return Gravatar(email).thumb


# user's location's zipcode is the same as the user
@gc.rule(['user.zipcode'], 'user.location.zipcode')
def user_location_zipcode(zipcode):
    return zipcode


# given a location's zipcode, return the current temperature there
@gc.rule(['location.zipcode'], 'location.current_temperature')
def location_current_temperature(zipcode):
    return weather_lib.current_temperature_by_zipcode(zipcode)
```

And now after that setup, here is an example query:

```python
gc.query({
    'user.books': [{
        'name?': None,
    }],
    'user.gravatar.url?': None,
    'user.location.current_temperature<': 30,
})
```

This query will find users in locations where the temperature is currently
under 30 degrees, and return you a URL to their gravatar profile and a list of
the names of the books they have.  This query will hit a SQL database and two
3rd party libraries.  If you decide that a user's books should no longer be
stored in a SQL database, your queries can remain the same.  The new graphcore
environment can be setup to map that relationship to a different database or
service instead.


### Comparison with Falcor

In Falcor, your router must resolve each path to a function which optionally
takes parameters describing the path, but that is it.  In falcor, your routes
can not know anything else about other parts of the virtual json object.  With
Graphcore, your function can depend on other parts of the graph.  This allows
you to describe the dependencies between all of the functions / paths and allow
graphcore to find an optimal way to glue your backend together.  There will
also be hooks which allow you to give hints or make specific changes to the AST
and control how the query is executed if you need to.

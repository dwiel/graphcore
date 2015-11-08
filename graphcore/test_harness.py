from . import graphcore

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


testgraphcore.property_type('user', 'books', 'book')


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


BOOK_ID_TO_AUTHOR_ID = {
    1: 'Louis Lowry',
    2: 'Neal Stephenson',
    3: 'Neal Stephenson',
}


@testgraphcore.rule(['book.id'], 'book.author.id')
def book_author_id(id):
    return BOOK_ID_TO_AUTHOR_ID[id]

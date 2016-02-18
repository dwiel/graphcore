def first_name(id):
    return 'Bob{}'.format(id)


def last_name(user_id):
    """ this function takes user_id as input instead of just id """
    return 'Jones{}'.format(user_id)


def age(user_id):
    return user_id + 30


def user_complex(id, thing, other_thing):
    return id + thing + other_thing


def book_ids(user_id):
    return [1, 2, 3]


def optionally_complex(id, const=1):
    """ graphcore wont map const as an input """
    return id + const


def book_with_user_name(first_name, book_id):
    return 'user: {}; book: {}'.format(first_name, book_id)


def profile(first_name, location__city):
    return '{first_name} lives in {location__city}'.format(
        first_name=first_name,
        location__city=location__city,
    )


def multi_id_thing(book_id, foo_id):
    return book_id + foo_id


def user_abc(user_name):
    return user_name

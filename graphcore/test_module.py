def first_name(id):
    return 'Bob{}'.format(id)


def last_name(user_id):
    """ this function takes user_id as input instead of just id """
    return 'Jones{}'.format(user_id)


def user_age(user_id):
    return user_id + 30


def user_complex(id, thing, other_thing):
    return id + thing + other_thing


def book_ids(user_id):
    return [1, 2, 3]

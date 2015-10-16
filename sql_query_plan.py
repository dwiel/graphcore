import six

class mysql_col(str):
    pass


def parse_comma_seperated_set(input):
    if isinstance(input, six.string_types):
        return set(map(str.strip, input.split(',')))
    else:
        return set(input)


class SQLQuery(object):
    def __init__(self, tables, selects, where):
        self.tables = parse_comma_seperated_set(tables)
        self.selects = parse_comma_seperated_set(selects)
        self.where = where

        self.flatten()

    def flatten(self):
        for k, v in list(self.where.copy().items()):
            if isinstance(v, SQLQuery):
                # this is definitely wrong, but its a start
                self.tables.update(v.tables)
                self.where.update(v.where)
                if len(v.selects) != 1:
                    raise ValueError('SQLQuery merging is only possible when the '
                                     'embedded query has one select')
                self.where[k] = mysql_col(list(v.selects)[0])

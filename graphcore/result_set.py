
class Result(object):

    def __init__(self, result=None):
        if isinstance(result, Result):
            self.result = result.result.copy()
        elif isinstance(result, dict):
            self.result = {}
            for k, v in result.items():
                self.set(k, v)
        else:
            self.result = {}

    def set(self, path, value):
        self.result[str(path)] = value

    def get(self, path):
        return self.result[str(path)]

    def to_json(self):
        return self.result

    def extract_json(self, paths):
        return {
            str(path): self.get(path) for path in paths
        }

    def __repr__(self):
        return '<Result {result}>'.format(result=repr(self.result))


class ResultSet(object):
    """ The ResultSet holds the state of the query as it is executed. """

    def __init__(self, init=None):
        # TODO handle more complex result set toplogies
        if isinstance(init, ResultSet):
            self.results = init.results.copy()
        elif isinstance(init, dict):
            self.results = {Result(init)}
        else:
            self.results = {Result()}

        print('d', self.results, init)

    def set(self, path, value):
        for result in self.results:
            result.set(path, value)

    def explode(self, existing_result, path, values):
        new_results = {
            Result(existing_result)
            for _ in range(len(values))
        }

        for result, value in zip(new_results, values):
            result.set(path, value)

        self.results.remove(existing_result)
        self.results.update(new_results)

    def to_json(self):
        return [
            result.to_json() for result in self.results
        ]

    def extract_json(self, paths):
        return [
            result.extract_json(paths) for result in self.results
        ]

    def __repr__(self):
        return '<ResultSet {str}>'.format(str=str(self))

    def __str__(self):
        return str(self.to_json())

    def __iter__(self):
        return iter(self.results)

    def copy(self):
        return ResultSet(self)

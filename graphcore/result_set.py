from .equality_mixin import EqualityMixin


class Result(EqualityMixin):

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

    def explode(self, path, values):
        new_results = [
            Result(self)
            for _ in range(len(values))
        ]

        for result, value in zip(new_results, values):
            result.set(path, value)

        return new_results

    def to_json(self):
        return self.result

    def extract_json(self, paths):
        return {
            str(path): self.get(path) for path in paths
        }

    def __repr__(self):
        return '<Result {result}>'.format(result=repr(self.result))


class ResultSet(EqualityMixin):
    """ The ResultSet holds the state of the query as it is executed. """

    def __init__(self, init=None):
        # TODO handle more complex result set toplogies
        if isinstance(init, ResultSet):
            self.results = init.results
        elif isinstance(init, dict):
            self.results = [Result(init)]
        elif isinstance(init, list):
            self.results = init
        else:
            self.results = []

    def set(self, path, value):
        for result in self.results:
            result.set(path, value)

    def to_json(self):
        return [
            result.to_json() for result in self.results
        ]

    def extract_json(self, paths):
        return [
            result.extract_json(paths) for result in self.results
        ]

    def filter(self, path, relation):
        self.results = [
            result for result in self.results
            if relation(result.get(path))
        ]

    def extend(self, results):
        self.results.extend(results)

    def __repr__(self):
        return '<ResultSet {str}>'.format(str=str(self))

    def __str__(self):
        return str(self.to_json())

    def __iter__(self):
        return iter(self.results)

import inspect


def input_mapping_decorator(function, input_mapping):
    def _input_mapping_decorator(**kwargs):
        new_kwargs = {
            input_mapping[k]: v for k, v in kwargs.items()
        }
        print('call', function, kwargs, new_kwargs)
        return function(**new_kwargs)

    _input_mapping_decorator.__name__ = function.__name__
    return _input_mapping_decorator


class ModuleReflector(object):

    def __init__(self, graphcore, module, type_name):
        """ add rules to graphcre instance based on functions found python module.
        """
        self.graphcore = graphcore
        self.module = module
        self.type_name = type_name

        self._reflect()

    def _reflect(self):
        for name, value in self.module.__dict__.items():
            if callable(value):
                arg_names, _, __, ___ = inspect.getargspec(value)

                print name, arg_names

                input_paths = [
                    self._input_name(arg_name) for arg_name in arg_names
                ]

                input_mapping = {
                    self._canonical_property_name(arg_name): arg_name
                    for arg_name in arg_names
                }

                print(input_mapping)

                self.graphcore.register_rule(
                    input_paths,
                    self._output_name(name),
                    function=input_mapping_decorator(value, input_mapping)
                )

    def _canonical_property_name(self, arg_name):
        """ given the name of an argument to a function, return
        the name of the graphcore property it is describing.

        user_id -> id
        id -> id
        name -> name
        """
        if arg_name.find(self.type_name) == 0:
            property_name = arg_name[len(self.type_name):]

            # remove leading underscore if it is there
            if property_name[0] == '_':
                property_name = property_name[1:]

            return property_name
        else:
            return arg_name

    def _input_name(self, arg_name):
        """ given the name of an argument to a function, return
        the corresponding path """

        return '{type_name}.{property_name}'.format(
            type_name=self.type_name,
            property_name=self._canonical_property_name(arg_name),
        )

    def _output_name(self, function_name):
        return '{type_name}.{function_name}'.format(
            type_name=self.type_name,
            function_name=self._canonical_property_name(function_name),
        )

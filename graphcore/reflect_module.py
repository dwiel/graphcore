import inspect

from .path import Path


def input_mapping_decorator(function, input_mapping):
    def _input_mapping_decorator(**kwargs):
        try:
            new_kwargs = {
                input_mapping[k]: v for k, v in kwargs.items()
            }
        except KeyError as e:
            raise KeyError((
                '{}; kwargs: {}; input_mapping: {}; ' +
                'for function: {}').format(
                    str(e), kwargs, input_mapping, function
            ))

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
            if inspect.isfunction(value):
                arg_names, _, __, defaults = inspect.getargspec(value)

                # dont map arguments with defaults to inputs
                if defaults:
                    arg_names = arg_names[:-len(defaults)]

                input_paths = [
                    self._input_name(arg_name) for arg_name in arg_names
                ]

                input_mapping = {
                    self._input_mapping_name(arg_name): arg_name
                    for arg_name in arg_names
                }

                self.graphcore.register_rule(
                    input_paths,
                    self._output_name(name),
                    function=input_mapping_decorator(value, input_mapping),
                    cardinality=self._cardinality(name),
                )

    def _input_mapping_name(self, arg_name):
        return Path(self._canonical_property_name(arg_name)).property

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
        elif arg_name[-4:] == '_ids':
            return arg_name[:-4] + '.' + arg_name[-3:-1]
        elif arg_name[-3:] == '_id':
            return arg_name[:-3] + '.' + arg_name[-2:]
        else:
            return arg_name

    def _cardinality(self, function_name):
        """ infer the cardinality of a function from its name """

        if function_name[-4:] == '_ids':
            return 'many'
        else:
            return 'one'

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

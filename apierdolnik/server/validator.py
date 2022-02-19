import inspect


class Validator:
    @staticmethod
    def validate(arg_name: str, arg_value: any, param: inspect.Parameter):
        if Validator._no_default_value(param) and arg_value is None:
            raise ValueError(f"Argument '{arg_name}' is required")

    @staticmethod
    def _no_default_value(param: inspect.Parameter):
        return param.default == inspect.Parameter.empty
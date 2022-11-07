import inspect


class Converter:
    @staticmethod
    def convert(arg_name: str, arg_value: any, param: inspect.Parameter):
        try:
            param_type = param.annotation
            if param_type not in (inspect.Parameter.empty, any):
                value = param_type(arg_value) if arg_value else param.default
            else:
                value = arg_value
            return value
        except ValueError:
            raise ValueError(
                f"Couldn't convert argument '{arg_name}' with value {arg_value} to {param.annotation.__name__}")
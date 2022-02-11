import inspect

from dataclasses import dataclass
from typing import Callable, Dict, Type
from itertools import zip_longest


@dataclass(frozen=True)
class EndpointParam:
    name: str
    type: Type
    is_required: bool
    default_value: any = None


required_sentinel = object()


class Endpoint:
    def __init__(self, func: Callable):
        self._func = func
        self._params = self._introspect_params()

    @property
    def func(self):
        return self._func

    @property
    def params(self):
        return self._params

    # TODO: change to list
    def _introspect_params(self) -> Dict[str, EndpointParam]:
        spec = inspect.getfullargspec(self._func)
        params = {}
        if spec.args and spec.defaults:
            for name, default_value in zip_longest(reversed(spec.args), reversed(spec.defaults),
                                                   fillvalue=required_sentinel):
                arg_type = spec.annotations[name]
                if default_value == required_sentinel:
                    param = EndpointParam(name=name, type=arg_type, is_required=True)
                else:
                    param = EndpointParam(name=name, type=arg_type, is_required=False, default_value=default_value)
                params[name] = param
        return params

    def __call__(self, *args, **kwargs):
        result = self._func(*args, **kwargs)
        match result:
            case response, http_code:
                return response, http_code
            case response:
                return response, 200

    def __repr__(self):
        return f"Endpoint('{self._func.__name__}')"


not_found_endpoint = Endpoint(lambda: (f'No such endpoint', 404))

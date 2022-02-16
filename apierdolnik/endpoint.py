import inspect

from typing import Callable, Dict


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

    def _introspect_params(self) -> Dict[str, inspect.Parameter]:
        sig = inspect.signature(self._func)
        for k, v in sig.parameters.items():
            print(k, v.kind, v.empty)
        return dict(sig.parameters)

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

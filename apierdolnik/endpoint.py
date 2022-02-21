import inspect

from typing import Callable, Dict

from response import Response


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
        return dict(sig.parameters)

    def __call__(self, *args, **kwargs) -> Response:
        result = self._func(*args, **kwargs)
        if isinstance(result, tuple):
            return Response(body=result[0], status_code=result[1])
        else:
            return Response(body=result, status_code=200)

    def __repr__(self):
        return f"Endpoint('{self._func.__name__}')"


not_found_endpoint = Endpoint(lambda: (f'No such endpoint', 404))

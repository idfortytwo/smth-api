from typing import Callable


class Endpoint:
    def __init__(self, func: Callable):
        self._func = func

    @property
    def func(self):
        return self._func

    def __call__(self, *args, **kwargs):
        result = self._func(*args, **kwargs)
        match result:
            case response, http_code:
                return response, http_code
            case response:
                return response, 200


not_found_endpoint = Endpoint(lambda: (f'No such endpoint', 404))


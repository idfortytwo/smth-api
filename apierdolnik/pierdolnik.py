import functools
from http.server import HTTPServer
from typing import NoReturn, List, Callable, Dict, Tuple

from endpoint import Endpoint
from server import RequestHandler


class Pierdolnik:
    def __init__(self, host='localhost', port=8080) -> None:
        self._host = host
        self._port = port
        self._routing_map: Dict[str, Tuple[List[str], Endpoint]] = {}

    def route(self, path: str, http_methods: List[str]):
        def decorator(func: Callable):
            endpoint = Endpoint(func)
            self._routing_map[path] = (http_methods, endpoint)

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def less_go(self) -> NoReturn:
        print(self._routing_map)

        RequestHandler.register_routes(self._routing_map)
        server = HTTPServer((self._host, self._port), RequestHandler)
        server.serve_forever()

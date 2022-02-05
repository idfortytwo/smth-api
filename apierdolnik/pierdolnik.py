import functools
from http.server import HTTPServer
from typing import NoReturn, List, Callable, Dict, Tuple

from server import RequestHandler


class Pierdolnik:
    def __init__(self, host='localhost', port=8080) -> None:
        self._host = host
        self._port = port
        self._routing_map: Dict[str, Tuple[List[str], Callable]] = {}

    def route(self, path: str, http_methods: List[str]):
        def decorator(endpoint: Callable):
            self._routing_map[path] = (http_methods, endpoint)

            @functools.wraps(endpoint)
            def wrapper(*args, **kwargs):
                return endpoint(*args, **kwargs)

            return wrapper

        return decorator

    def less_go(self) -> NoReturn:
        print(self._routing_map)

        RequestHandler.register_routes(self._routing_map)
        server = HTTPServer((self._host, self._port), RequestHandler)
        server.serve_forever()

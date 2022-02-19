import functools
import re

from http.server import HTTPServer
from typing import NoReturn, List, Callable, Dict, Tuple

from endpoint import Endpoint
from server.request_handler import RequestHandler


class Pierdolnik:
    def __init__(self, host='localhost', port=8080) -> None:
        self._host = host
        self._port = port
        self._routing_map: Dict[re.Pattern, Tuple[List[str], Endpoint]] = {}

    def route(self, path: str, http_methods: List[str]):
        pattern = self._path_to_regex(path)

        def decorator(func: Callable):
            endpoint = Endpoint(func)
            self._routing_map[pattern] = (http_methods, endpoint)

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def less_go(self) -> NoReturn:
        RequestHandler.register_routes(self._routing_map)
        server = HTTPServer((self._host, self._port), RequestHandler)
        server.serve_forever()

    @staticmethod
    def _path_to_regex(path: str) -> re.Pattern:
        regexed_path = re.sub(r":(\w+)", r"(?P<\1>[^/]+)", path) + '$'
        return re.compile(regexed_path)
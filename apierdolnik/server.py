import json
import re
import traceback

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Dict, Tuple, List

from endpoint import Endpoint, not_found_endpoint, EndpointParam


class RequestHandler(BaseHTTPRequestHandler):
    HTTP_CODES = [
        100, 101, 102, 103, 200, 201, 202, 203, 204, 205, 206, 207, 226, 300, 301, 302, 303, 304, 305, 306, 307, 308,
        400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 415, 416, 417, 418, 421, 422, 423, 424,
        425, 426, 428, 429, 431, 451, 500, 501, 502, 503, 504, 505, 506, 507, 508, 510, 511]

    @classmethod
    def register_routes(cls, routing_map: Dict):
        cls._routing_map: Dict[re.Pattern, Tuple[List[str], Endpoint]] = routing_map

    # overridding request handling
    def handle_one_request(self):
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(HTTPStatus.REQUEST_URI_TOO_LONG)
                return
            if not self.raw_requestline:
                self.close_connection = True
                return
            if not self.parse_request():
                return

            self._handle_request()
            self.wfile.flush()
        except TimeoutError as e:
            self.log_error("Request timed out: %r", e)
            self.close_connection = True
            return

    def _handle_request(self):
        path, args_str = self._split_path_and_args(self.path)

        endpoint, pos_args = self._get_endpoint_and_pos_params(path=path, http_method=self.command)

        query_args = {}
        if endpoint != not_found_endpoint and args_str:
            for arg in args_str.split('&'):
                k, v = arg.split('=')
                query_args[k] = v

        response, http_code = self._handle_endpoint(endpoint, {**pos_args, **query_args})
        response_json = json.dumps(response)
        self._send(response_json, http_code)

    def _get_endpoint_and_pos_params(self, path: str, http_method: str):
        for regex, (http_methods, endpoint) in self._routing_map.items():
            m = regex.match(path)
            if m and endpoint and http_method in http_methods:
                return endpoint, m.groupdict()

        return not_found_endpoint, {}

    @staticmethod
    def _split_path_and_args(url: str):
        query_index = url.rfind('?')
        query_pos = query_index if query_index != -1 else len(url)
        return url[:query_pos], url[query_pos + 1:]

    def _handle_endpoint(self, endpoint: Endpoint, args: Dict) -> Tuple[any, int]:
        try:
            validated_args = self._parse_args(args, endpoint.params)
            response, http_code = endpoint(**validated_args)
        except Exception as e:
            traceback.print_exc()
            return {'error_msg': str(e)}, 500

        if http_code not in self.HTTP_CODES:
            raise ValueError(f'Invalid response code {http_code} for endpoint {endpoint.func}')

        return response, http_code

    @staticmethod
    def _parse_args(args: Dict, params: Dict[str, EndpointParam]) -> Dict:
        parsed_args = {}
        for name, param in params.items():
            arg_value = args.get(name)

            if param.is_required and not arg_value:
                raise ValueError(f"Argument '{name}' is required")

            try:
                value = param.type(arg_value) if arg_value else param.default_value
            except ValueError:
                raise ValueError(f"Argument '{name}' should have type {param.type.__name__}")

            parsed_args[name] = value
        return parsed_args

    def _send(self, response_body: str, http_code: int):
        self.send_response(http_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(response_body, 'utf-8'))
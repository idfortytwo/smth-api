import inspect
import json
import re
import traceback
import cgi

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Dict, Tuple, List

from endpoint import Endpoint, not_found_endpoint


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
        url, query_str = self._split_url_and_query(self.path)

        endpoint, positional_params = self._get_endpoint_and_positional_params(url=url, http_method=self.command)
        named_params = self._extract_named_params(query_str)

        response, http_code = self._handle_endpoint(endpoint, {**positional_params, **named_params})
        response_json = json.dumps(response)
        self._send(response_json, http_code)

    def _extract_named_params(self, query_str: str):
        content_type = self.headers['Content-Type']
        if content_type:
            if content_type == 'application/x-www-form-urlencoded':
                content_length = int(self.headers['Content-Length'])
                return RequestParser.parse_urlencoded(self.rfile, content_length)
            elif content_type.split(';')[0] == 'multipart/form-data':
                return RequestParser.parse_multipart(self.rfile, content_type)
        else:
            return RequestParser.parse_query_str(query_str)

    @staticmethod
    def _split_url_and_query(url: str) -> Tuple[str, str]:
        query_index = url.rfind('?')
        query_pos = query_index if query_index != -1 else len(url)
        return url[:query_pos], url[query_pos + 1:]

    def _get_endpoint_and_positional_params(self, url: str, http_method: str):
        for regex, (http_methods, endpoint) in self._routing_map.items():
            m = regex.match(url)
            if m and endpoint and http_method in http_methods:
                return endpoint, m.groupdict()

        return not_found_endpoint, {}

    def _handle_endpoint(self, endpoint: Endpoint, args: Dict) -> Tuple[any, int]:
        try:
            params: Dict[str, inspect.Parameter] = endpoint.params
            args = self._validate_and_convert_args(args, params)
            response, http_code = endpoint(**args)
        except Exception as e:
            traceback.print_exc()
            return {'error_msg': str(e)}, 500

        if http_code not in self.HTTP_CODES:
            raise ValueError(f'Invalid response code {http_code} for endpoint {endpoint.func}')

        return response, http_code

    def _validate_and_convert_args(self, args: Dict, params: Dict[str, inspect.Parameter]) -> Dict:
        parsed_args = {}
        for name, param in params.items():
            arg_value = args.get(name)

            if self._no_default_value(param) and not arg_value:
                raise ValueError(f"Argument '{name}' is required")

            try:
                value = param.annotation(arg_value) if arg_value else param.default
            except ValueError:
                raise ValueError(f"Argument '{name}' should have type {param.annotation.__name__}")

            parsed_args[name] = value
        return parsed_args

    @staticmethod
    def _no_default_value(param: inspect.Parameter):
        return param.default == inspect.Parameter.empty

    def _send(self, response_body: str, http_code: int):
        self.send_response(http_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(response_body, 'utf-8'))


class RequestParser:
    @staticmethod
    def parse_multipart(content, content_type: str):
        ctype, pdict = cgi.parse_header(content_type)
        pdict['boundary'] = pdict['boundary'].encode("utf-8")  # noqa
        fields = cgi.parse_multipart(content, pdict)  # noqa
        return {
            key: value[0] if len(value) == 1 else value
            for key, value
            in fields.items()
        }

    @staticmethod
    def parse_urlencoded(content, content_length: int):
        body = content.read(content_length)
        query_str = body.decode()
        return RequestParser.parse_query_str(query_str)

    @staticmethod
    def parse_query_str(query_str: str):
        query_params = {}
        if query_str:
            for query_param in query_str.split('&'):
                k, v = query_param.split('=')
                query_params[k] = v
        return query_params
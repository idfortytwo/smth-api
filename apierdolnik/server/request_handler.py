import json
import re
import traceback
import typing
import pydantic

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Dict, Tuple, List
from inspect import Parameter

from endpoint import Endpoint, not_found_endpoint
from server.converter import Converter
from server.request_parser import RequestParser
from server.validator import Validator


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
        params = {**named_params, **positional_params}

        self._extract_json(params)

        response, http_code = self._process_endpoint(endpoint, params)
        response_json = json.dumps(response)
        self._send(response_json, http_code)

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

    def _extract_named_params(self, query_str: str):
        content_type = self.headers['Content-Type']
        if content_type:
            if content_type == 'application/x-www-form-urlencoded':
                content_length = int(self.headers['Content-Length'])
                return RequestParser.parse_urlencoded(self.rfile, content_length)
            elif content_type.split(';')[0] == 'multipart/form-data':
                return RequestParser.parse_multipart(self.rfile, content_type)
        return RequestParser.parse_query_str(query_str)

    def _extract_json(self, params: Dict[str, any]):
        if self.headers['Content-Type'] == 'application/json':
            json_data = RequestParser.parse_json(self)
            params['__json_data'] = json_data

    def _process_endpoint(self, endpoint: Endpoint, args: Dict) -> Tuple[any, int]:
        try:
            endpoint_params: Dict[str, Parameter] = endpoint.params
            args = self._process_args(args, endpoint_params)
            response, http_code = endpoint(**args)
        except Exception as e:
            traceback.print_exc()
            return {'error_msg': str(e)}, 500

        if http_code not in self.HTTP_CODES:
            raise ValueError(f'Invalid response code {http_code} for endpoint {endpoint.func}')

        return response, http_code

    def _process_args(self, args: Dict, params: Dict[str, Parameter]) -> Dict:
        pydantic_params, normal_params = self._separate_pydantic_params(params)
        parsed_args = {}

        for arg_name, param in normal_params.items():
            arg_value = args.get(arg_name)
            converted_value = self._validate_and_convert_arg(arg_name, arg_value, param)
            parsed_args[arg_name] = converted_value

        if json_data := args.get('__json_data'):
            for param_name, obj in self._json_to_models(json_data, pydantic_params):
                parsed_args[param_name] = obj

        return parsed_args

    @staticmethod
    def _separate_pydantic_params(params: Dict[str, Parameter]) -> Tuple[Dict[str, Parameter], Dict[str, Parameter]]:
        pydantic_params = {}
        other_params = {}
        for name, param in params.items():
            if issubclass(param.annotation, pydantic.BaseModel):
                pydantic_params[name] = param
            else:
                other_params[name] = param
        return pydantic_params, other_params

    @staticmethod
    def _validate_and_convert_arg(name: str, value: any, param: Parameter):
        Validator.validate(name, value, param)
        return Converter.convert(name, value, param)

    @staticmethod
    def _json_to_models(json_data: Dict, pydantic_params: Dict[str, Parameter]):
        for param in pydantic_params.values():
            model: typing.Type[pydantic.BaseModel] = param.annotation
            obj = model(**json_data)
            yield param.name, obj

    def _send(self, response_body: str, http_code: int):
        self.send_response(http_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(response_body, 'utf-8'))
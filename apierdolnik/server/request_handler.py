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
from server.parsers import RequestParser, JsonParser
from server.validator import Validator


class RequestHandler(BaseHTTPRequestHandler):
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
            response = endpoint(**args)

        except Exception as e:
            traceback.print_exc()
            return {'error_msg': str(e)}, 500

        return response.body, response.status_code

    def _process_args(self, args: Dict, params: Dict[str, Parameter]) -> Dict:
        complex_params, primitive_params = self._separate_params(params)
        parsed_args = {}

        json_data = args.get('__json_data')

        for arg_name, param in primitive_params.items():
            if arg_name == 'json_data':
                value = json_data
            else:
                arg_value = args.get(arg_name)
                value = self._validate_and_convert_arg(arg_name, arg_value, param)

            parsed_args[arg_name] = value

        if json_data:
            complex_args = self._parse_json(json_data, complex_params)
            return {**parsed_args, **complex_args}

        return parsed_args

    @staticmethod
    def _separate_params(params: Dict[str, Parameter]) -> Tuple[Dict[str, Parameter], Dict[str, Parameter]]:
        complex_params, primitive_params = {}, {}
        for name, param in params.items():
            annotation = param.annotation
            if typing.get_origin(annotation) or issubclass(annotation, pydantic.BaseModel):
                complex_params[name] = param
            else:
                primitive_params[name] = param
        return complex_params, primitive_params

    @staticmethod
    def _validate_and_convert_arg(name: str, value: any, param: Parameter):
        Validator.validate(name, value, param)
        return Converter.convert(name, value, param)

    @staticmethod
    def _parse_json(json_data: Dict, params: Dict[str, Parameter]):
        return {
            name: JsonParser.parse(json_data, param.annotation)
            for name, param
            in params.items()
        }

    def _send(self, response_body: str, http_code: int):
        self.send_response(http_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(response_body, 'utf-8'))
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
        url, url_query = self._split_url_and_query(self.path)
        endpoint, url_match = self._get_endpoint_and_url_match(url=url, http_method=self.command)

        params = self._extract_params(url_query, url_match) if url_match else {}
        response, http_code = self._process_endpoint(endpoint, params)

        response_json = json.dumps(response)
        self._send(response_json, http_code)

    @staticmethod
    def _split_url_and_query(url: str) -> Tuple[str, str]:
        query_index = url.rfind('?')
        query_pos = query_index if query_index != -1 else len(url)
        return url[:query_pos], url[query_pos + 1:]

    def _get_endpoint_and_url_match(self, url: str, http_method: str) -> Tuple[Endpoint, re.Match | None]:
        for regex, (http_methods, endpoint) in self._routing_map.items():
            url_match = regex.match(url)
            if url_match and endpoint and http_method in http_methods:
                return endpoint, url_match

        return not_found_endpoint, None

    def _extract_params(self, url_query: str, url_match: re.Match):
        url_params = self._extract_url_params(url_query)
        form_params = self._extract_form_params()
        positional_params = url_match.groupdict()
        params = {**url_params, **form_params, **positional_params}

        if json_data := self._extract_json():
            params['json_data'] = json_data

        return params

    @staticmethod
    def _extract_url_params(url_query: str):
        return RequestParser.parse_query_str(url_query)

    def _extract_form_params(self):
        content_type = self.headers['Content-Type']
        if content_type:
            if content_type == 'application/x-www-form-urlencoded':
                content_length = int(self.headers['Content-Length'])
                return RequestParser.parse_urlencoded(self.rfile, content_length)
            elif content_type.split(';')[0] == 'multipart/form-data':
                return RequestParser.parse_multipart(self.rfile, content_type)
        return {}

    def _extract_json(self):
        if self.headers['Content-Type'] == 'application/json':
            return RequestParser.parse_json(self)

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

        json_data = args.get('json_data')
        parsed_args = self._process_primitive_params(args, params, json_data)

        if json_data:
            complex_args = self._parse_json(json_data, complex_params)
            parsed_args.update(complex_args)

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

    def _process_primitive_params(self, args: Dict, params: Dict[str, Parameter], json_data: Dict = None):
        parsed_args = {}
        for arg_name, param in params.items():
            if arg_name == 'json_data':
                value = json_data
            else:
                arg_value = args.get(arg_name)
                value = self._validate_and_convert_arg(arg_name, arg_value, param)
            parsed_args[arg_name] = value
        return parsed_args

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
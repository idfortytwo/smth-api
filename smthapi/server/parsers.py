import cgi
import json
from http.server import BaseHTTPRequestHandler
from typing import Union, Type, Sequence, get_origin, get_args


class RequestParser:
    @staticmethod
    def parse_json(request: BaseHTTPRequestHandler):
        content_length = int(request.headers['Content-Length'])
        body_encoded = request.rfile.read(content_length)
        body = body_encoded.decode()
        return json.loads(body)

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


class JsonParser:
    @staticmethod
    def parse(data: any, data_type: Type = None):
        if (generic_origin := get_origin(data_type)) and (generic_args := get_args(data_type)):
            if generic_origin in (list, tuple):
                return JsonParser.parse_array(data, generic_args[0])
            elif generic_origin is dict:
                return JsonParser.parse_dict(data, generic_args[0], generic_args[1])
        else:
            if isinstance(data, dict):
                obj = data_type(**data)
            elif isinstance(data, Sequence):
                obj = data_type(*data)
            else:
                obj = data_type(data)
            return obj

    @staticmethod
    def parse_array(data: Union[list, tuple], value_type: Type):
        parsed_list = []
        for value in data:
            parsed_list.append(JsonParser.parse(value, value_type))
        return parsed_list

    @staticmethod
    def parse_dict(data: dict, key_type: Type, value_type: Type):
        parsed_dict = {}
        for key, value in data.items():
            parsed_key = JsonParser.parse(key, key_type)
            parsed_value = JsonParser.parse(value, value_type)
            parsed_dict[parsed_key] = parsed_value
        return parsed_dict
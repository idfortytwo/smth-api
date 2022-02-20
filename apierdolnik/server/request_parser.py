import cgi
import json
from http.server import BaseHTTPRequestHandler


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
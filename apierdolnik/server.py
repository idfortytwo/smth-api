import json
import traceback
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
        cls._routing_map: Dict[str, Tuple[List[str], Endpoint]] = routing_map

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
        endpoint = self._get_endpoint(path=self.path, http_method=self.command)
        response, http_code = self._handle_endpoint(endpoint)
        response_json = json.dumps(response)
        self._send(response_json, http_code)

    def _get_endpoint(self, path: str, http_method: str) -> Endpoint:
        http_methods, endpoint = self._routing_map.get(path, (None, []))
        if endpoint and http_method in http_methods:
            return endpoint
        return not_found_endpoint

    def _handle_endpoint(self, endpoint: Endpoint) -> Tuple[any, int]:
        try:
            response, http_code = endpoint()
        except Exception as e:
            traceback.print_exc()
            return {'error_msg': str(e)}, 500

        if http_code not in self.HTTP_CODES:
            raise ValueError(f'Invalid response code {http_code} for endpoint {endpoint.func}')

        return response, http_code

    def _send(self, response_body: str, http_code: int):
        self.send_response(http_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(response_body, 'utf-8'))
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Dict, Callable, Tuple, List


class RequestHandler(BaseHTTPRequestHandler):
    HTTP_CODES = [
        100, 101, 102, 103, 200, 201, 202, 203, 204, 205, 206, 207, 226, 300, 301, 302, 303, 304, 305, 306, 307, 308,
        400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 415, 416, 417, 418, 421, 422, 423, 424,
        425, 426, 428, 429, 431, 451, 500, 501, 502, 503, 504, 505, 506, 507, 508, 510, 511]

    @classmethod
    def register_routes(cls, routing_map: Dict):
        cls._routing_map: Dict[str, Tuple[List[str], Callable]] = routing_map

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
        http_methods, endpoint = self._routing_map.get(self.path, (None, []))
        if endpoint and self.command in http_methods:
            self._parse_endpoint(endpoint)

    def _parse_endpoint(self, endpoint: Callable):
        result, http_code = self._get_result_and_code(endpoint)
        response_body = json.dumps(result)

        print(response_body, http_code)

        self.send_response(http_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(response_body, 'utf-8'))

    def _get_result_and_code(self, endpoint: Callable) -> Tuple[any, int]:
        match endpoint():
            case result, http_code:
                if http_code in self.HTTP_CODES:
                    return result, http_code
                else:
                    return {'error_msg': 'Endpoint returned invalid response type'}, 500
            case result:
                return result, 200
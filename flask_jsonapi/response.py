import http
import json

from flask import helpers


class JsonApiResponse:
    base_header = {'Content-Type': 'application/vnd.api+json'}

    def __init__(self, response_data, headers=None, status=None):
        self.response_data = response_data
        self.status = status or http.HTTPStatus.OK
        self.headers = headers or {}

    def make_response(self):
        self.response_data.update({'jsonapi': {'version': '1.0'}})
        response = helpers.make_response(
            json.dumps(self.response_data),
            self.status,
        )
        response.headers.extend(self.base_header)
        response.headers.extend(self.headers)
        return response


class JsonApiListResponse(JsonApiResponse):
    def __init__(self, response_data, headers=None, status=None):
        super().__init__(response_data, headers, status)
        self.response_data.update({'meta': {'count': len(self.response_data['data'])}})


class JsonApiErrorResponse:
    base_header = {'Content-Type': 'application/vnd.api+json'}

    def __init__(self, *jsonapi_errors, status=None):
        self.jsonapi_errors_tuple = jsonapi_errors
        self.status = status or http.HTTPStatus.INTERNAL_SERVER_ERROR

    @property
    def jsonapi_errors(self):
        return {
            'errors': list(self.jsonapi_errors_tuple),
            'jsonapi': {
                'version': '1.0'
            }
        }

    def make_error_response(self):
        response = helpers.make_response(
            json.dumps(self.jsonapi_errors),
            self.status,
        )
        response.headers.extend(self.base_header)
        return response

import http
import json

from flask import helpers


class BaseResponse:
    def __init__(self, headers=None, status=None):
        self.status = status or http.HTTPStatus.OK
        self.headers = headers or {}

    def make_response(self):
        response = helpers.make_response(
            self.get_content(),
            self.status,
        )
        response.headers.extend(self.headers)
        return response

    def get_content(self):
        raise NotImplementedError


class EmptyResponse(BaseResponse):
    def __init__(self, headers=None, status=http.HTTPStatus.NO_CONTENT):
        super().__init__(headers, status)

    def get_content(self):
        return ''


class BaseJsonApiResponse(BaseResponse):
    base_header = {'Content-Type': 'application/vnd.api+json'}

    def make_response(self):
        response = super().make_response()
        response.headers.extend(self.base_header)
        return response

    def get_content(self):
        data = dict(self.get_response_data(), **{'jsonapi': {'version': '1.0'}})
        return json.dumps(data)

    def get_response_data(self):
        raise NotImplementedError


class JsonApiResponse(BaseJsonApiResponse):
    def __init__(self, response_data, headers=None, status=None):
        self.response_data = response_data
        super().__init__(headers, status)

    def get_response_data(self):
        return self.response_data


class JsonApiListResponse(JsonApiResponse):
    def get_response_data(self):
        response_data = super().get_response_data()
        return dict(**response_data, **{'meta': {'count': len(self.response_data['data'])}})


class JsonApiErrorResponse(BaseJsonApiResponse):
    def __init__(self, *jsonapi_errors, headers=None, status=http.HTTPStatus.INTERNAL_SERVER_ERROR):
        super().__init__(headers, status)
        self.jsonapi_errors_tuple = jsonapi_errors

    @classmethod
    def from_marshmallow_errors(cls, errors, status=http.HTTPStatus.UNPROCESSABLE_ENTITY):
        return cls(*errors['errors'], status=status)

    def get_response_data(self):
        return {
            'errors': list(self.jsonapi_errors_tuple),
        }

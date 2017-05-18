import http
import json

from flask_jsonapi import exceptions
from flask_jsonapi import response


def test_jsonapi_error_response(app):
    with app.test_request_context('/example/5d285d41-398d-4322-a6d4-d15af6bd930e/'):
        error_response = response.JsonApiErrorResponse(
            exceptions.JsonApiException(
                source="An object containing references to the source of the error. "
                    "http://jsonapi.org/format/#errors",
                detail='exception details',
                title='Something terrible happened.',
                status=http.HTTPStatus.INTERNAL_SERVER_ERROR
            ).to_dict()
        ).make_response()
        assert json.loads(error_response.data.decode()) == {
            "jsonapi": {
                "version": "1.0"
            },
            "errors": [
                {
                    "detail": "exception details",
                    "title": "Something terrible happened.",
                    "status": 500,
                    "source": "An object containing references to the source of the error. "
                              "http://jsonapi.org/format/#errors"
                }
            ]
        }

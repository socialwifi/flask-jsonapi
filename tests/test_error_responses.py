import datetime

from unittest import mock

import flask
import marshmallow_jsonapi
import werkzeug.datastructures
import werkzeug.exceptions

from marshmallow_jsonapi import fields

from flask_jsonapi import exceptions
from flask_jsonapi import resources
from flask_jsonapi import response as jsonapi_response


class ExampleSchema(marshmallow_jsonapi.Schema):
    id = fields.Str()

    class Meta:
        type_ = 'example'
        self_url = '/failing/{id}/'
        self_url_kwargs = {'id': '<id>'}


class SecretFailingSchema(ExampleSchema):
    name = fields.Method('get_name')

    def get_name(self, obj):
        raise KeyError('secret')


class SuccessfulView(resources.ResourceDetail):
    schema = ExampleSchema

    def read(self, id):
        return {'id': id}

    def update(self, id, data, **kwargs):
        return {'id': id}


def make_view(api, error):
    class FailingView(resources.ResourceDetail):
        schema = ExampleSchema

        def read(self, id):
            raise error

    api.route(FailingView, 'failing', '/failing/<id>/')


def test_unexpected_exception_is_a_generic_jsonapi_500(api, jsonapi_client):
    make_view(api, KeyError('database password'))
    with mock.patch('flask_jsonapi.resources.logger') as logger:
        response = jsonapi_client.get('/failing/1/')
    assert response.status_code == 500
    assert response.headers['Content-Type'] == 'application/vnd.api+json'
    assert response.get_json(force=True)['errors'] == [{'status': 500, 'title': 'Internal server error'}]
    assert b'database password' not in response.data
    assert logger.exception.called


def test_flask_abort_is_a_jsonapi_error(api, jsonapi_client):
    make_view(api, werkzeug.exceptions.Forbidden())
    response = jsonapi_client.get('/failing/1/')
    assert response.status_code == 403
    assert response.get_json(force=True)['errors'] == [{'status': 403, 'title': 'Forbidden'}]


def test_jsonapi_exception_is_rendered_as_before(api, jsonapi_client):
    make_view(api, exceptions.Unauthorized(detail='No token.'))
    response = jsonapi_client.get('/failing/1/')
    assert response.status_code == 401
    assert response.get_json(force=True)['errors'] == [{'status': 401, 'title': 'Unauthorized', 'detail': 'No token.'}]


def test_abort_with_a_response_returns_that_response_unchanged(api, jsonapi_client):
    make_view(api, werkzeug.exceptions.HTTPException(response=flask.Response('teapot', 418)))
    response = jsonapi_client.get('/failing/1/')
    assert response.status_code == 418
    assert response.data == b'teapot'


def test_http_exception_without_code_is_a_generic_jsonapi_500(api, jsonapi_client):
    make_view(api, werkzeug.exceptions.HTTPException())
    response = jsonapi_client.get('/failing/1/')
    assert response.status_code == 500
    assert response.headers['Content-Type'] == 'application/vnd.api+json'
    assert response.get_json(force=True)['errors'] == [{'status': 500, 'title': 'Internal server error'}]


def test_response_serialization_failure_is_a_generic_jsonapi_500(api, jsonapi_client):
    class UnserializableView(resources.ResourceDetail):
        schema = ExampleSchema

        def get(self, *args, **kwargs):
            return jsonapi_response.JsonApiResponse({'data': datetime.datetime.now()})

    api.route(UnserializableView, 'unserializable', '/unserializable/<id>/')
    with mock.patch('flask_jsonapi.resources.logger') as logger:
        response = jsonapi_client.get('/unserializable/1/')
    assert response.status_code == 500
    assert response.headers['Content-Type'] == 'application/vnd.api+json'
    assert response.get_json(force=True)['errors'] == [{'status': 500, 'title': 'Internal server error'}]
    assert logger.exception.called


def test_head_is_served_by_the_get_handler(api, jsonapi_client):
    api.route(SuccessfulView, 'successful', '/successful/<id>/')
    with mock.patch('flask_jsonapi.resources.logger') as logger:
        response = jsonapi_client.head('/successful/1/')
    assert response.status_code == 200
    assert response.data == b''
    assert not logger.exception.called


def test_method_without_handler_is_a_jsonapi_405(api, jsonapi_client):
    class PutWithoutHandlerView(SuccessfulView):
        methods = ['GET', 'PUT']

    api.route(PutWithoutHandlerView, 'put_without_handler', '/put-without-handler/<id>/')
    response = jsonapi_client.put('/put-without-handler/1/')
    assert response.status_code == 405
    assert response.headers['Content-Type'] == 'application/vnd.api+json'
    assert response.get_json(force=True)['errors'][0]['status'] == 405


def test_patch_with_wrong_type_is_a_jsonapi_409(api, jsonapi_client):
    api.route(SuccessfulView, 'successful', '/successful/<id>/')
    response = jsonapi_client.patch('/successful/1/', json={'data': {'type': 'wrong', 'id': '1'}})
    assert response.status_code == 409
    assert response.headers['Content-Type'] == 'application/vnd.api+json'
    assert response.get_json(force=True)['errors'] == [
        {'detail': 'Invalid type. Expected "example".', 'source': {'pointer': '/data/type'}},
    ]


def test_schema_dump_error_is_a_generic_jsonapi_500(api, jsonapi_client):
    class SecretFailingView(SuccessfulView):
        schema = SecretFailingSchema

    api.route(SecretFailingView, 'secret_failing', '/secret-failing/<id>/')
    with mock.patch('flask_jsonapi.resources.logger') as logger:
        response = jsonapi_client.get('/secret-failing/1/')
    assert response.status_code == 500
    assert response.get_json(force=True)['errors'] == [{'status': 500, 'title': 'Internal server error'}]
    assert b'secret' not in response.data
    assert logger.exception.called


def test_list_schema_dump_error_is_a_generic_jsonapi_500(api, jsonapi_client):
    class SecretFailingListView(resources.ResourceList):
        schema = SecretFailingSchema

        def read_many(self, filters, sorting, pagination):
            return [{'id': '1'}]

    api.route(SecretFailingListView, 'secret_failing_list', '/secret-failing/')
    with mock.patch('flask_jsonapi.resources.logger') as logger:
        response = jsonapi_client.get('/secret-failing/')
    assert response.status_code == 500
    assert b'secret' not in response.data
    assert logger.exception.called


def test_http_exception_headers_are_kept(api, jsonapi_client):
    challenge = werkzeug.datastructures.WWWAuthenticate('Bearer', {'realm': 'api'})
    make_view(api, werkzeug.exceptions.Unauthorized(www_authenticate=challenge))
    response = jsonapi_client.get('/failing/1/')
    assert response.status_code == 401
    assert response.headers['WWW-Authenticate'] == 'Bearer realm=api'
    assert response.headers['Content-Type'] == 'application/vnd.api+json'

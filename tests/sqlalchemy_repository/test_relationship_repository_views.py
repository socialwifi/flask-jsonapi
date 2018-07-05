import http
import json
from unittest import mock

import marshmallow_jsonapi
from marshmallow_jsonapi import fields

from flask_jsonapi import api
from flask_jsonapi import resource_repository_views
from tests.sqlalchemy_repository import conftest


class ProfileSchema(marshmallow_jsonapi.Schema):
    id = fields.Int(required=True)
    premium_membership = fields.Bool()

    class Meta:
        type_ = 'profile'
        strict = True


class AddressSchema(marshmallow_jsonapi.Schema):
    id = fields.Int(required=True)
    email = fields.Str()

    class Meta:
        type_ = 'address'
        strict = True


class UserProfileRelationshipView(resource_repository_views.ToOneRelationshipRepositoryView):
    schema = ProfileSchema


class UserAddressesRelationshipView(resource_repository_views.ToManyRelationshipRepositoryView):
    schema = AddressSchema


def test_deserialize_relationship_to_one():
    schema = UserProfileRelationshipView().computed_schema
    data, errors = schema.load({
        "data": {"type": "profile", "id": 12}
    })
    assert data == {'id': 12}


def test_serialize_relationship_to_one():
    schema = UserProfileRelationshipView().computed_schema
    data, errors = schema.dump({'id': 12, 'premium_membership': True})
    assert data == {'data': {'type': 'profile', 'id': 12}}


def test_deserialize_relationship_to_many():
    schema = UserAddressesRelationshipView().computed_schema
    data, errors = schema.load({
        'data': [
            {'type': 'address', 'id': 12}
        ]
    })
    assert data == [{'id': 12}]


def test_serialize_relationship_to_many():
    schema = UserAddressesRelationshipView().computed_schema
    data, errors = schema.dump([{'id': 12, 'email': 'address@email.com'}])
    assert data == {
        'data': [
            {'type': 'address', 'id': 12}
        ]
    }


@mock.patch.object(UserProfileRelationshipView, 'repository')
def test_relationship_repository_to_one_get(user_profile_repository, app):
    user_profile_repository.get_detail.return_value = {'id': 12}
    application_api = api.Api(app)
    application_api.route(UserProfileRelationshipView,
                          'user_profile_relationship',
                          '/user/<int:id>/relationships/profile/')
    response = app.test_client().get(
        '/user/666/relationships/profile/',
        headers=conftest.JSONAPI_HEADERS
    )
    result = json.loads(response.data.decode('utf-8'))
    assert UserProfileRelationshipView.repository.get_detail.call_args[0] == (666,)
    assert response.status_code == http.HTTPStatus.OK
    assert result == {
       'data': {
          'id': 12,
          'type': 'profile'
       },
       'jsonapi': {
          'version': '1.0'
       }
    }


@mock.patch.object(UserProfileRelationshipView, 'repository')
def test_relationship_repository_to_one_patch(user_profile_repository, app):
    user_profile_repository.update.return_value = {'id': 12}
    application_api = api.Api(app)
    application_api.route(UserProfileRelationshipView,
                          'user_profile_relationship',
                          '/user/<int:id>/relationships/profile/')
    json_data = json.dumps({
        'data': {
            'type': 'profile',
            'id': 12
        }
    })
    response = app.test_client().patch(
        '/user/666/relationships/profile/',
        headers=conftest.JSONAPI_HEADERS,
        data=json_data,
    )
    result = json.loads(response.data.decode('utf-8'))
    assert UserProfileRelationshipView.repository.update.call_args[0] == (666, {'id': 12})
    assert response.status_code == http.HTTPStatus.OK
    assert result == {
        'data': {
            'id': 12,
            'type': 'profile'
        },
        'jsonapi': {
            'version': '1.0'
        }
    }


@mock.patch.object(UserProfileRelationshipView, 'repository')
def test_relationship_repository_to_one_delete(user_profile_repository, app):
    user_profile_repository.delete.return_value = {}
    application_api = api.Api(app)
    application_api.route(UserProfileRelationshipView,
                          'user_profile_relationship',
                          '/user/<int:id>/relationships/profile/')
    json_data = json.dumps({
        'data': None
    })
    response = app.test_client().patch(
        '/user/666/relationships/profile/',
        headers=conftest.JSONAPI_HEADERS,
        data=json_data,
    )
    assert UserProfileRelationshipView.repository.delete.call_args[0] == (666,)
    assert response.status_code == http.HTTPStatus.NO_CONTENT


@mock.patch.object(UserAddressesRelationshipView, 'repository')
def test_relationship_repository_to_many_get(user_addresses_repository, app):
    user_addresses_repository.get_list.return_value = [{'id': 12}, {'id': 24}]
    application_api = api.Api(app)
    application_api.route(UserAddressesRelationshipView,
                          'user_addresses_relationship',
                          '/user/<int:id>/relationships/addresses/')
    response = app.test_client().get(
        '/user/666/relationships/addresses/',
        headers=conftest.JSONAPI_HEADERS
    )
    result = json.loads(response.data.decode('utf-8'))
    assert UserAddressesRelationshipView.repository.get_list.call_args[0] == (666,)
    assert response.status_code == http.HTTPStatus.OK
    assert result == {
       'data': [
          {
             'id': 12,
             'type': 'address'
          },
          {
             'id': 24,
             'type': 'address'
          }
       ],
       'jsonapi': {
          'version': '1.0'
       }
    }


@mock.patch.object(UserAddressesRelationshipView, 'repository')
def test_relationship_repository_to_many_create(user_addresses_repository, app):
    user_addresses_repository.create.return_value = [{'id': 12}]
    application_api = api.Api(app)
    application_api.route(UserAddressesRelationshipView,
                          'user_addresses_relationship',
                          '/user/<int:id>/relationships/addresses/')
    json_data = json.dumps({
        'data': [
            {'type': 'address', 'id': 12}
        ]
    })
    response = app.test_client().post(
        '/user/666/relationships/addresses/',
        headers=conftest.JSONAPI_HEADERS,
        data=json_data,
    )
    result = json.loads(response.data.decode('utf-8'))
    assert UserAddressesRelationshipView.repository.create.call_args[0] == (666, [{'id': 12}])
    assert response.status_code == http.HTTPStatus.OK
    assert result == {
       'data': [
          {
             'id': 12,
             'type': 'address'
          },
       ],
       'jsonapi': {
          'version': '1.0'
       }
    }


@mock.patch.object(UserAddressesRelationshipView, 'repository')
def test_relationship_repository_to_many_patch(user_addresses_repository, app):
    user_addresses_repository.update.return_value = [{'id': 12}]
    application_api = api.Api(app)
    application_api.route(UserAddressesRelationshipView,
                          'user_addresses_relationship',
                          '/user/<int:id>/relationships/addresses/')
    json_data = json.dumps({
        'data': [
            {'type': 'address', 'id': 12}
        ]
    })
    response = app.test_client().patch(
        '/user/666/relationships/addresses/',
        headers=conftest.JSONAPI_HEADERS,
        data=json_data,
    )
    result = json.loads(response.data.decode('utf-8'))
    assert UserAddressesRelationshipView.repository.update.call_args[0] == (666, [{'id': 12}])
    assert response.status_code == http.HTTPStatus.OK
    assert result == {
       'data': [
          {
             'id': 12,
             'type': 'address'
          },
       ],
       'jsonapi': {
          'version': '1.0'
       }
    }


@mock.patch.object(UserAddressesRelationshipView, 'repository')
def test_relationship_repository_to_many_delete(user_addresses_repository, app):
    user_addresses_repository.delete.return_value = []
    application_api = api.Api(app)
    application_api.route(UserAddressesRelationshipView,
                          'user_addresses_relationship',
                          '/user/<int:id>/relationships/addresses/')
    json_data = json.dumps({
        'data': [
            {'type': 'address', 'id': 12}
        ]
    })
    response = app.test_client().delete(
        '/user/666/relationships/addresses/',
        headers=conftest.JSONAPI_HEADERS,
        data=json_data,
    )
    assert UserAddressesRelationshipView.repository.delete.call_args[0] == (666, [{'id': 12}])
    assert response.status_code == http.HTTPStatus.NO_CONTENT

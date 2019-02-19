import collections
import json

import marshmallow_jsonapi

from marshmallow_jsonapi import fields

from flask_jsonapi import PermissionManagerBase
from flask_jsonapi import ProtectedResourceRepository
from flask_jsonapi import ProtectedResourceRepositoryViewSet
from flask_jsonapi import api
from flask_jsonapi.protected_resource_repository_views import CREATE_ACTION
from flask_jsonapi.protected_resource_repository_views import DESTROY_ACTION
from flask_jsonapi.protected_resource_repository_views import LIST_ACTION
from flask_jsonapi.protected_resource_repository_views import MANAGER_ROLE
from flask_jsonapi.protected_resource_repository_views import NO_ROLE
from flask_jsonapi.protected_resource_repository_views import OWNER_ROLE
from flask_jsonapi.protected_resource_repository_views import READ_ACTION
from flask_jsonapi.protected_resource_repository_views import READER_ROLE
from flask_jsonapi.protected_resource_repository_views import UPDATE_ACTION
from flask_jsonapi.resource_repositories.repositories import Parent

JSONAPI_HEADERS = {'content-type': 'application/vnd.api+json', 'accept': 'application/vnd.api+json'}


class ExampleSchema(marshmallow_jsonapi.Schema):
    id = fields.UUID(required=True)
    body = fields.Str()

    class Meta:
        type_ = 'example'
        self_view_many = 'example_list'
        self_view = 'example_detail'
        self_view_kwargs = {'example_id': '<id>'}
        strict = True


ExampleModel = collections.namedtuple('ExampleModel', 'id body')


class Repository(ProtectedResourceRepository):
    def __init__(self):
        self.deleted_ids = []

    def create(self, data, **kwargs):
        return ExampleModel(**data)

    def get_list(self, filters=None, sorting=None, pagination=None):
        return [
            ExampleModel(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a4', body='heheh'),
            ExampleModel(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a5', body='hihi'),
        ]

    def get_detail(self, id):
        return ExampleModel(id=id, body='Gwynbelidd')

    def delete(self, id):
        self.deleted_ids.append(id)

    def update(self, id, **data):
        pass

    def get_parent_by_filters(self, filters):
        return Parent('parent', 777)

    def get_parent_by_data(self, data):
        return Parent('parent', 777)

    def get_parent_by_id(self, id):
        return Parent('parent', 777)


def view_set_factory(*, action, required_role, user_role):
    class ExampleResourceRepositoryViewSet(ProtectedResourceRepositoryViewSet):
        schema = ExampleSchema
        permission_manager = PermissionManagerBase(
            get_account_id_method=lambda: 'user_id',
            get_account_role_name_method=lambda parent, account_id: user_role,
            permission_map={
                action: required_role,
            },
        )

        def __init__(self):
            super().__init__(repository=Repository())

    return ExampleResourceRepositoryViewSet()


def test_required_role_same_as_user_role(app):
    application_api = api.Api(app)
    view_set = view_set_factory(action=LIST_ACTION, required_role=OWNER_ROLE, user_role=OWNER_ROLE)
    application_api.repository(view_set, 'example', '/examples/')
    response = app.test_client().get('/examples/', headers=JSONAPI_HEADERS)

    assert response.status_code == 200


def test_required_role_lower_than_user_role(app):
    application_api = api.Api(app)
    view_set = view_set_factory(action=LIST_ACTION, required_role=MANAGER_ROLE, user_role=OWNER_ROLE)
    application_api.repository(view_set, 'example', '/examples/')
    response = app.test_client().get('/examples/', headers=JSONAPI_HEADERS)

    assert response.status_code == 200


def test_required_role_higher_than_user_role_list(app):
    application_api = api.Api(app)
    view_set = view_set_factory(action=LIST_ACTION, required_role=OWNER_ROLE, user_role=MANAGER_ROLE)
    application_api.repository(view_set, 'example', '/examples/')
    response = app.test_client().get('/examples/', headers=JSONAPI_HEADERS)

    assert response.status_code == 403


def test_required_role_higher_than_user_role_create(app):
    application_api = api.Api(app)
    view_set = view_set_factory(action=CREATE_ACTION, required_role=OWNER_ROLE, user_role=MANAGER_ROLE)
    application_api.repository(view_set, 'example', '/examples/')
    app.testing = True
    data = {
        'data': {
            'type': 'example',
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'attributes': {
                'body': "Nice body.",
            },
        },
    }
    response = app.test_client().post('/examples/', headers=JSONAPI_HEADERS, data=json.dumps(data))

    assert response.status_code == 403


def test_required_role_higher_than_user_role_read(app):
    application_api = api.Api(app)
    view_set = view_set_factory(action=READ_ACTION, required_role=OWNER_ROLE, user_role=MANAGER_ROLE)
    application_api.repository(view_set, 'example', '/examples/')
    response = app.test_client().get('/examples/1/', headers=JSONAPI_HEADERS)

    assert response.status_code == 403


def test_required_role_higher_than_user_role_update(app):
    application_api = api.Api(app)
    view_set = view_set_factory(action=UPDATE_ACTION, required_role=OWNER_ROLE, user_role=MANAGER_ROLE)
    application_api.repository(view_set, 'example', '/examples/')
    data = {
        'data': {
            'type': 'example',
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'attributes': {
                'body': "Nice body.",
            },
        },
    }
    response = app.test_client().patch('/examples/1/', headers=JSONAPI_HEADERS, data=json.dumps(data))

    assert response.status_code == 403


def test_required_role_higher_than_user_role_destroy(app):
    application_api = api.Api(app)
    view_set = view_set_factory(action=DESTROY_ACTION, required_role=OWNER_ROLE, user_role=MANAGER_ROLE)
    application_api.repository(view_set, 'example', '/examples/')
    response = app.test_client().delete('/examples/1/', headers=JSONAPI_HEADERS)

    assert response.status_code == 403


def test_no_role_required(app):
    application_api = api.Api(app)
    view_set = view_set_factory(action=LIST_ACTION, required_role=NO_ROLE, user_role=None)
    application_api.repository(view_set, 'example', '/examples/')
    response = app.test_client().get('/examples/', headers=JSONAPI_HEADERS)

    assert response.status_code == 200


def test_deny_access_without_role(app):
    application_api = api.Api(app)
    view_set = view_set_factory(action=LIST_ACTION, required_role=READER_ROLE, user_role=None)
    application_api.repository(view_set, 'example', '/examples/')
    response = app.test_client().get('/examples/', headers=JSONAPI_HEADERS)

    assert response.status_code == 403


def test_action_not_configured(app):
    application_api = api.Api(app)
    view_set = view_set_factory(action=DESTROY_ACTION, required_role=READER_ROLE, user_role=None)
    application_api.repository(view_set, 'example', '/examples/')
    response = app.test_client().get('/examples/', headers=JSONAPI_HEADERS)

    assert response.status_code == 403

import collections
import json

import marshmallow_jsonapi
from marshmallow_jsonapi import fields

from flask_jsonapi import api
from flask_jsonapi import resource_repositories

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


class Repository:
    def __init__(self):
        self.deleted_ids = []

    def create(self, **kwargs):
        return ExampleModel(**kwargs)

    def get_list(self, filters=None):
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


class ExampleResourceRepositoryViewSet(resource_repositories.ResourceRepositoryViewSet):
    schema = ExampleSchema

    def __init__(self):
        super().__init__(repository=Repository())


def test_integration_get_list(app):
    application_api = api.Api(app)
    application_api.repository(ExampleResourceRepositoryViewSet(), 'example', '/examples/')
    response = app.test_client().get(
        '/examples/',
        headers=JSONAPI_HEADERS
    )
    result = json.loads(response.data.decode())
    assert result == {
        'data': [
            {
                'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
                'type': 'example',
                'attributes': {
                    'body': 'heheh'
                }
            }, {
                'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a5',
                'type': 'example',
                'attributes': {
                    'body': 'hihi'
                },
            }
        ],
        'jsonapi': {
            'version': '1.0'
        },
        'meta': {
            'count': 2
        }
    }


def test_integration_create_resource(app):
    application_api = api.Api(app)
    application_api.repository(ExampleResourceRepositoryViewSet(), 'example', '/examples/')

    json_data = json.dumps({
        'data': {
            'type': 'example',
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'attributes': {
                'body': "Nice body.",
            }
        }
    })
    response = app.test_client().post(
        '/examples/',
        headers=JSONAPI_HEADERS,
        data=json_data,
    )
    assert json.loads(response.data.decode()) == {
        "data": {
            "type": "example",
            "id": "f60717a3-7dc2-4f1a-bdf4-f2804c3127a4",
            "attributes": {
                "body": "Nice body."
            }
        },
        "jsonapi": {
            "version": "1.0"
        }
    }


def test_integration_get(app):
    application_api = api.Api(app)
    application_api.repository(ExampleResourceRepositoryViewSet(), 'example', '/examples/')
    response = app.test_client().get(
        '/examples/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/',
        headers=JSONAPI_HEADERS
    )
    result = json.loads(response.data.decode())
    assert result == {
        'data': {
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'type': 'example',
            'attributes': {
                'body': 'Gwynbelidd'
            }
        },
        'jsonapi': {
            'version': '1.0'
        }
    }


def test_integration_delete(app):
    application_api = api.Api(app)
    view_set = ExampleResourceRepositoryViewSet()
    application_api.repository(view_set, 'example', '/examples/')
    response = app.test_client().delete(
        '/examples/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/',
        headers=JSONAPI_HEADERS
    )
    assert response.status_code == 204
    assert response.data == b''
    assert view_set.repository.deleted_ids == ['f60717a3-7dc2-4f1a-bdf4-f2804c3127a4']


def test_integration_patch_with_empty_response(app, ):
    application_api = api.Api(app)
    view_set = ExampleResourceRepositoryViewSet()
    application_api.repository(view_set, 'example', '/examples/')

    json_data = json.dumps({
        'data': {
            'type': 'example',
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'attributes': {
                'body': "Nice body.",
            }
        }
    })
    response = app.test_client().patch(
        '/examples/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/',
        headers=JSONAPI_HEADERS,
        data=json_data,
    )
    assert response.status_code == 204
    assert response.data == b''

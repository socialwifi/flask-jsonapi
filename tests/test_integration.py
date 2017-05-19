import collections
import json

import marshmallow_jsonapi
import pytest
from marshmallow_jsonapi import fields

from flask_jsonapi import api
from flask_jsonapi import resource


@pytest.fixture
def example_schema():
    class ExmapleSchema(marshmallow_jsonapi.Schema):
        id = fields.UUID(required=True)
        body = fields.Str()

        class Meta:
            type_ = 'example'
            self_view_many = 'example_list'
            self_view = 'example_detail'
            self_view_kwargs = {'example_id': '<id>'}
            strict = True
    return ExmapleSchema


@pytest.fixture
def example_model():
    ExampleModel = collections.namedtuple('ExampleModel', 'id body')
    return ExampleModel


def test_integration_get_list(app, example_schema, example_model):
    class ExampleListView(resource.ResourceList):
        schema = example_schema

        def read_many(self):
            return [
                example_model(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a4', body='heheh'),
                example_model(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a5', body='hihi'),
            ]

    application_api = api.Api(app)
    application_api.route(ExampleListView, 'example_list', '/examples/')
    response = app.test_client().get(
        '/examples/',
        headers={'content-type': 'application/vnd.api+json'}
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


def test_integration_create_resource(app, example_schema, example_model):
    class ExampleListView(resource.ResourceList):
        schema = example_schema

        def create(self, *args, **kwargs):
            return example_model(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a4', body='Nice body.')

    json_data = json.dumps({
        'data': {
            'type': 'example',
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'attributes': {
                'body': "Nice body.",
            }
        }
    })
    application_api = api.Api(app)
    application_api.route(ExampleListView, 'example_list', '/examples/')
    response = app.test_client().post(
        '/examples/',
        headers={'content-type': 'application/vnd.api+json'},
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


def test_integration_get(app, example_schema, example_model):

    class ExampleDetailView(resource.ResourceDetail):
        schema = example_schema

        def read(self, id):
            return example_model(id=id, body='Gwynbelidd')

    application_api = api.Api(app)
    application_api.route(ExampleDetailView, 'example_detail', '/examples/<id>/')
    response = app.test_client().get(
        '/examples/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/',
        headers={'content-type': 'application/vnd.api+json'}
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


def test_integration_delete(app, example_schema, example_model):

    class ExampleDetailView(resource.ResourceDetail):
        schema = example_schema
        deleted_ids = []

        def destroy(self, id):
            self.deleted_ids.append(id)

    application_api = api.Api(app)
    application_api.route(ExampleDetailView, 'example_detail', '/examples/<id>/')
    response = app.test_client().delete(
        '/examples/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/',
        headers={'content-type': 'application/vnd.api+json'}
    )
    assert response.status_code == 204
    assert response.data == b''
    assert ExampleDetailView.deleted_ids == ['f60717a3-7dc2-4f1a-bdf4-f2804c3127a4']


def test_integration_patch(app, example_schema, example_model):

    class ExampleDetailView(resource.ResourceDetail):
        schema = example_schema

        def update(self, id, data):
            data.pop('id')
            return example_model(id=id, **data)

    json_data = json.dumps({
        'data': {
            'type': 'example',
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'attributes': {
                'body': "Nice body.",
            }
        }
    })
    application_api = api.Api(app)
    application_api.route(ExampleDetailView, 'example_list', '/examples/<id>/')
    response = app.test_client().patch(
        '/examples/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/',
        headers={'content-type': 'application/vnd.api+json'},
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


def test_integration_patch_with_empty_response(app, example_schema, example_model):

    class ExampleDetailView(resource.ResourceDetail):
        schema = example_schema

        def update(self, id, data):
            pass

    json_data = json.dumps({
        'data': {
            'type': 'example',
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'attributes': {
                'body': "Nice body.",
            }
        }
    })
    application_api = api.Api(app)
    application_api.route(ExampleDetailView, 'example_list', '/examples/<id>/')
    response = app.test_client().patch(
        '/examples/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/',
        headers={'content-type': 'application/vnd.api+json'},
        data=json_data,
    )
    assert response.status_code == 204
    assert response.data == b''

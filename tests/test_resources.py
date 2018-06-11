import collections
import json
from unittest import mock

import marshmallow_jsonapi
import pytest
from marshmallow_jsonapi import fields

from flask_jsonapi import api
from flask_jsonapi import filters_schema
from flask_jsonapi import resources

JSONAPI_HEADERS = {'content-type': 'application/vnd.api+json', 'accept': 'application/vnd.api+json'}


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
    class ExampleListView(resources.ResourceList):
        schema = example_schema

        def read_many(self, filters, pagination):
            return [
                example_model(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a4', body='heheh'),
                example_model(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a5', body='hihi'),
            ]

    application_api = api.Api(app)
    application_api.route(ExampleListView, 'example_list', '/examples/')
    response = app.test_client().get(
        '/examples/',
        headers=JSONAPI_HEADERS
    )
    result = json.loads(response.data.decode())
    assert response.status_code == 200
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


def test_integration_get_list_with_pagination(app, example_schema, example_model):
    class ExampleListView(resources.ResourceList):
        schema = example_schema

        def read_many(self, filters, pagination):
            return [
                example_model(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a4', body='heheh'),
                example_model(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a5', body='hihi'),
            ]

        def get_count(self, filters):
            return 5

    application_api = api.Api(app)
    application_api.route(ExampleListView, 'example_list', '/examples/')
    response = app.test_client().get(
        '/examples/?page[size]=2&page[number]=1',
        headers=JSONAPI_HEADERS
    )
    result = json.loads(response.data.decode())
    assert response.status_code == 200
    assert result == {
        'data': [
            {
                'type': 'example',
                'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
                'attributes': {
                    'body': 'heheh'
                }
            },
            {
                'type': 'example',
                'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a5',
                'attributes': {
                    'body': 'hihi'
                }
            }
        ],
        'links': {
            'self': 'http://localhost/examples/?page[size]=2&page[number]=1',
            'first': 'http://localhost/examples/?page[size]=2&page[number]=1',
            'previous': None,
            'next': 'http://localhost/examples/?page[size]=2&page[number]=2',
            'last': 'http://localhost/examples/?page[size]=2&page[number]=3'
        },
        'meta': {
            'count': 2
        },
        'jsonapi': {
            'version': '1.0'
        }
    }


def test_integration_bad_accept_header(app, example_schema, example_model):
    class ExampleListView(resources.ResourceList):
        schema = example_schema

    application_api = api.Api(app)
    application_api.route(ExampleListView, 'example_list', '/examples/')
    response = app.test_client().get('/examples/', headers={'accept': 'text/html'})
    assert response.status_code == 406
    assert json.loads(response.data.decode()) == {
        'errors': [{
            'detail': 'Accept header must be application/vnd.api+json',
            'source': '',
            'status': 406,
            'title': 'InvalidRequestHeader'
        }],
        'jsonapi': {
            'version': '1.0'
        },
    }


def test_integration_bad_content_type_header(app, example_schema, example_model):
    class ExampleListView(resources.ResourceList):
        schema = example_schema

    application_api = api.Api(app)
    application_api.route(ExampleListView, 'example_list', '/examples/')
    response = app.test_client().post('/examples/', headers={'accept': 'application/vnd.api+json'})
    assert response.status_code == 415
    assert json.loads(response.data.decode()) == {
        'errors': [{
            'detail': 'Content-Type header must be application/vnd.api+json',
            'source': '',
            'status': 415,
            'title': 'InvalidRequestHeader'
        }],
        'jsonapi': {
            'version': '1.0'
        },
    }


def test_integration_get_filtered_list(app, example_schema, example_model):
    class ExampleListView(resources.ResourceList):
        schema = example_schema
        filter_schema = filters_schema.FilterSchema({
            'basic': filters_schema.FilterField(),
            'listed': filters_schema.ListFilterField(),
            'renamed': filters_schema.FilterField(field_name='dumb-name'),
            'integer': filters_schema.FilterField(parse_value=int),
            'skipped_filter': filters_schema.FilterField(),

        })

        applied_filters = []

        def read_many(self, filters, pagination):
            self.applied_filters.append(filters)
            return []

    application_api = api.Api(app)
    application_api.route(ExampleListView, 'example_list', '/examples/')
    response = app.test_client().get(
        '/examples/?filter[basic]=text&filter[listed]=first,second&filter[dumb-name]=another&filter[integer]=3',
        headers=JSONAPI_HEADERS
    )
    assert response.status_code == 200
    assert ExampleListView.applied_filters == [{
        'basic': 'text',
        'listed': ['first', 'second'],
        'renamed': 'another',
        'integer': 3,
    }]


def test_integration_pagination(app, example_schema):
    class ExampleListView(resources.ResourceList):
        schema = example_schema

        applied_pagination = {}

        def read_many(self, filters, pagination):
            self.applied_pagination.update(pagination)
            return []

        def get_count(self, filters):
            return 0

    application_api = api.Api(app)
    application_api.route(ExampleListView, 'example_list', '/examples/')
    response = app.test_client().get(
        '/examples/?page[size]=100&page[number]=50',
        headers=JSONAPI_HEADERS
    )
    assert response.status_code == 200
    assert ExampleListView.applied_pagination == {
        'size': 100,
        'number': 50,
    }


def test_integration_create_resource(app, example_schema, example_model):
    class ExampleListView(resources.ResourceList):
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


def test_integration_create_resource_invalid_input(app, example_schema, example_model):
    class TestSchema(marshmallow_jsonapi.Schema):
        id = fields.UUID()
        f1 = fields.Str(required=True)
        f2 = fields.Str(required=True)

        class Meta:
            type_ = 'test'
            strict = True

    class ExampleListView(resources.ResourceList):
        schema = TestSchema

        def create(self, *args, **kwargs):
            return example_model(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a4', body='Nice body.')

    json_data = json.dumps({
        'data': {
            'type': 'test',
        }
    })
    application_api = api.Api(app)
    application_api.route(ExampleListView, 'example_list', '/examples/')
    response = app.test_client().post(
        '/examples/',
        headers=JSONAPI_HEADERS,
        data=json_data,
    )
    result = json.loads(response.data.decode())
    assert result == {
        'errors': mock.ANY,
        "jsonapi": {
            "version": "1.0"
        }
    }
    assert list(sorted(result['errors'], key=lambda x: x['source']['pointer'])) == [
        {
            'detail': 'Missing data for required field.',
            'source': {'pointer': '/data/attributes/f1'}
        }, {
            'detail': 'Missing data for required field.',
            'source': {'pointer': '/data/attributes/f2'}
        }
    ]


def test_integration_get(app, example_schema, example_model):

    class ExampleDetailView(resources.ResourceDetail):
        schema = example_schema

        def read(self, id):
            return example_model(id=id, body='Gwynbelidd')

    application_api = api.Api(app)
    application_api.route(ExampleDetailView, 'example_detail', '/examples/<id>/')
    response = app.test_client().get(
        '/examples/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/',
        headers=JSONAPI_HEADERS
    )
    result = json.loads(response.data.decode())
    assert response.status_code == 200
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

    class ExampleDetailView(resources.ResourceDetail):
        schema = example_schema
        deleted_ids = []

        def destroy(self, id):
            self.deleted_ids.append(id)

    application_api = api.Api(app)
    application_api.route(ExampleDetailView, 'example_detail', '/examples/<id>/')
    response = app.test_client().delete(
        '/examples/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/',
        headers=JSONAPI_HEADERS
    )
    assert response.status_code == 204
    assert response.data == b''
    assert ExampleDetailView.deleted_ids == ['f60717a3-7dc2-4f1a-bdf4-f2804c3127a4']


def test_integration_patch(app, example_schema, example_model):

    class ExampleDetailView(resources.ResourceDetail):
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


def test_integration_patch_with_empty_response(app, example_schema, example_model):

    class ExampleDetailView(resources.ResourceDetail):
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
        headers=JSONAPI_HEADERS,
        data=json_data,
    )
    assert response.status_code == 204
    assert response.data == b''


def test_creating_view_with_dynamic_schema(app, example_schema, example_model):
    class ExampleDetailView(resources.ResourceDetail):

        def read(self, id):
            return example_model(id=id, body='Gwynbelidd')

    application_api = api.Api(app)
    application_api.route(ExampleDetailView, 'example_detail', '/examples/<id>/',
                          view_kwargs={'schema': example_schema})
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

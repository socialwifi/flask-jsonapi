import collections

from unittest import mock

import marshmallow_jsonapi

from marshmallow_jsonapi import fields

from flask_jsonapi import filters_schema
from flask_jsonapi import resource_repository_views
from flask_jsonapi import resources
from flask_jsonapi.resource_repositories import repositories


class ExampleSchema(marshmallow_jsonapi.Schema):
    id = fields.UUID(required=True)
    body = fields.Str()

    class Meta:
        type_ = 'example'
        self_view_many = 'example_list'
        self_view = 'example_detail'
        self_view_kwargs = {'example_id': '<id>'}
        strict = True


def resource_factory(id=None, body=None):
    ExampleModel = collections.namedtuple('ExampleModel', 'id body')
    return ExampleModel(id=id, body=body)


def test_integration_get_list(api, jsonapi_client):
    class ExampleListView(resources.ResourceList):
        schema = ExampleSchema

        def read_many(self, filters, sorting, pagination):
            return [
                resource_factory(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a4', body='heheh'),
                resource_factory(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a5', body='hihi'),
            ]

    api.route(ExampleListView, 'example_list', '/examples/')

    response = jsonapi_client.get('/examples/')

    assert response.status_code == 200
    result = response.get_json(force=True)
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


def test_sorting(api, jsonapi_client):
    class ExampleRepository(repositories.ResourceRepository):
        pass

    class ExampleListView(resource_repository_views.ResourceRepositoryViewSet):
        schema = ExampleSchema
        repository = ExampleRepository

    api.repository(ExampleListView(), 'example', '/examples/')
    get_list_mock = mock.MagicMock()

    with mock.patch('flask_jsonapi.resource_repositories.repositories.ResourceRepository.get_list', get_list_mock):
        jsonapi_client.get('/examples/?sort=body')

    get_list_mock.assert_called_once_with({}, ('body',), {})


def test_integration_get_list_with_pagination(api, jsonapi_client):
    class ExampleListView(resources.ResourceList):
        schema = ExampleSchema

        def read_many(self, filters, sorting, pagination):
            return [
                resource_factory(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a4', body='heheh'),
                resource_factory(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a5', body='hihi'),
            ]

        def get_count(self, filters):
            return 5

    api.route(ExampleListView, 'example_list', '/examples/')

    response = jsonapi_client.get('/examples/?page[size]=2&page[number]=1')

    assert response.status_code == 200
    result = response.get_json(force=True)
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


def test_integration_bad_accept_header(api, test_client):
    class ExampleListView(resources.ResourceList):
        schema = ExampleSchema

    api.route(ExampleListView, 'example_list', '/examples/')

    response = test_client.get('/examples/', headers={'accept': 'text/html'})

    assert response.status_code == 406
    assert response.get_json(force=True) == {
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


def test_integration_bad_content_type_header(api, test_client):
    class ExampleListView(resources.ResourceList):
        schema = ExampleSchema

    api.route(ExampleListView, 'example_list', '/examples/')

    response = test_client.post('/examples/', headers={'accept': 'application/vnd.api+json'})

    assert response.status_code == 415
    assert response.get_json(force=True) == {
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


def test_integration_get_filtered_list(api, jsonapi_client):
    class ExampleFiltersSchema(filters_schema.FilterSchema):
        basic = filters_schema.FilterField()
        listed = filters_schema.ListFilterField()
        dumb_name = filters_schema.FilterField(attribute='renamed')
        integer = filters_schema.FilterField(type_=fields.Int)
        skipped_filter = filters_schema.FilterField()

    class ExampleListView(resources.ResourceList):
        schema = ExampleSchema
        filter_schema = ExampleFiltersSchema()

        applied_filters = {}

        def read_many(self, filters, sorting, pagination):
            self.applied_filters.update(filters)
            return []

    api.route(ExampleListView, 'example_list', '/examples/')

    response = jsonapi_client.get(
        '/examples/?filter[basic]=text&filter[listed]=first,second&filter[dumb-name]=another&filter[integer]=3',
    )

    assert response.status_code == 200
    assert ExampleListView.applied_filters == {
        'basic': 'text',
        'listed': ['first', 'second'],
        'renamed': 'another',
        'integer': 3,
    }


def test_integration_pagination(api, jsonapi_client):
    class ExampleListView(resources.ResourceList):
        schema = ExampleSchema

        applied_pagination = {}

        def read_many(self, filters, sorting, pagination):
            self.applied_pagination.update(pagination)
            return []

        def get_count(self, filters):
            return 0

    api.route(ExampleListView, 'example_list', '/examples/')

    response = jsonapi_client.get('/examples/?page[size]=100&page[number]=50')

    assert response.status_code == 200
    assert ExampleListView.applied_pagination == {
        'size': 100,
        'number': 50,
    }


def test_integration_create_resource(api, jsonapi_client):
    class ExampleListView(resources.ResourceList):
        schema = ExampleSchema

        def create(self, *args, **kwargs):
            return resource_factory(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a4', body='Nice body.')

    api.route(ExampleListView, 'example_list', '/examples/')

    response = jsonapi_client.post(
        '/examples/',
        json={
            'data': {
                'type': 'example',
                'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
                'attributes': {
                    'body': "Nice body.",
                }
            }
        },
    )

    assert response.get_json(force=True) == {
        'data': {
            'type': 'example',
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'attributes': {
                'body': 'Nice body.'
            }
        },
        'jsonapi': {
            'version': '1.0'
        }
    }


def test_integration_create_resource_invalid_input(api, jsonapi_client):
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
            return resource_factory(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a4', body='Nice body.')

    api.route(ExampleListView, 'example_list', '/examples/')

    response = jsonapi_client.post(
        '/examples/',
        json={
            'data': {
                'type': 'test',
            }
        }
    )

    result = response.get_json(force=True)
    assert result == {
        'errors': mock.ANY,
        'jsonapi': {
            'version': '1.0'
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


def test_integration_get(api, jsonapi_client):
    class ExampleDetailView(resources.ResourceDetail):
        schema = ExampleSchema

        def read(self, id):
            return resource_factory(id=id, body='Gwynbelidd')

    api.route(ExampleDetailView, 'example_detail', '/examples/<id>/')

    response = jsonapi_client.get('/examples/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/')

    result = response.get_json(force=True)
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


def test_integration_delete(api, jsonapi_client):

    class ExampleDetailView(resources.ResourceDetail):
        schema = ExampleSchema
        deleted_ids = []

        def destroy(self, id):
            self.deleted_ids.append(id)

    api.route(ExampleDetailView, 'example_detail', '/examples/<id>/')

    response = jsonapi_client.delete('/examples/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/')

    assert response.status_code == 204
    assert response.data == b''
    assert ExampleDetailView.deleted_ids == ['f60717a3-7dc2-4f1a-bdf4-f2804c3127a4']


def test_integration_patch(api, jsonapi_client):
    class ExampleDetailView(resources.ResourceDetail):
        schema = ExampleSchema

        def update(self, id, data, **kwargs):
            data.pop('id')
            return resource_factory(id=id, **data)

    api.route(ExampleDetailView, 'example_list', '/examples/<id>/')

    response = jsonapi_client.patch(
        '/examples/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/',
        json={
            'data': {
                'type': 'example',
                'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
                'attributes': {
                    'body': 'Nice body.',
                }
            }
        }
    )

    assert response.get_json(force=True) == {
        'data': {
            'type': 'example',
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'attributes': {
                'body': 'Nice body.'
            }
        },
        'jsonapi': {
            'version': '1.0'
        }
    }


def test_integration_patch_with_empty_response(api, jsonapi_client):
    class ExampleDetailView(resources.ResourceDetail):
        schema = ExampleSchema

        def update(self, id, data, **kwargs):
            pass

    api.route(ExampleDetailView, 'example_list', '/examples/<id>/')

    response = jsonapi_client.patch(
        '/examples/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/',
        json={
            'data': {
                'type': 'example',
                'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
                'attributes': {
                    'body': 'Nice body.',
                }
            }
        }
    )

    assert response.status_code == 204
    assert response.data == b''


def test_creating_view_with_dynamic_schema(api, jsonapi_client):
    class ExampleDetailView(resources.ResourceDetail):
        def read(self, id):
            return resource_factory(id=id, body='Gwynbelidd')

    api.route(ExampleDetailView, 'example_detail', '/examples/<id>/', view_kwargs={'schema': ExampleSchema})

    response = jsonapi_client.get('/examples/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/')

    result = response.get_json(force=True)
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

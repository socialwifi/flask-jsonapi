import json

from marshmallow_jsonapi import Schema
from marshmallow_jsonapi import fields

from flask_jsonapi import api
from flask_jsonapi import resource_repository_views
from flask_jsonapi.resource_repositories import repositories

JSONAPI_HEADERS = {'content-type': 'application/vnd.api+json', 'accept': 'application/vnd.api+json'}


class TomatoSchema(Schema):
    id = fields.Str(required=True)
    name = fields.Str(required=True)

    class Meta:
        type_ = 'tomato'
        self_view_many = 'tomato_list'
        self_view = 'tomato_detail'
        self_view_kwargs = {'tomato_id': '<id>'}
        strict = True


class DescendantModel:
    def __init__(self, **kwargs):
        self.id = kwargs['id']
        self.name = kwargs['name']
        self.parent_id = kwargs['parent_id']


class TomatoModel:
    def __init__(self, **kwargs):
        self.id = kwargs['id']


class BadDataModel:
    def __init__(self, **kwargs):
        self.id = kwargs['id']
        self.number = kwargs['number']


class BadSchema(Schema):
    other_id = fields.Str(required=True)

    class Meta:
        type_ = 'bad'
        self_view_many = 'bad_list'
        self_view = 'bad_detail'
        self_view_kwargs = {'bad_id': '<id>'}
        strict = True


class BadDataSchema(Schema):
    id = fields.Str(required=True)
    number = fields.DateTime(required=True)

    class Meta:
        type_ = 'bad'
        self_view_many = 'bad_list'
        self_view = 'bad_detail'
        self_view_kwargs = {'bad_id': '<id>'}
        strict = True


database_simulation = {}


class BadRepository(repositories.ResourceRepository):
    def get_list(self, filters=None, sorting=None, pagination=None):
        pass

    def get_detail(self, id):
        pass


class TomatoRepository(repositories.ResourceRepository):
    def create(self, data, **kwargs):
        obj = TomatoModel(**data)
        database_simulation[data['id']] = obj
        return obj

    def get_list(self, filters=None, sorting=None, pagination=None):
        return database_simulation.values()


class BadDataRepository(repositories.ResourceRepository):
    def get_list(self, filters=None, sorting=None, pagination=None):
        return database_simulation.values()

    def get_detail(self, id):
        return database_simulation[int(id)]


class TomatoRepositoryViewSet(resource_repository_views.ResourceRepositoryViewSet):
    schema = TomatoSchema
    repository = TomatoRepository()


class BadResourceRepositoryViewSet(resource_repository_views.ResourceRepositoryViewSet):
    schema = BadSchema
    repository = BadRepository()


class BadDataResourceRepositoryViewSet(resource_repository_views.ResourceRepositoryViewSet):
    schema = BadDataSchema
    repository = BadDataRepository()


def test_bad_get_list(app):
    database_simulation.clear()
    application_api = api.Api(app)
    application_api.repository(BadResourceRepositoryViewSet(), 'bad', '/bad/')
    response = app.test_client().get(
        '/bad/',
        headers=JSONAPI_HEADERS,
    )
    result = json.loads(response.data.decode('utf-8'))
    assert result['errors'][0]['status'] == 500
    assert result['errors'][0]['detail'] == 'Must have an `id` field'


def test_bad_get_detail(app):
    database_simulation.clear()
    application_api = api.Api(app)
    application_api.repository(BadResourceRepositoryViewSet(), 'bad', '/bad/')
    response = app.test_client().get(
        '/bad/1/',
        headers=JSONAPI_HEADERS,
    )
    result = json.loads(response.data.decode('utf-8'))
    assert result['errors'][0]['status'] == 500
    assert result['errors'][0]['detail'] == 'Must have an `id` field'


def test_bad_data_get_list(app):
    database_simulation.clear()
    application_api = api.Api(app)
    application_api.repository(BadDataResourceRepositoryViewSet(), 'bad', '/bad/')
    model = BadDataModel(**{'id': 111, 'number': 1})
    database_simulation[model.id] = model
    response = app.test_client().get(
        '/bad/',
        headers=JSONAPI_HEADERS,
    )
    result = json.loads(response.data.decode('utf-8'))
    assert result['errors'][0]['status'] == 500
    assert result['errors'][0]['detail'] == "'int' object has no attribute 'isoformat'"


def test_bad_data_get_detail(app):
    database_simulation.clear()
    application_api = api.Api(app)
    application_api.repository(BadDataResourceRepositoryViewSet(), 'bad', '/bad/')
    model = BadDataModel(**{'id': 111, 'number': 1})
    database_simulation[model.id] = model
    response = app.test_client().get(
        '/bad/111/',
        headers=JSONAPI_HEADERS,
    )
    result = json.loads(response.data.decode('utf-8'))
    assert result['errors'][0]['status'] == 500
    assert result['errors'][0]['detail'] == "'int' object has no attribute 'isoformat'"


def test_create_with_missing_data(app):
    application_api = api.Api(app)
    application_api.repository(TomatoRepositoryViewSet(), 'tomatoes', '/tomatoes/')

    json_data = json.dumps({
        'data': {
            'type': 'tomato',
            'id': '61042c6f-0c83-4c26-aa74-2cfbd025879a',
        }
    })
    response = app.test_client().post(
        '/tomatoes/',
        headers=JSONAPI_HEADERS,
        data=json_data,
    )
    result = json.loads(response.data.decode('utf-8'))
    errors = result['errors']
    assert errors[0]['detail'] in 'Missing data for required field.'
    assert errors[0]['source'] == {'pointer': '/data/attributes/name'}


def test_create_with_invalid_data(app):
    application_api = api.Api(app)
    application_api.repository(TomatoRepositoryViewSet(), 'tomatoes', '/tomatoes/')

    json_data = json.dumps({
        'data': {
            'type': 'tomato',
            'id': 1234,
            'attributes': {
                'name': 'red',
            },
        },
    })
    response = app.test_client().post(
        '/tomatoes/',
        headers=JSONAPI_HEADERS,
        data=json_data,
    )
    result = json.loads(response.data.decode('utf-8'))
    errors = result['errors']
    assert errors[0]['detail'] in 'Not a valid string.'
    assert errors[0]['source'] == {'pointer': '/data/id'}

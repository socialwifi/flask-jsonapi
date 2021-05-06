import json

from marshmallow_jsonapi import Schema
from marshmallow_jsonapi import fields

from flask_jsonapi import api
from flask_jsonapi import resource_repository_views
from flask_jsonapi.marshmallow_nested_extension.field import CompleteNestedRelationship
from flask_jsonapi.marshmallow_nested_extension.schema import IdMappingSchema
from flask_jsonapi.nested import nested_resource_repositories
from flask_jsonapi.nested.nested_repository import ChildRepository
from flask_jsonapi.resource_repositories import repositories

JSONAPI_HEADERS = {'content-type': 'application/vnd.api+json', 'accept': 'application/vnd.api+json'}


class DescendantSchema(IdMappingSchema, Schema):
    id = fields.Str(required=True)
    name = fields.Str(required=False)

    class Meta:
        type_ = 'descendant'
        self_view_many = 'descendant_list'
        self_view = 'descendant_detail'
        self_view_kwargs = {'descendant_id': '<id>'}
        strict = True


class ParentSchema(Schema):
    id = fields.Str(required=True)

    class Meta:
        type_ = 'parent'
        self_view_many = 'parent_list'
        self_view = 'parent_detail'
        self_view_kwargs = {'parent_id': '<id>'}
        strict = True


class ParentSchemaAtomic(IdMappingSchema, ParentSchema):
    descendant = CompleteNestedRelationship(
        schema=DescendantSchema,
        attribute='descendant',
        many=True, include_resource_linkage=True,
        type_='descendant'
    )


class DescendantModel:
    def __init__(self, **kwargs):
        self.id = kwargs['id']
        self.name = kwargs['name']
        self.parent_id = kwargs['parent_id']


class ParentModel:
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


class DescendantRepository(repositories.ResourceRepository):
    def create(self, data, **kwargs):
        descendant = DescendantModel(**data)
        self._add_descendant_object_to_parent(data, descendant)
        return descendant

    def _add_descendant_object_to_parent(self, data, descendant):
        parent = database_simulation[data['parent_id']]
        setattr(parent, 'descendant', [descendant])


class ParentRepository(repositories.ResourceRepository):
    children_repositories = {
        'descendant': ChildRepository(
            repository=DescendantRepository(),
            foreign_parent_name='parent_id'
        )
    }

    def create(self, data, **kwargs):
        obj = ParentModel(**data)
        database_simulation[data['id']] = obj
        return obj

    def get_list(self, filters=None, sorting=None, pagination=None):
        return database_simulation.values()


class BadDataRepository(repositories.ResourceRepository):
    def get_list(self, filters=None, sorting=None, pagination=None):
        return database_simulation.values()

    def get_detail(self, id):
        return database_simulation[int(id)]


class ParentResourceRepositoryViewSet(nested_resource_repositories.NestedResourceRepositoryViewSet):
    schema = ParentSchema
    nested_schema = ParentSchemaAtomic

    def __init__(self):
        super().__init__(repository=ParentRepository())


class BadResourceRepositoryViewSet(resource_repository_views.ResourceRepositoryViewSet):
    schema = BadSchema
    repository = BadRepository()


class BadDataResourceRepositoryViewSet(resource_repository_views.ResourceRepositoryViewSet):
    schema = BadDataSchema
    repository = BadDataRepository()


def test_integration_create_nested_resource(app):
    application_api = api.Api(app)
    application_api.repository(ParentResourceRepositoryViewSet(), 'parent', '/parents/')

    json_data = json.dumps({
        'data': {
            'type': 'parent',
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'relationships': {
                'descendant': {
                    'data': [
                        {
                            'type': 'descendant',
                            'attributes': {
                                'name': 'Olga',
                                '__id__': '_tem_id_3344'
                            },
                            'id': 'f60717a3-7dc2-0000-0000-f2804c3127a4'
                        }
                    ]
                }
            }
        }
    })
    response = app.test_client().post(
        '/parents/',
        headers=JSONAPI_HEADERS,
        data=json_data,
    )
    result = json.loads(response.data.decode('utf-8'))
    expected = {
        "data": {
            "id": "f60717a3-7dc2-4f1a-bdf4-f2804c3127a4",
            "type": "parent",
            "relationships": {
                "descendant": {
                    "data":
                        [
                            {
                                "id": "f60717a3-7dc2-0000-0000-f2804c3127a4",
                                "type": "descendant",
                                "attributes": {
                                    "__id__": "_tem_id_3344",
                                    "name": "Olga"
                                }
                            }
                        ]
                }
            }
        },
        "jsonapi": {"version": "1.0"}
    }
    assert expected == result


def test_integration_get_list_use_schema_instead_of_atomic_schema(app):
    database_simulation.clear()
    application_api = api.Api(app)
    application_api.repository(ParentResourceRepositoryViewSet(), 'parent', '/parents/')
    parent = ParentModel(**{'id': 111})
    database_simulation[parent.id] = parent
    response = app.test_client().get(
        '/parents/',
        headers=JSONAPI_HEADERS,
    )
    result = json.loads(response.data.decode('utf-8'))
    expected = {
        'meta': {'count': 1},
        'data': [
            {
                'id': '111',
                'type': 'parent'
            }
        ],
        'jsonapi': {'version': '1.0'}
    }
    assert expected == result


def test_integration_get_nested_resource(app):
    database_simulation.clear()
    application_api = api.Api(app)
    application_api.repository(ParentResourceRepositoryViewSet(), 'parent', '/parents/')

    response = app.test_client().get(
        '/parents/',
        headers=JSONAPI_HEADERS,
    )
    result = json.loads(response.data.decode('utf-8'))
    expected = {
        "data": [],
        "meta": {"count": 0},
        "jsonapi": {"version": "1.0"},
    }
    assert expected == result


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

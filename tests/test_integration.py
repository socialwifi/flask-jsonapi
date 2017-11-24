import json

from marshmallow_jsonapi import Schema
from marshmallow_jsonapi import fields

from flask_jsonapi import api
from flask_jsonapi.resource_repositories import repositories
from flask_jsonapi import resource_repository_views
from flask_jsonapi.marshmallow_nested_extension.field import CompleteNestedRelationship
from flask_jsonapi.marshmallow_nested_extension.schema import IdMappingSchema
from flask_jsonapi.nested import nested_resource_repositories
from flask_jsonapi.nested.nested_repository import ChildRepository

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


class KidSchema(IdMappingSchema, Schema):
    id = fields.Str(required=True)
    name = fields.Str(required=False)

    class Meta:
        type_ = 'kid'
        self_view_many = 'kid_list'
        self_view = 'kid_detail'
        self_view_kwargs = {'kid_id': '<id>'}
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
    descendants = CompleteNestedRelationship(
        schema=DescendantSchema,
        attribute='descendants',
        many=True, include_resource_linkage=True,
        type_='descendant'
    )
    kid = CompleteNestedRelationship(
        schema=KidSchema,
        attribute='kid',
        many=False, include_resource_linkage=True,
        type_='kid'
    )


class DescendantModel:
    def __init__(self, **kwargs):
        self.id = kwargs['id']
        self.name = kwargs['name']
        self.parent_id = kwargs['parent_id']


class KidModel:
    def __init__(self, **kwargs):
        self.id = kwargs['id']
        self.name = kwargs['name']
        self.parent_id = kwargs['parent_id']


class ParentModel:
    def __init__(self, **kwargs):
        self.id = kwargs['id']


database_simulation = {}


class DescendantRepository(repositories.ResourceRepository):
    def create(self, data, **kwargs):
        descendant = DescendantModel(**data)
        self._add_descendant_object_to_parent(data, descendant)
        return descendant

    def _add_descendant_object_to_parent(self, data, descendant):
        parent = database_simulation[data['parent_id']]
        setattr(parent, 'descendants', [descendant])


class KidRepository(repositories.ResourceRepository):
    def create(self, data, **kwargs):
        kid = DescendantModel(**data)
        self._add_kid_object_to_parent(data, kid)
        return kid

    def _add_kid_object_to_parent(self, data, kid):
        parent = database_simulation[data['parent_id']]
        setattr(parent, 'kid', kid)


class ParentRepository(repositories.ResourceRepository):
    children_repositories = {
        'descendants': ChildRepository(
            repository=DescendantRepository(),
            foreign_parent_name='parent_id'
        ),
        'kid': ChildRepository(
            repository=KidRepository(),
            foreign_parent_name='parent_id'
        )
    }

    def create(self, data, **kwargs):
        obj = ParentModel(**data)
        database_simulation[data['id']] = obj
        return obj

    def get_list(self, filters=None):
        return database_simulation.values()


class ParentResourceRepositoryViewSet(nested_resource_repositories.NestedResourceRepositoryViewSet):
    schema = ParentSchema
    nested_schema = ParentSchemaAtomic

    def __init__(self):
        super().__init__(repository=ParentRepository())


def test_integration_create_nested_resource(app):
    application_api = api.Api(app)
    application_api.repository(ParentResourceRepositoryViewSet(), 'parent', '/parents/')

    json_data = json.dumps({
        'data': {
            'type': 'parent',
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'relationships': {
                'descendants': {
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
                "descendants": {
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


def test_integration_create_nested_resource_when_child_is_single_object(app):
    application_api = api.Api(app)
    application_api.repository(ParentResourceRepositoryViewSet(), 'parent', '/parents/')

    json_data = json.dumps({
        'data': {
            'type': 'parent',
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'relationships': {
                'kid': {
                    'data':
                        {
                            'type': 'kid',
                            'attributes': {
                                'name': 'Olga',
                                '__id__': '_tem_id_3344'
                            },
                            'id': 'f60717a3-7dc2-0000-0000-f2804c3127a4'
                        }

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
                "kid": {
                    "data":

                            {
                                "id": "f60717a3-7dc2-0000-0000-f2804c3127a4",
                                "type": "kid",
                                "attributes": {
                                    "__id__": "_tem_id_3344",
                                    "name": "Olga"
                                }
                            }

                }
            }
        },
        "jsonapi": {"version": "1.0"}
    }
    print(result)
    print(database_simulation)
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

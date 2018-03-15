import http
from contextlib import contextmanager

from flask_jsonapi import ResourceBase, ResourceList, ResourceDetail, response


class NestedExtenstion(ResourceBase):
    def __init__(self, *, nested_schema, **kwargs):
        super().__init__(**kwargs)
        self.nested_schema = nested_schema

    @contextmanager
    def replace_schema(self):
        schema = self.schema
        self.schema = self.nested_schema
        yield
        self.schema = schema


class NestedResourceDetail(NestedExtenstion, ResourceDetail):
    def patch(self, *args, **kwargs):
        with self.replace_schema():
            response = super().patch(*args, **kwargs)
        return response

    def prepare_response(self, data, computed_schema):
        id_map = {}
        kwargs = {'id_map': id_map}
        resource = self.update(self.resource_id, data, **kwargs)
        if resource:
            return response.JsonApiResponse(computed_schema.dump(resource, **kwargs).data)
        else:
            return response.EmptyResponse()


class NestedResourceList(NestedExtenstion, ResourceList):
    def post(self, *args, **kwargs):
        with self.replace_schema():
            response = super().post(*args, **kwargs)
        return response

    def prepare_response(self, data):
        id_map = {}
        kwargs = {'id_map': id_map}
        object = self.create(data=data, **kwargs)
        return response.JsonApiResponse(
            self.schema().dump(object, **kwargs).data,
            status=http.HTTPStatus.CREATED,
        )

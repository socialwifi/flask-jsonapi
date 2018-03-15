import http
from contextlib import contextmanager

from flask_jsonapi import ResourceBase, ResourceList, response


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

import types

import pytest

from marshmallow_jsonapi import Schema
from marshmallow_jsonapi import fields

from flask_jsonapi import data_services
from flask_jsonapi import guards
from flask_jsonapi import middlewares
from flask_jsonapi import permissions
from flask_jsonapi.data_services import exceptions as ds_exceptions


class ArticleSchema(Schema):
    id = fields.Int()
    title = fields.Str(required=True)
    owner = fields.Str()

    class Meta:
        type_ = 'articles'
        self_view = 'articles_detail'
        self_view_kwargs = {'id': '<id>'}
        self_view_many = 'articles_list'


class InMemoryArticles(data_services.DataService):
    def __init__(self):
        self.rows = {}
        self.calls = []

    def create(self, *, data):
        self.calls.append(('create', {'data': data}))
        row = types.SimpleNamespace(id=max(self.rows, default=0) + 1, title=None, owner=None)
        vars(row).update(data)
        self.rows[row.id] = row
        return row

    def read(self, *, id):
        self.calls.append(('read', {'id': id}))
        try:
            return self.rows[int(id)]
        except (KeyError, ValueError):
            raise ds_exceptions.ResourceNotFound('Article {} not found.'.format(id))

    def list(self, *, filters, sorting, pagination):
        self.calls.append(('list', {'filters': filters, 'sorting': sorting, 'pagination': pagination}))
        rows = [self.rows[key] for key in sorted(self.rows)]
        if pagination:
            start = (pagination['number'] - 1) * pagination['size']
            return data_services.ListResult(rows[start:start + pagination['size']], total=len(rows))
        return data_services.ListResult(rows, total=None)

    def update(self, *, resource, data):
        self.calls.append(('update', {'resource': resource, 'data': data}))
        vars(resource).update(data)
        return resource

    def destroy(self, *, resource):
        self.calls.append(('destroy', {'resource': resource}))
        del self.rows[resource.id]


class RecordingGuard(guards.Guard):
    def __init__(self, log):
        self.log = log

    def check(self, action):
        self.log.append('guard')


class RecordingMiddleware(middlewares.Middleware):
    def __init__(self, log, name):
        self.log = log
        self.name = name

    def read(self, *, id, inner):
        self.log.append(self.name)
        return inner.read(id=id)

    def list(self, *, filters, sorting, pagination, inner):
        self.log.append(self.name)
        return inner.list(filters=filters, sorting=sorting, pagination=pagination)


class RecordingObjectPermissions(permissions.ObjectPermissions):
    def __init__(self, log):
        self.log = log

    def create(self, *, data, inner):
        self.log.append('object permissions')
        return inner.create(data=data)

    def read(self, *, id, inner):
        self.log.append('object permissions')
        return inner.read(id=id)

    def list(self, *, filters, sorting, pagination, inner):
        self.log.append('object permissions')
        return inner.list(filters=filters, sorting=sorting, pagination=pagination)

    def update(self, *, resource, data, inner):
        self.log.append('object permissions')
        return inner.update(resource=resource, data=data)

    def destroy(self, *, resource, inner):
        self.log.append('object permissions')
        return inner.destroy(resource=resource)


@pytest.fixture
def articles():
    service = InMemoryArticles()
    service.rows[1] = types.SimpleNamespace(id=1, title='first', owner='me')
    service.rows[2] = types.SimpleNamespace(id=2, title='second', owner='other')
    return service

from contextlib import contextmanager

from flask_jsonapi import descriptors
from flask_jsonapi import exceptions
from flask_jsonapi import filters_schema
from flask_jsonapi import resources


class BaseResourceRepository:
    def create(self, data, **kwargs):
        raise exceptions.NotImplementedMethod('Creating is not implemented.')

    def get_list(self, filters=None):
        raise exceptions.NotImplementedMethod('Getting list is not implemented.')

    def get_detail(self, id):
        raise exceptions.NotImplementedMethod('Getting object is not implemented.')

    def delete(self, id):
        raise exceptions.NotImplementedMethod('Deleting is not implemented')

    def update(self, id, **data):
        raise exceptions.NotImplementedMethod('Updating is not implemented')

    @contextmanager
    def begin_transaction(self):
        yield


class ResourceRepositoryViewMixin:
    repository = BaseResourceRepository()

    def __init__(self, *, repository=None, **kwargs):
        super().__init__(**kwargs)
        if repository:
            self.repository = repository


class ResourceRepositoryDetailView(ResourceRepositoryViewMixin, resources.ResourceDetail):
    def read(self, id):
        return self.repository.get_detail(id)

    def destroy(self, id):
        self.repository.delete(id)

    def update(self, id, data):
        data['id'] = id
        self.repository.update(**data)


class ResourceRepositoryListView(ResourceRepositoryViewMixin, resources.ResourceList):
    def read_many(self, filters):
        return self.repository.get_list(filters)

    def create(self, data, **kwargs):
        return self.repository.create(data, **kwargs)


class ResourceRepositoryViewSet:
    repository = BaseResourceRepository()
    schema = descriptors.NotImplementedProperty('schema')
    filter_schema = filters_schema.FilterSchema({})
    detail_view_cls = ResourceRepositoryDetailView
    list_view_cls = ResourceRepositoryListView
    view_decorators = ()
    view_kwargs = None

    def __init__(self, *, repository=None, schema=None, filter_schema=None, detail_view_cls=None, list_view_cls=None,
                 view_decorators=None, view_kwargs=None):
        if repository:
            self.repository = repository
        if schema:
            self.schema = schema
        if filter_schema:
            self.filter_schema = filter_schema
        if detail_view_cls:
            self.detail_view_cls = detail_view_cls
        if list_view_cls:
            self.list_view_cls = list_view_cls
        if view_decorators:
            self.view_decorators = view_decorators
        if view_kwargs:
            self.view_kwargs = view_kwargs

    def as_detail_view(self, view_name):
        return self.decorate(
            self.detail_view_cls.as_view(view_name, **self.get_views_kwargs())
        )

    def as_list_view(self, view_name):
        return self.decorate(
            self.list_view_cls.as_view(view_name, filter_schema=self.filter_schema, **self.get_views_kwargs())
        )

    def decorate(self, view):
        for decorator in self.view_decorators:
            view = decorator(view)
        return view

    def get_views_kwargs(self):
        return {
            'schema': self.schema,
            'repository': self.repository,
            **(self.view_kwargs or {})
        }

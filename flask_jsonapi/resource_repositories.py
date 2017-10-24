from flask_jsonapi import descriptors
from flask_jsonapi import exceptions
from flask_jsonapi import filters_schema
from flask_jsonapi import nested_repository

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


class ResourceRepositoryViewSet:
    repository = BaseResourceRepository()
    schema = descriptors.NotImplementedProperty('schema')
    filter_schema = filters_schema.FilterSchema({})
    view_decorators = ()
    view_kwargs = None
    nested = False

    def __init__(self, *, repository=None, schema=None, filter_schema=None, view_decorators=None, view_kwargs=None, nested=False):
        if repository:
            self.repository = repository
        if schema:
            self.schema = schema
        if filter_schema:
            self.filter_schema = filter_schema
        if view_decorators:
            self.view_decorators = view_decorators
        if view_kwargs:
            self.view_kwargs = view_kwargs
        if nested:
            self.nested = nested
        if self.nested:
            self.repository = self.extend_repository()

    def as_detail_view(self, view_name):
        return self.decorate(
            ResourceRepositoryDetailView.as_view(view_name, **self.get_views_kwargs())
        )

    def as_list_view(self, view_name):
        cls = NestedResourceRepositoryListView if self.nested else ResourceRepositoryListView
        return self.decorate(
            cls.as_view(view_name, filter_schema=self.filter_schema, **self.get_views_kwargs())
        )

    def decorate(self, view):
        for decorator in self.view_decorators:
            view = decorator(view)
        return view

    def get_views_kwargs(self):
        return {
            'schema': self.schema,
            'repository': self.repository,
            'nested': self.nested,
            **(self.view_kwargs or {})
        }

    def extend_repository(self):
        return nested_repository.NestedRepository(repository=self.repository)


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


class NestedResourceRepositoryListView(ResourceRepositoryViewMixin, resources.NestedResourceList):
    def read_many(self, filters):
        return self.repository.get_list(filters)

    def create(self, data, **kwargs):
        return self.repository.create(data, **kwargs)

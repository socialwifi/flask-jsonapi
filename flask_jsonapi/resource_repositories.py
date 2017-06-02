from flask_jsonapi import descriptors
from flask_jsonapi import resources


class ResourceRepositoryViewSet:
    repository = descriptors.NotImplementedProperty('repository')
    schema = descriptors.NotImplementedProperty('schema')
    view_kwargs = None

    def __init__(self, *, repository=None, schema=None, view_kwargs=None):
        if repository:
            self.repository = repository
        if schema:
            self.schema = schema
        if view_kwargs:
            self.view_kwargs = view_kwargs

    def as_detail_view(self, view_name):
        return ResourceRepositoryDetailView.as_view(view_name, **self.get_views_kwargs())

    def as_list_view(self, view_name):
        return ResourceRepositoryListView.as_view(view_name, **self.get_views_kwargs())

    def get_views_kwargs(self):
        return {
            'schema': self.schema,
            'repository': self.repository,
            **(self.view_kwargs or {})
        }


class ResourceRepositoryViewMixin:
    repository = descriptors.NotImplementedProperty('repository')

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

    def create(self, data):
        return self.repository.create(**data)

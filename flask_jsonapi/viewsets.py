from . import descriptors
from . import filters_schema
from . import views


class ViewSet:
    detail_view_class = views.DetailView
    list_view_class = views.ListView
    middlewares = None
    data_service = descriptors.NotImplementedProperty('data_service')
    schema_class = descriptors.NotImplementedProperty('schema_class')
    filter_schema = filters_schema.FilterSchema()
    view_kwargs = None

    def as_detail_view(self, view_name):
        return self.detail_view_class.as_view(view_name, **self.get_views_kwargs())

    def as_list_view(self, view_name):
        return self.list_view_class.as_view(view_name, filter_schema=self.filter_schema, **self.get_views_kwargs())

    def get_views_kwargs(self):
        return {
            'schema': self.schema_class,
            'middlewares': self.middlewares or [],
            'data_service': self.data_service,
            **(self.view_kwargs or {}),
        }

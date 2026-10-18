from flask_jsonapi import descriptors
from flask_jsonapi import filters_schema
from flask_jsonapi import views


class ViewSet:
    detail_view_class = views.DetailView
    list_view_class = views.ListView
    schema_class = descriptors.NotImplementedProperty('schema_class')
    data_service = descriptors.NotImplementedProperty('data_service')
    filter_schema = filters_schema.FilterSchema()
    allowed_actions = frozenset()
    guards = ()
    object_permissions = None
    middlewares = ()
    view_decorators = ()

    def as_detail_view(self, view_name):
        return self._decorate(self.detail_view_class.as_view(view_name, **self.get_views_kwargs()))

    def as_list_view(self, view_name):
        return self._decorate(
            self.list_view_class.as_view(view_name, filter_schema=self.filter_schema, **self.get_views_kwargs())
        )

    def get_views_kwargs(self):
        return {
            'schema': self.schema_class,
            'data_service': self.data_service,
            'allowed_actions': self.allowed_actions,
            'guards': self.guards,
            'object_permissions': self.object_permissions,
            'middlewares': self.middlewares,
        }

    def _decorate(self, view):
        for decorator in self.view_decorators:
            view = decorator(view)
        return view

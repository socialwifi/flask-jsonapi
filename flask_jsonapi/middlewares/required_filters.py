import typing

from flask_jsonapi.data_services import exceptions

from . import base


class CheckRequiredListFilters(base.Middleware):
    def __init__(self, required_filters: typing.List[str]):
        self.required_filters = required_filters

    def list(self, *, filters, sorting, pagination, inner):
        for name in self.required_filters:
            if name not in filters:
                raise exceptions.InvalidFilterParameter('"{}" filter is required'.format(name))
        return inner.list(filters=filters, sorting=sorting, pagination=pagination)

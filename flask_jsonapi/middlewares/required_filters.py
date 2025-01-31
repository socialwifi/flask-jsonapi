from flask_jsonapi import exceptions

from . import base


class CheckRequiredListFilters(base.Middleware):
    def __init__(self, required_filters: list[str]):
        self.required_filters = required_filters

    def read_many(self, *, filters, **kwargs):
        for filter in self.required_filters:
            if filter not in filters:
                raise exceptions.InvalidFilters('"{}" filter is required'.format(filter))
        return super().read_many(filters=filters, **kwargs)

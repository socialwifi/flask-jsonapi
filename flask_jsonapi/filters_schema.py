import contextlib

import flask

from flask_jsonapi import exceptions
from flask_jsonapi import utils


class FilterField(utils.EqualityMixin):
    def __init__(self, *, field_name=None, parse_value=str):
        self.field_name_override = field_name
        self._parse_value = parse_value

    def parse(self, field_name):
        field_name = self.field_name_override or field_name
        value_string = flask.request.args['filter[{}]'.format(field_name)]
        try:
            return self.parse_value(value_string)
        except ValueError as e:
            raise exceptions.InvalidFilters('Error parsing {} filter: {}'.format(field_name, e))

    def parse_value(self, value_string):
        return self._parse_value(value_string)


class ListFilterField(FilterField):
    def parse_value(self, value_string):
        return [self._parse_value(part) for part in value_string.split(',')]


class FilterSchemaOptions:
    def __init__(self, meta=None):
        self.fields = getattr(meta, 'fields', ())


class FilterSchemaMeta(type):
    def __new__(cls, name, bases, attrs):
        attrs['declared_filters'] = cls.get_declared_filters(bases, attrs)

        new_class = super().__new__(cls, name, bases, attrs)
        new_class._meta = FilterSchemaOptions(getattr(new_class, 'Meta', None))
        new_class.base_filters = new_class.get_filters()

        return new_class

    @classmethod
    def get_declared_filters(cls, bases, attrs):
        filters = [
            (filter_name, attrs.pop(filter_name))
            for filter_name, obj in list(attrs.items())
            if isinstance(obj, FilterField)
        ]
        for base in reversed(bases):
            if hasattr(base, 'declared_filters'):
                filters = [
                    (name, f) for name, f
                    in base.declared_filters.items()
                    if name not in attrs
                ] + filters

        return dict(filters)


class FilterSchemaBase:
    def parse(self):
        result = {}
        for name, field in self.base_filters.items():
            with contextlib.suppress(KeyError):
                result[name] = field.parse(name)
        return result

    @classmethod
    def get_filters(cls):
        filters = {}
        fields = cls.get_fields()
        for field_name in fields:
            filters[field_name] = FilterField(field_name=field_name)
        filters.update(cls.declared_filters)
        return filters

    @classmethod
    def get_fields(cls):
        if not isinstance(cls._meta.fields, (list, tuple)):
            raise ValueError('`fields` option must be a list or tuple.')
        return cls._meta.fields


class FilterSchema(FilterSchemaBase, metaclass=FilterSchemaMeta):
    pass

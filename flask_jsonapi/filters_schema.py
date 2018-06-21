import re

import flask

from flask_jsonapi import exceptions
from flask_jsonapi import utils
from werkzeug import datastructures


class Operators:
    EQ = 'eq'
    NE = 'ne'
    GT = 'gt'
    LT = 'lt'
    GTE = 'gte'
    LTE = 'lte'
    CONTAINS = 'contains'
    NOTCONTAINS = 'notcontains'
    IN = 'in'
    NOTIN = 'notin'
    EXACT = 'exact'
    IEXACT = 'iexact'
    STARTSWITH = 'startswith'
    ISTARTSWITH = 'istartswith'
    IENDSWITH = 'iendswith'
    ISNULL = 'isnull'
    RANGE = 'range'
    YEAR = 'year'
    MONTH = 'month'
    DAY = 'day'


class FilterField(utils.EqualityMixin):
    default_operator = Operators.EQ

    def __init__(self, *, field_name=None, parse_value=str, operators=None, default_operator=None):
        self.default_operator = default_operator or self.default_operator
        self.operators = operators or [self.default_operator]
        self.field_name_override = field_name
        self._parse_value = parse_value

    def parse(self, field_name, remaining_filter_attributes, value):
        if len(remaining_filter_attributes) > 1:
            raise ValueError("attribute field must be specified as the last field in filter")
        try:
            value = self.parse_value(value)
            operator = self._extract_operator_if_present(remaining_filter_attributes)
        except ValueError:
            raise
        else:
            filter_attribute = '{}__{}'.format(field_name, operator or '')
            return {filter_attribute: value}

    def parse_value(self, value):
        return self._parse_value(value)

    def _extract_operator_if_present(self, remaining_filter_attributes):
        try:
            operator = remaining_filter_attributes[0]
        except IndexError:
            operator = self.default_operator
        if operator not in self.operators:
            raise ValueError("forbidden operator '{}'".format(operator))
        return operator


class ListFilterField(FilterField):
    default_operator = Operators.IN

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

    def parse(self) -> dict:
        result = {}
        for key, value in self.request_filters.items(multi=True):
            try:
                parsed_filter = self._process_filter(key, value)
                result.update(parsed_filter)
            except ValueError as exc:
                raise exceptions.InvalidFilters("Error parsing '{}={}': {}".format(key, value, exc))
        return result

    @property
    def request_filters(self) -> datastructures.MultiDict:
        return datastructures.MultiDict(
            [(key, value) for key, value
             in flask.request.args.items(multi=True)
             if key.startswith('filter')]
        )

    def _process_filter(self, key, value):
        filter_attributes = self._extract_filter_attributes(key)
        current_filter_attribute, *remaining_filter_attributes = filter_attributes
        try:
            filter_field_name = self.field_name_override_map[current_filter_attribute]
            filter_field = self.base_filters[filter_field_name]
        except KeyError:
            raise ValueError("no matching filter for attribute '{}'".format(current_filter_attribute))
        return filter_field.parse(filter_field_name, remaining_filter_attributes, value)

    def _extract_filter_attributes(self, filter_args_key):
        filter_attribute_regex = r'\[(.*?)\]'
        attributes = re.findall(filter_attribute_regex, filter_args_key)
        return tuple(attributes)

    @property
    def field_name_override_map(self):
        return {field.field_name_override or name: name for name, field in self.base_filters.items()}


class FilterSchema(FilterSchemaBase, metaclass=FilterSchemaMeta):
    pass

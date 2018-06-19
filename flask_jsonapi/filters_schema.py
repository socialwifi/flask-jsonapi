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

    def parse(self, processed_filter_path, remaining_filter_attributes, value):
        if len(remaining_filter_attributes) > 1:
            raise ValueError("attribute field must be specified as the last field in filter")
        try:
            value = self.parse_value(value)
            operator = self._extract_operator_if_present(remaining_filter_attributes)
        except ValueError:
            raise
        else:
            string_path = '.'.join(processed_filter_path)
            filter_attribute = '{}__{}'.format(string_path, operator or '')
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


class RelationshipFilterField(FilterField):
    def __init__(self, fields: dict, field_name=None):
        self.field_name_override = field_name
        self.fields = fields
        self.fields_name_map = FilterFieldNameOverrideMap(fields)

    def parse(self, processed_filter_path, remaining_filter_attribute_path, value):
        if len(remaining_filter_attribute_path) == 0:
            raise ValueError("filtering directly by relationship is forbidden")
        current_filter_attribute, *remaining_filter_attributes = remaining_filter_attribute_path
        current_filter_field_name = self.fields_name_map.get(current_filter_attribute)
        field = self.fields[current_filter_field_name]
        current_processed_filter_path = [*processed_filter_path, current_filter_field_name]
        return field.parse(current_processed_filter_path, remaining_filter_attributes, value)

    @classmethod
    def from_filter_schema(cls, filter_schema, field_name=None):
        return RelationshipFilterField(field_name=field_name, fields=filter_schema.base_filters)


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


class FilterFieldNameOverrideMap:
    def __init__(self, fields):
        self.fields = fields

    def get(self, attribute):
        try:
            filter_field_name = self.field_name_override_map[attribute]
        except KeyError:
            raise ValueError("no matching filter for attribute '{}'".format(attribute))
        else:
            return filter_field_name

    @property
    def field_name_override_map(self):
        return {field.field_name_override or name: name for name, field in self.fields.items()}


class FilterSchemaBase:
    def __init__(self):
        self.fields_name_map = FilterFieldNameOverrideMap(self.base_filters)

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
        current_filter_attribute, *remaining_filter_attribute_path = filter_attributes
        current_filter_field_name = self.fields_name_map.get(current_filter_attribute)
        filter_field = self.base_filters[current_filter_field_name]
        return filter_field.parse([current_filter_field_name], remaining_filter_attribute_path, value)

    def _extract_filter_attributes(self, filter_args_key):
        filter_attribute_regex = r'\[(.*?)\]'
        attributes = re.findall(filter_attribute_regex, filter_args_key)
        return tuple(attributes)

    @property
    def field_name_override_map(self):
        return {field.field_name_override or name: name for name, field in self.base_filters.items()}


class FilterSchema(FilterSchemaBase, metaclass=FilterSchemaMeta):
    pass

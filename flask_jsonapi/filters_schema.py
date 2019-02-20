import re

import flask

from marshmallow import exceptions as ma_exceptions
from marshmallow_jsonapi import fields as ma_fields
from marshmallow_jsonapi import schema as ma_schema
from werkzeug import datastructures

from flask_jsonapi import exceptions
from flask_jsonapi import utils


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
    default_operator = None

    def __init__(self, *, attribute=None, type_=ma_fields.Str, operators=None, default_operator=None):
        self.default_operator = default_operator or self.default_operator
        self.operators = operators or [self.default_operator]
        self.attribute = attribute
        self.type_ = type_

    def parse(self, processed_filter_path, remaining_filter_attributes, value):
        if len(remaining_filter_attributes) > 1:
            raise ValueError("attribute field must be specified as the last field in filter")
        try:
            value = self.parse_value(value)
            operator = self._extract_operator_if_present(remaining_filter_attributes)
        except ma_exceptions.ValidationError as e:
            raise ValueError from e
        else:
            filter_attribute = '__'.join(processed_filter_path)
            if operator is not None:
                filter_attribute = '{}__{}'.format(filter_attribute, operator or '')
            return {filter_attribute: value}

    def parse_value(self, value):
        if value == '':
            raise ValueError("empty filter value provided ")
        return self.type_().deserialize(value)

    def _extract_operator_if_present(self, remaining_filter_attributes):
        try:
            operator = remaining_filter_attributes[0]
        except IndexError:
            operator = self.default_operator
        if operator not in self.operators:
            raise ValueError("forbidden operator '{}'".format(operator))
        return operator


class ListFilterField(FilterField):
    def parse_value(self, value_string):
        return [self.type_().deserialize(part) for part in value_string.split(',')]


class RelationshipFilterField(FilterField):
    def __init__(self, filters_schema, field_name=None, attribute=None):
        self.field_name_override = field_name
        self.attribute = attribute
        self.fields = filters_schema.base_filters

    def parse(self, processed_filter_path, remaining_filter_attribute_path, value):
        if len(remaining_filter_attribute_path) == 0:
            raise ValueError("filtering directly by relationship is forbidden")
        current_filter_attribute, *remaining_filter_attributes = remaining_filter_attribute_path
        filter_field = self.fields[current_filter_attribute]
        current_filter_field_name = filter_field.attribute or current_filter_attribute
        current_processed_filter_path = [*processed_filter_path, current_filter_field_name]
        return filter_field.parse(current_processed_filter_path, remaining_filter_attributes, value)


class FilterSchemaOptions:
    def __init__(self, meta=None):
        self.schema = getattr(meta, 'schema', None)
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
        schema = cls.get_schema()
        if len(fields) != 0 and schema is None:
            raise ValueError('`fields` and `schema` attributes must be provided.')
        for field_name in fields:
            attribute = cls.get_model_attribute(schema, field_name)
            field_cls = utils.get_field_class(schema, field_name)
            filters[field_name] = FilterField(attribute=attribute, type_=field_cls)
        filters.update(cls.declared_filters)
        return filters

    @classmethod
    def get_schema(cls):
        schema = cls._meta.schema
        if schema is not None and not issubclass(schema, ma_schema.Schema):
            raise ValueError('`schema` option must be a `marshmallow_jsonapi.Schema` subclass.')
        return schema

    @classmethod
    def get_fields(cls):
        if not isinstance(cls._meta.fields, (list, tuple)):
            raise ValueError('`fields` option must be a list or tuple.')
        return cls._meta.fields

    @staticmethod
    def get_model_attribute(schema, field):
        if utils.is_field_mapped(schema, field):
            return schema._declared_fields[field].attribute
        if utils.is_relationship(schema, field) and schema._declared_fields[field].id_field is not None:
            return '{}__{}'.format(field, schema._declared_fields[field].id_field)
        return field

    def parse(self) -> dict:
        result = {}
        for key, value in self.request_filters.items(multi=True):
            try:
                parsed_filter = self._process_filter(key, value)
                result.update(parsed_filter)
            except (ValueError, KeyError) as exc:
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
        filter_field = self.base_filters[current_filter_attribute]
        current_filter_field_name = filter_field.attribute or current_filter_attribute
        return filter_field.parse([current_filter_field_name], remaining_filter_attribute_path, value)

    def _extract_filter_attributes(self, filter_args_key):
        filter_attribute_regex = r'\[(.*?)\]'
        attributes = re.findall(filter_attribute_regex, filter_args_key)
        attributes = map(lambda x: x.replace('-', '_'), attributes)
        return tuple(attributes)


class FilterSchema(FilterSchemaBase, metaclass=FilterSchemaMeta):
    pass

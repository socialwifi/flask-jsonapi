import contextlib

import flask

from flask_jsonapi import exceptions


class FilterSchema:
    def __init__(self, fields: dict):
        self.fields = fields

    def parse(self):
        result = {}
        for name, field in self.fields.items():
            with contextlib.suppress(KeyError):
                result[name] = field.parse(name)
        return result


class FilterField:
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

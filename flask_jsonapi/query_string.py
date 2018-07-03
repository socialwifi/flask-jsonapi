import itertools
import math
import re

import flask
from six.moves.urllib import parse

from flask_jsonapi import exceptions


class QueryStringParser:
    def parse(self):
        raise NotImplementedError


class Pagination(QueryStringParser):
    def get_links(self, *args, **kwargs):
        raise NotImplementedError


class SizeNumberPagination(Pagination):
    def parse(self):
        size = flask.request.args.get('page[size]')
        number = flask.request.args.get('page[number]')
        if size is None and number is None:
            return {}
        elif size is None or number is None:
            raise exceptions.InvalidPage('One of page parameters wrongly or not specified.')
        else:
            try:
                size = int(size)
                number = int(number)
            except ValueError:
                raise exceptions.InvalidPage('Page parameters must be integers.')
            return {'size': size, 'number': number}

    def get_links(self, page_size, current_page, total_count):
        last_page = math.ceil(total_count / page_size)
        previous_page = current_page - 1 if current_page > 1 else None
        next_page = current_page + 1 if current_page < last_page else None
        return self._format_links(current_page, previous_page, next_page, last_page)

    def _format_links(self, current_page, previous_page, next_page, last_page):
        request_args = flask.request.args.copy()
        request_args.pop('page[number]')
        base_link = '{}?{}'.format(flask.request.base_url, parse.unquote(parse.urlencode(request_args)))
        format_query_string = base_link + '&page[number]={}'
        return {
            'self': format_query_string.format(current_page),
            'first': format_query_string.format(1),
            'previous': format_query_string.format(previous_page) if previous_page else None,
            'next': format_query_string.format(next_page) if next_page else None,
            'last': format_query_string.format(last_page),
        }


class IncludeParser:
    def __init__(self, schema):
        self.schema = schema

    def parse(self):
        include_parameter = flask.request.args.get('include')
        if include_parameter:
            include_fields = tuple(include_parameter.replace('-', '_').split(','))
            try:
                self.schema().check_relations(include_fields)
            except ValueError as exc:
                raise exceptions.InvalidInclude(detail=str(exc))
            return include_fields
        else:
            return tuple()


class SparseFieldsParser:
    def __init__(self, schema):
        self.schema = schema

    def parse(self):
        sparse_fields = tuple(itertools.chain.from_iterable(self.get_sparse_fields()))
        if not sparse_fields:
            return None
        return sparse_fields

    def get_sparse_fields(self):
        for key, value in self.get_request_fields():
            resource = self.extract_resource(key)
            fields = self.extract_fields(value)
            if resource == self.schema.opts.type_:
                yield fields
            else:
                yield self.format_resource_paths(resource, fields)

    def get_request_fields(self):
        for key, value in flask.request.args.items(multi=True):
            if key.startswith('fields'):
                yield key, value

    def extract_resource(self, key):
        resource_regex = r'fields\[([a-zA-Z0-9\-\_\ ]+)\]'
        match = re.fullmatch(resource_regex, key)
        if match is None:
            raise exceptions.InvalidField(detail=key)
        resource = match.group(1)
        resource = resource.replace('-', '_')
        return resource

    def extract_fields(self, value):
        fields_regex = r'([a-zA-Z0-9\-\_\ ]+,?)+'
        match = re.fullmatch(fields_regex, value)
        if match is None:
            raise exceptions.InvalidField(detail=value)
        fields = value.replace('-', '_').split(',')
        return fields

    def format_resource_paths(self, resource, fields):
        return ['{}.{}'.format(resource, value) for value in fields]

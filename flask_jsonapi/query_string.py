import math

import flask
from six.moves.urllib import parse

from flask_jsonapi import exceptions


class Pagination:
    def parse(self):
        raise NotImplementedError

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

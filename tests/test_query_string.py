import pytest

from flask_jsonapi import exceptions
from flask_jsonapi import query_string


class TestSizeNumberPagination:
    def test_pagination(self, app):
        with app.test_request_context('/examples/?page[size]=100&page[number]=50'):
            parsed_pagination = query_string.SizeNumberPagination().parse()
            assert parsed_pagination == {'size': 100, 'number': 50}

    def test_pagination_not_provided(self, app):
        with app.test_request_context('/examples/'):
            parsed_pagination = query_string.SizeNumberPagination().parse()
            assert parsed_pagination == {}

    def test_pagination_invalid_provided(self, app):
        with app.test_request_context('/examples/?page[size]=100'):
            with pytest.raises(exceptions.InvalidPage, detail='One of page parameters wrongly or not specified.'):
                query_string.SizeNumberPagination().parse()

    def test_pagination_not_int(self, app):
        with app.test_request_context('/examples/?page[size]=100&page[number]=x'):
            with pytest.raises(exceptions.InvalidPage, detail='Page parameters must be integers.'):
                query_string.SizeNumberPagination().parse()

    def test_links_first_page(self, app):
        with app.test_request_context('/examples/?page[size]=10&page[number]=1'):
            links = query_string.SizeNumberPagination().get_links(
                page_size=10, current_page=1, total_count=50)
            assert links == {
                'self': 'http://localhost/examples/?page[size]=10&page[number]=1',
                'first': 'http://localhost/examples/?page[size]=10&page[number]=1',
                'previous': None,
                'next': 'http://localhost/examples/?page[size]=10&page[number]=2',
                'last': 'http://localhost/examples/?page[size]=10&page[number]=5',
            }

    def test_links_middle_page(self, app):
        with app.test_request_context('/examples/?page[size]=10&page[number]=1'):
            links = query_string.SizeNumberPagination().get_links(
                page_size=10, current_page=3, total_count=50)
            assert links == {
                'self': 'http://localhost/examples/?page[size]=10&page[number]=3',
                'first': 'http://localhost/examples/?page[size]=10&page[number]=1',
                'previous': 'http://localhost/examples/?page[size]=10&page[number]=2',
                'next': 'http://localhost/examples/?page[size]=10&page[number]=4',
                'last': 'http://localhost/examples/?page[size]=10&page[number]=5'
            }

    def test_links_last_page(self, app):
        with app.test_request_context('/examples/?page[size]=10&page[number]=1'):
            links = query_string.SizeNumberPagination().get_links(
                page_size=10, current_page=5, total_count=50)
            assert links == {
                'self': 'http://localhost/examples/?page[size]=10&page[number]=5',
                'first': 'http://localhost/examples/?page[size]=10&page[number]=1',
                'previous': 'http://localhost/examples/?page[size]=10&page[number]=4',
                'next': None,
                'last': 'http://localhost/examples/?page[size]=10&page[number]=5'
            }

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

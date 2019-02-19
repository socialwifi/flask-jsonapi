import pytest
from marshmallow_jsonapi import Schema
from marshmallow_jsonapi import fields

from flask_jsonapi import exceptions
from flask_jsonapi import query_string


@pytest.fixture
def user_schema():
    class UserSchema(Schema):
        id = fields.Str()
        name = fields.Str()
        age = fields.Integer()
        email_address = fields.Str(attribute='email')
        role = fields.Relationship()

        class Meta:
            type_ = 'user'
            self_view_many = 'user_list'
            self_view = 'user_detail'
            self_view_kwargs = {'user_id': '<id>'}
            strict = True

    return UserSchema


@pytest.fixture
def sort_parser(user_schema):
    return query_string.SortParser(schema=user_schema)


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
            with pytest.raises(exceptions.InvalidPage, message='One of page parameters wrongly or not specified.'):
                query_string.SizeNumberPagination().parse()

    def test_pagination_not_int(self, app):
        with app.test_request_context('/examples/?page[size]=100&page[number]=x'):
            with pytest.raises(exceptions.InvalidPage, message='Page parameters must be integers.'):
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


class TestSortParser:
    def test_sorting(self, app, sort_parser):
        with app.test_request_context('/examples/?sort=name,-age'):
            parsed_sort = sort_parser.parse()
        assert parsed_sort == ('name', '-age')

    def test_parser_change_field_name_to_attribute(self, app, sort_parser):
        with app.test_request_context('/examples/?sort=email_address'):
            parsed_sort = sort_parser.parse()
        assert parsed_sort == ('email', )

    def test_parser_raise_exception_when_field_does_not_exist(self, app, sort_parser):
        with pytest.raises(exceptions.InvalidSort):
            with app.test_request_context('/examples/?sort=some_bad_field'):
                sort_parser.parse()

    def test_parser_raise_exception_when_sorting_on_relation_field(self, app, sort_parser):
        with pytest.raises(exceptions.InvalidSort):
            with app.test_request_context('/examples/?sort=role'):
                sort_parser.parse()

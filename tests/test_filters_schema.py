import uuid

import pytest

import flask_jsonapi
from flask_jsonapi import filters_schema


class TestFiltersSchema:
    def test_filters_schema_options(self):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            class Meta:
                fields = ['id', 'body']

        assert ExampleFiltersSchema._meta.fields == ['id', 'body']

    def test_get_filters_generated(self):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            class Meta:
                fields = ['id', 'body']

        assert ExampleFiltersSchema.base_filters == {
            'id': filters_schema.FilterField(field_name='id'),
            'body': filters_schema.FilterField(field_name='body'),
        }

    def test_get_filters_combined(self):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            title = filters_schema.ListFilterField()

            class Meta:
                fields = ['id', 'body']

        assert ExampleFiltersSchema.base_filters == {
            'id': filters_schema.FilterField(field_name='id'),
            'body': filters_schema.FilterField(field_name='body'),
            'title': filters_schema.ListFilterField()
        }

    def test_get_filters_combined_override_field_from_meta(self):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            id = filters_schema.ListFilterField(field_name='identifier')

            class Meta:
                fields = ['id', 'body']

        assert ExampleFiltersSchema.base_filters == {
            'id': filters_schema.ListFilterField(field_name='identifier'),
            'body': filters_schema.FilterField(field_name='body'),
        }

    def test_inheriting_fields(self):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            title = filters_schema.FilterField()

            class Meta:
                fields = ['id', 'body']

        class ExampleFiltersSchemaDerived(ExampleFiltersSchema):
            content = filters_schema.FilterField()

            class Meta:
                fields = ['id']

        assert ExampleFiltersSchemaDerived.base_filters == {
            'id': filters_schema.FilterField(field_name='id'),
            'title': filters_schema.FilterField(),
            'content': filters_schema.FilterField(),
        }


class TestFiltersSchemaBasic:
    def test_basic(self, app):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            basic = filters_schema.FilterField()
            listed = filters_schema.ListFilterField()
            renamed = filters_schema.FilterField(field_name='dumb-name')
            integer = filters_schema.FilterField(parse_value=int)
            skipped_filter = filters_schema.FilterField()

        with app.test_request_context('?filter[basic]=text'
                                      '&filter[listed]=first,second'
                                      '&filter[dumb-name]=another'
                                      '&filter[integer]=3'):
            parsed_filters = ExampleFiltersSchema().parse()
            assert parsed_filters == {
                'basic__eq': 'text',
                'listed__in': ['first', 'second'],
                'renamed__eq': 'another',
                'integer__eq': 3,
            }

    def test_invalid_filter(self, app):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            valid = filters_schema.FilterField()

        with app.test_request_context('?filter[invalid]=text'):
            with pytest.raises(flask_jsonapi.exceptions.InvalidFilters):
                ExampleFiltersSchema().parse()

    def test_parse_value(self, app):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            identifier = filters_schema.FilterField(parse_value=uuid.UUID)

        with app.test_request_context('?filter[identifier]=11111111-1111-1111-1111-111111111111'):
            parsed_filters = ExampleFiltersSchema().parse()
            assert parsed_filters == {'identifier__eq': uuid.UUID('11111111-1111-1111-1111-111111111111')}

    def test_parse_value_error(self, app):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            identifier = filters_schema.FilterField(parse_value=uuid.UUID)
        with app.test_request_context('?filter[identifier]=1234'):
            with pytest.raises(flask_jsonapi.exceptions.InvalidFilters):
                ExampleFiltersSchema().parse()

    def test_parse_operator(self, app):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            basic = filters_schema.FilterField(operators=[filters_schema.Operators.NE])

        with app.test_request_context('?filter[basic][ne]=text'):
            parsed_filters = ExampleFiltersSchema().parse()
            assert parsed_filters == {
                'basic__ne': 'text',
            }

    def test_custom_default_operator(self, app):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            basic = filters_schema.FilterField(default_operator='like')
        with app.test_request_context('?filter[basic]=text'):
            parsed_filters = ExampleFiltersSchema().parse()
            assert parsed_filters == {'basic__like': 'text'}

    def test_operator_not_allowed(self, app):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            basic = filters_schema.FilterField(
                operators=[filters_schema.Operators.NE, filters_schema.Operators.EQ]
            )
        with app.test_request_context('?filter[basic][like]=text'):
            with pytest.raises(flask_jsonapi.exceptions.InvalidFilters):
                ExampleFiltersSchema().parse()

    def test_default_operator_not_in_operators(self, app):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            basic = filters_schema.FilterField(
                operators=[filters_schema.Operators.NE]
            )
        with app.test_request_context('?filter[basic]=text'):
            with pytest.raises(flask_jsonapi.exceptions.InvalidFilters):
                ExampleFiltersSchema().parse()

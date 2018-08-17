import uuid

import marshmallow_jsonapi
import pytest
from marshmallow_jsonapi import fields

import flask_jsonapi
from flask_jsonapi import filters_schema


class TestFiltersSchemaCreation:
    def test_simple(self):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            title = filters_schema.ListFilterField()

        assert ExampleFiltersSchema.base_filters == {
            'title': filters_schema.ListFilterField()
        }

    def test_inheriting_fields(self):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            title = filters_schema.FilterField()

        class ExampleFiltersSchemaDerived(ExampleFiltersSchema):
            content = filters_schema.FilterField()

        assert ExampleFiltersSchemaDerived.base_filters == {
            'title': filters_schema.FilterField(),
            'content': filters_schema.FilterField(),
        }

    def test_creation_using_schema(self):
        class ExampleSchema(marshmallow_jsonapi.Schema):
            id = fields.UUID(required=True)
            body = fields.Str()
            is_active = fields.Boolean(attribute='active')

            class Meta:
                type_ = 'example'

        class ExampleFiltersSchema(filters_schema.FilterSchema):
            class Meta:
                schema = ExampleSchema
                fields = ['id', 'body', 'is_active']

        assert ExampleFiltersSchema.base_filters == {
            'id': filters_schema.FilterField(attribute='id', type_=fields.UUID),
            'body': filters_schema.FilterField(attribute='body'),
            'is_active': filters_schema.FilterField(attribute='active', type_=fields.Boolean),
        }


class TestFiltersSchemaBasic:
    def test_basic(self, app):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            basic = filters_schema.FilterField()
            listed = filters_schema.ListFilterField()
            dumb_name = filters_schema.FilterField(attribute='renamed')
            integer = filters_schema.FilterField(type_=fields.Int)
            skipped_filter = filters_schema.FilterField()

        with app.test_request_context('?filter[basic]=text'
                                      '&filter[listed]=first,second'
                                      '&filter[dumb-name]=another'
                                      '&filter[integer]=3'):
            parsed_filters = ExampleFiltersSchema().parse()
            assert parsed_filters == {
                'basic': 'text',
                'listed': ['first', 'second'],
                'renamed': 'another',
                'integer': 3,
            }

    def test_invalid_filter(self, app):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            valid = filters_schema.FilterField()

        with app.test_request_context('?filter[invalid]=text'):
            with pytest.raises(flask_jsonapi.exceptions.InvalidFilters):
                ExampleFiltersSchema().parse()

    def test_parse_value(self, app):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            identifier = filters_schema.FilterField(type_=fields.UUID)

        with app.test_request_context('?filter[identifier]=11111111-1111-1111-1111-111111111111'):
            parsed_filters = ExampleFiltersSchema().parse()
            assert parsed_filters == {'identifier': uuid.UUID('11111111-1111-1111-1111-111111111111')}

    def test_parse_value_error(self, app):
        class ExampleFiltersSchema(filters_schema.FilterSchema):
            identifier = filters_schema.FilterField(type_=fields.UUID)
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

    def test_parse_generated_from_schema(self, app):
        class ExampleSchema(marshmallow_jsonapi.Schema):
            id = fields.UUID(required=True)
            first_body = fields.Str()
            second_body = fields.Str()
            is_active = fields.Boolean(attribute='active')
            related = fields.Relationship(attribute='related_id')
            other_related = fields.Relationship(id_field='id')

            class Meta:
                type_ = 'example'

        class ExampleFiltersSchema(filters_schema.FilterSchema):

            class Meta:
                schema = ExampleSchema
                fields = ['id', 'first_body', 'second_body', 'is_active', 'related', 'other_related']

        with app.test_request_context('?filter[id]=11111111-1111-1111-1111-111111111111'
                                      '&filter[first-body]=first-text'
                                      '&filter[second_body]=second-text'
                                      '&filter[is-active]=true'
                                      '&filter[related]=456'
                                      '&filter[other-related]=789'):
            parsed_filters = ExampleFiltersSchema().parse()
            assert parsed_filters == {
                'id': uuid.UUID('11111111-1111-1111-1111-111111111111'),
                'first_body': 'first-text',
                'second_body': 'second-text',
                'active': True,
                'related_id': '456',
                'other_related__id': '789',
            }


class TestFiltersSchemaRelationship:
    def test_basic(self, app):
        class FirstFiltersSchema(filters_schema.FilterSchema):
            id = filters_schema.FilterField()

        class SecondFiltersSchema(filters_schema.FilterSchema):
            attribute = filters_schema.FilterField()
            other_relationship = filters_schema.RelationshipFilterField(
                FirstFiltersSchema, attribute='renamed_relationship'
            )

        class ThirdFiltersSchema(filters_schema.FilterSchema):
            relationship = filters_schema.RelationshipFilterField(SecondFiltersSchema)

        with app.test_request_context('?filter[relationship][other_relationship][id]=123'
                                      '&filter[relationship][attribute]=text'):
            parsed_filters = ThirdFiltersSchema().parse()
            assert parsed_filters == {
                'relationship__renamed_relationship__id': '123',
                'relationship__attribute': 'text',
            }

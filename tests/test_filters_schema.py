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

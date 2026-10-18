import pytest

from flask_jsonapi import middlewares
from flask_jsonapi.data_services import exceptions as ds_exceptions


def test_required_filters(articles):
    pipeline = middlewares.build_pipeline([middlewares.CheckRequiredListFilters(['author_id'])], articles)

    with pytest.raises(ds_exceptions.InvalidFilterParameter) as error_info:
        pipeline.list(filters={}, sorting=[], pagination={})

    assert error_info.value.detail == '"author_id" filter is required'
    assert articles.calls == []


def test_required_filters_reports_first_missing_and_passes_when_present(articles):
    pipeline = middlewares.build_pipeline(
        [middlewares.CheckRequiredListFilters(['author_id', 'owner'])], articles)

    with pytest.raises(ds_exceptions.InvalidFilterParameter) as error_info:
        pipeline.list(filters={'owner': 'me'}, sorting=[], pagination={})
    assert error_info.value.detail == '"author_id" filter is required'

    pipeline.list(filters={'author_id': 1, 'owner': 'me'}, sorting=[], pagination={})
    assert articles.calls[-1][0] == 'list'

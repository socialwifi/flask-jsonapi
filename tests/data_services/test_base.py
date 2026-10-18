import dataclasses

import pytest

from flask_jsonapi import data_services
from flask_jsonapi.data_services import base


@pytest.mark.parametrize(argnames='call', argvalues=[
    lambda service: service.create(data={}),
    lambda service: service.read(id=1),
    lambda service: service.list(filters=None, sorting=None, pagination=None),
    lambda service: service.update(resource=object(), data={}),
    lambda service: service.destroy(resource=object()),
], ids=['create', 'read', 'list', 'update', 'destroy'])
def test_base_data_service_methods_are_not_implemented(call):
    with pytest.raises(NotImplementedError):
        call(base.DataService())


def test_data_service_has_no_count():
    assert not hasattr(base.DataService, 'count')


def test_list_result_holds_items_and_total_and_is_frozen():
    result = data_services.ListResult(['a'], total=7)

    assert (result.items, result.total) == (['a'], 7)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.total = None

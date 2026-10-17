import types

from unittest import mock

import pytest

from flask_jsonapi import data_services
from flask_jsonapi import exceptions


def test_update_puts_resource_id_into_data_and_returns_result():
    repository = mock.Mock()
    adapter = data_services.LegacyRepositoryAdapter(repository)
    result = adapter.update(resource=types.SimpleNamespace(id=7), data={'title': 'x'})
    repository.update.assert_called_once_with({'title': 'x', 'id': 7})
    assert result is repository.update.return_value


def test_destroy_passes_resource_id_to_legacy_delete():
    repository = mock.Mock()
    data_services.LegacyRepositoryAdapter(repository).destroy(resource=types.SimpleNamespace(id=7))
    repository.delete.assert_called_once_with(7)


def test_reads_and_create_are_forwarded_to_legacy_methods():
    repository = mock.Mock()
    adapter = data_services.LegacyRepositoryAdapter(repository)
    adapter.create(data={'a': 1})
    adapter.read(id=3)
    repository.create.assert_called_once_with({'a': 1})
    repository.get_detail.assert_called_once_with(3)


def test_paginated_list_returns_items_and_legacy_count():
    repository = mock.Mock()
    result = data_services.LegacyRepositoryAdapter(repository).list(
        filters={'f': 1}, sorting=['s'], pagination={'size': 1, 'number': 1})
    repository.get_list.assert_called_once_with({'f': 1}, ['s'], {'size': 1, 'number': 1})
    repository.get_count.assert_called_once_with({'f': 1})
    assert result == data_services.ListResult(repository.get_list.return_value, repository.get_count.return_value)


def test_unpaginated_list_does_not_count():
    repository = mock.Mock()
    result = data_services.LegacyRepositoryAdapter(repository).list(filters={}, sorting=[], pagination={})
    assert result == data_services.ListResult(repository.get_list.return_value, None)
    assert not repository.get_count.called


def test_adapter_has_no_count():
    assert not hasattr(data_services.LegacyRepositoryAdapter, 'count')


def test_legacy_jsonapi_exceptions_pass_through():
    repository = mock.Mock()
    repository.get_detail.side_effect = exceptions.ObjectNotFound(source={}, detail='Missing.')
    with pytest.raises(exceptions.ObjectNotFound):
        data_services.LegacyRepositoryAdapter(repository).read(id=1)

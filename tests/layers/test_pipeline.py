from unittest import mock

import pytest

from flask_jsonapi import data_services
from flask_jsonapi import middlewares
from flask_jsonapi.middlewares import pipeline as pipeline_module


class Recording(middlewares.Middleware):
    def __init__(self, name, events):
        self.name = name
        self.events = events

    def update(self, *, resource, data, inner):
        self.events.append(f'{self.name}:before')
        result = inner.update(resource=resource, data=data)
        self.events.append(f'{self.name}:after')
        return result


def test_empty_pipeline_is_the_data_service():
    data_service = mock.Mock(spec=data_services.DataService)
    assert middlewares.build_pipeline([], data_service) is data_service


def test_middlewares_run_in_list_order():
    events = []
    data_service = mock.Mock(spec=data_services.DataService)
    data_service.update.side_effect = lambda **kwargs: events.append('service')
    pipeline = middlewares.build_pipeline([Recording('a', events), Recording('b', events)], data_service)
    pipeline.update(resource='r', data={})
    assert events == ['a:before', 'b:before', 'service', 'b:after', 'a:after']


@pytest.mark.parametrize('method, kwargs', [
    ('create', {'data': {'a': 1}}),
    ('read', {'id': 1}),
    ('list', {'filters': {}, 'sorting': [], 'pagination': {}}),
    ('update', {'resource': 'r', 'data': {}}),
    ('destroy', {'resource': 'r'}),
])
def test_base_middleware_passes_every_method_through(method, kwargs):
    data_service = mock.Mock(spec=data_services.DataService)
    pipeline = middlewares.build_pipeline([middlewares.Middleware()], data_service)
    result = getattr(pipeline, method)(**kwargs)
    getattr(data_service, method).assert_called_once_with(**kwargs)
    assert result is getattr(data_service, method).return_value


@pytest.mark.parametrize('cls', [middlewares.Middleware, pipeline_module._Link])
def test_pipeline_has_no_count(cls):
    assert not hasattr(cls, 'count')


def test_middleware_can_call_inner_more_than_once():
    class ReadsBeforeUpdate(middlewares.Middleware):
        def update(self, *, resource, data, inner):
            inner.read(id=resource)
            return inner.update(resource=resource, data=data)

    data_service = mock.Mock(spec=data_services.DataService)
    pipeline = middlewares.build_pipeline([ReadsBeforeUpdate(), middlewares.Middleware()], data_service)
    pipeline.update(resource=1, data={})
    data_service.read.assert_called_once_with(id=1)
    data_service.update.assert_called_once_with(resource=1, data={})

import logging

import flask_jsonapi

from flask_jsonapi import descriptors
from flask_jsonapi import exceptions as api_exceptions
from flask_jsonapi import filters_schema
from flask_jsonapi import data_services
from flask_jsonapi import middlewares as middlewares_

logger = logging.getLogger(__name__)


class DetailView(flask_jsonapi.ResourceDetail):
    def __init__(self, middlewares: list[middlewares_.Middleware], data_service: data_services.DataService, **kwargs):
        super().__init__(**kwargs)
        self._data_service = data_service
        self._pipeline = self._pipeline_factory(middlewares)

    @classmethod
    def _pipeline_factory(cls, middlewares: list[middlewares_.Middleware]):
        pipeline = middlewares.copy()
        pipeline.append(middlewares_.DataServiceAdapter())
        return pipeline

    def read(self, id):
        middlewares = iter(self._pipeline)
        try:
            return next(middlewares).read(middlewares=middlewares, data_service=self._data_service, id=id)
        except data_services.ResourceNotFound as e:
            raise api_exceptions.ObjectNotFound(detail=e.detail)
        except data_services.DataServiceException as e:
            raise api_exceptions.JsonApiException(detail=e.detail)

    def update(self, id, data):
        middlewares = iter(self._pipeline)
        try:
            return next(middlewares).update(middlewares=middlewares, data_service=self._data_service, id=id, data=data)
        except data_services.DataServiceException as e:
            raise api_exceptions.JsonApiException(detail=e.detail)

    def destroy(self, id):
        middlewares = iter(self._pipeline)
        try:
            return next(middlewares).destroy(middlewares=middlewares, data_service=self._data_service, id=id)
        except data_services.DataServiceException as e:
            raise api_exceptions.JsonApiException(detail=e.detail)


class ListView(flask_jsonapi.ResourceList):
    def __init__(self, middlewares: list[middlewares_.Middleware], data_service: data_services.DataService, **kwargs):
        super().__init__(**kwargs)
        self._data_service = data_service
        self._pipeline = self._pipeline_factory(middlewares)

    @classmethod
    def _pipeline_factory(cls, middlewares: list[middlewares_.Middleware]):
        pipeline = middlewares.copy()
        pipeline.append(middlewares_.DataServiceAdapter())
        return pipeline

    def create(self, data):
        middlewares = iter(self._pipeline)
        try:
            return next(middlewares).create(middlewares=middlewares, data_service=self._data_service, data=data)
        except data_services.DataServiceException as e:
            raise api_exceptions.JsonApiException(detail=e.detail)

    def read_many(self, filters, sorting, pagination):
        middlewares = iter(self._pipeline)
        try:
            return next(middlewares).read_many(
                middlewares=middlewares, data_service=self._data_service, filters=filters, sorting=sorting,
                pagination=pagination)
        except data_services.InvalidSortParameter as e:
            raise api_exceptions.InvalidSort(detail=e.detail)
        except data_services.DataServiceException as e:
            raise api_exceptions.JsonApiException(detail=e.detail)

    def get_count(self, filters):
        return self._data_service.get_count(filters=filters)


class ViewSet:
    detail_view_cls = DetailView
    list_view_cls = ListView
    middlewares = None
    data_service = None
    schema = descriptors.NotImplementedProperty('schema')
    filter_schema = filters_schema.FilterSchema()
    view_kwargs = None

    def as_detail_view(self, view_name):
        return self.detail_view_cls.as_view(view_name, **self.get_views_kwargs())

    def as_list_view(self, view_name):
        return self.list_view_cls.as_view(view_name, filter_schema=self.filter_schema, **self.get_views_kwargs())

    def get_views_kwargs(self):
        return {
            'schema': self.schema,
            'middlewares': self.middlewares or [],
            'data_service': self.data_service,
            **(self.view_kwargs or {}),
        }

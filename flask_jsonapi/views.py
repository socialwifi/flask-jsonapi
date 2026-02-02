import logging

from . import data_services
from . import exceptions
from . import middlewares as middlewares_
from . import resources

logger = logging.getLogger(__name__)


class DetailView(resources.ResourceDetail):
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
            raise exceptions.ObjectNotFound(detail=e.detail)
        except data_services.DataServiceException as e:
            raise exceptions.JsonApiException(detail=e.detail)

    def update(self, id, data):
        middlewares = iter(self._pipeline)
        try:
            return next(middlewares).update(middlewares=middlewares, data_service=self._data_service, id=id, data=data)
        except data_services.DataServiceException as e:
            raise exceptions.JsonApiException(detail=e.detail)

    def destroy(self, id):
        middlewares = iter(self._pipeline)
        try:
            return next(middlewares).destroy(middlewares=middlewares, data_service=self._data_service, id=id)
        except data_services.DataServiceException as e:
            raise exceptions.JsonApiException(detail=e.detail)


class ListView(resources.ResourceList):
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
            raise exceptions.JsonApiException(detail=e.detail)

    def read_many(self, filters, sorting, pagination):
        middlewares = iter(self._pipeline)
        try:
            return next(middlewares).read_many(
                middlewares=middlewares, data_service=self._data_service, filters=filters, sorting=sorting,
                pagination=pagination)
        except data_services.InvalidSortParameter as e:
            raise exceptions.InvalidSort(detail=e.detail)
        except data_services.DataServiceException as e:
            raise exceptions.JsonApiException(detail=e.detail)

    def get_count(self, filters):
        return self._data_service.get_count(filters=filters)

import functools
import logging

from flask_jsonapi import exceptions
from flask_jsonapi import resources
from flask_jsonapi import response
from flask_jsonapi.data_services import exceptions as data_service_exceptions
from flask_jsonapi.middlewares import build_pipeline

logger = logging.getLogger(__name__)


def translate_data_service_exception(error):
    if isinstance(error, data_service_exceptions.ResourceNotFound):
        return exceptions.ObjectNotFound(detail=error.detail)
    if isinstance(error, data_service_exceptions.PermissionDenied):
        return exceptions.ForbiddenError(detail=error.detail)
    if isinstance(error, data_service_exceptions.InvalidData):
        if error.field:
            pointer = '/data/attributes/{}'.format(error.field)
            return exceptions.AttributeValidationError(error.detail, source={'pointer': pointer})
        return exceptions.UnprocessableEntity(detail=error.detail)
    if isinstance(error, data_service_exceptions.Conflict):
        return exceptions.Conflict(detail=error.detail)
    if isinstance(error, data_service_exceptions.InvalidSortParameter):
        return exceptions.InvalidSort(error.detail)
    if isinstance(error, data_service_exceptions.InvalidFilterParameter):
        return exceptions.InvalidFilters(error.detail)
    if isinstance(error, data_service_exceptions.Unavailable):
        return exceptions.ServiceUnavailable(detail=error.detail)
    logger.exception('Unexpected data service error', exc_info=error)
    return exceptions.JsonApiException(status=500, title='Internal server error')


def _translating_data_service_errors(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except data_service_exceptions.DataServiceException as error:
            raise translate_data_service_exception(error) from error
    return wrapper


class LayeredViewMixin:
    def __init__(self, *, data_service, allowed_actions=(), guards=(), object_permissions=None, middlewares=(),
                 **kwargs):
        super().__init__(**kwargs)
        self.allowed_actions = allowed_actions
        self.guards = guards
        layers = middlewares if object_permissions is None else [object_permissions, *middlewares]
        self.pipeline = build_pipeline(layers, data_service)

    def _authorize(self, action):
        if action not in self.allowed_actions:
            raise exceptions.MethodNotAllowed(detail='{} is not allowed for this resource'.format(action.capitalize()))
        for guard in self.guards:
            guard.check(action)


class DetailView(LayeredViewMixin, resources.ResourceDetail):
    def get(self, *args, **kwargs):
        self._authorize(resources.Actions.read)
        return super().get(*args, **kwargs)

    def patch(self, *args, **kwargs):
        self._authorize(resources.Actions.update)
        return super().patch(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._authorize(resources.Actions.destroy)
        return super().delete(*args, **kwargs)

    @_translating_data_service_errors
    def read(self, id):
        return self._read_resource(id)

    @_translating_data_service_errors
    def update(self, id, data, **kwargs):
        resource = self._read_resource(id)
        data_without_id = {key: value for key, value in data.items() if key != 'id'}
        return self.pipeline.update(resource=resource, data=data_without_id)

    @_translating_data_service_errors
    def destroy(self, id):
        resource = self._read_resource(id)
        return self.pipeline.destroy(resource=resource)

    def _read_resource(self, id):
        resource = self.pipeline.read(id=id)
        if resource is None:
            raise exceptions.ObjectNotFound()
        return resource


class ListView(LayeredViewMixin, resources.ListResourceBase):
    def get(self, *args, **kwargs):
        self._authorize(resources.Actions.list)
        query = self._parse_list_query()
        result = self._list(**query)
        return response.JsonApiListResponse(
            response_data=self._dump_list(result.items),
            links=self._pagination_links(query['pagination'], result),
        )

    def post(self, *args, **kwargs):
        self._authorize(resources.Actions.create)
        return super().post(*args, **kwargs)

    @_translating_data_service_errors
    def _list(self, filters, sorting, pagination):
        return self.pipeline.list(filters=filters, sorting=sorting, pagination=pagination)

    def _pagination_links(self, parsed_pagination, result):
        if not parsed_pagination:
            return {}
        page_size = parsed_pagination['size']
        current_page = parsed_pagination['number']
        if result.total is None:
            return self.pagination.get_links_without_total(page_size, current_page, len(result.items))
        return self.pagination.get_links(page_size, current_page, result.total)

    @_translating_data_service_errors
    def create(self, data, **kwargs):
        return self.pipeline.create(data=data)

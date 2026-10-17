import functools
import http
import logging

import marshmallow
import werkzeug.exceptions

from flask import request
from flask import views
from marshmallow_jsonapi import exceptions as marshmallow_jsonapi_exceptions

from flask_jsonapi import decorators
from flask_jsonapi import descriptors
from flask_jsonapi import exceptions
from flask_jsonapi import filters_schema
from flask_jsonapi import query_string
from flask_jsonapi import response

logger = logging.getLogger(__name__)


class ResourceBase(views.View):
    schema = descriptors.NotImplementedProperty('schema')
    args = None
    kwargs = None

    def __init__(self, *, schema=None):
        if schema:
            self.schema = schema
        self.sort_parser = query_string.SortParser(schema=self.schema)
        self.include_parser = query_string.IncludeParser(schema=self.schema)
        self.sparse_fields_parser = query_string.SparseFieldsParser(schema=self.schema)

    @classmethod
    def as_view(cls, name, *class_args, **class_kwargs):
        view = super().as_view(name, *class_args, **class_kwargs)
        return decorators.check_headers(view)

    def dispatch_request(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        handler = self._handler_for(request.method)
        try:
            return handler(request, *args, **kwargs).make_response()
        except exceptions.JsonApiException as e:
            return response.JsonApiErrorResponse(
                e.to_dict(),
                status=e.status
            ).make_response()
        except werkzeug.exceptions.HTTPException as e:
            if e.response is not None:
                return e.response
            if e.code is None:
                return self._internal_server_error_response()
            return response.JsonApiErrorResponse(
                {'status': e.code, 'title': e.name},
                headers=self._forwarded_headers(e),
                status=e.code
            ).make_response()
        except Exception:
            logger.exception('Unhandled exception in %s %s', request.method, request.path)
            return self._internal_server_error_response()

    def _handler_for(self, method):
        handler = getattr(self, method.lower(), None)
        if handler is None and method == 'HEAD':
            handler = getattr(self, 'get', None)
        return handler or self._http_method_not_allowed

    @staticmethod
    def _forwarded_headers(http_exception):
        return [
            (name, value) for name, value in http_exception.get_headers()
            if name.lower() not in ('content-type', 'content-length')
        ]

    @staticmethod
    def _internal_server_error_response():
        return response.JsonApiErrorResponse(
            {'status': http.HTTPStatus.INTERNAL_SERVER_ERROR.value, 'title': 'Internal server error'},
            status=http.HTTPStatus.INTERNAL_SERVER_ERROR
        ).make_response()

    def _http_method_not_allowed(self, request, *args, **kwargs):
        logger.error(
            'Method Not Allowed (%s): %s', request.method, request.path,
            extra={'status_code': http.HTTPStatus.METHOD_NOT_ALLOWED, 'request': request}
        )
        raise exceptions.MethodNotAllowed()


class ResourceDetail(ResourceBase):
    methods = ['GET', 'DELETE', 'PATCH']
    id_kwarg = 'id'

    def get(self, *args, **kwargs):
        resource = self.read(self.resource_id)
        include_fields = self.include_parser.parse()
        sparse_fields = self.sparse_fields_parser.parse()
        try:
            data = self.schema(include_data=include_fields, only=sparse_fields).dump(resource)
        except marshmallow.ValidationError as e:
            raise exceptions.JsonApiException(detail='marshmallow.ValidationError', source=e.messages)
        else:
            return response.JsonApiResponse(data)

    def delete(self, *args, **kwargs):
        self.destroy(self.resource_id)
        return response.EmptyResponse()

    def patch(self, *args, **kwargs):
        self._check_body_id()
        computed_schema = self.schema(partial=True)
        try:
            data = computed_schema.load(request.get_json())
        except marshmallow_jsonapi_exceptions.IncorrectTypeError as e:
            return response.JsonApiErrorResponse.from_marshmallow_errors(e.messages, status=http.HTTPStatus.CONFLICT)
        except marshmallow.ValidationError as e:
            return response.JsonApiErrorResponse.from_marshmallow_errors(e.messages)
        else:
            self._check_loaded_id(data)
            resource = self.update(self.resource_id, data)
            if resource:
                return response.JsonApiResponse(computed_schema.dump(resource))
            else:
                return response.EmptyResponse()

    def _check_body_id(self):
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get('data'), dict):
            return
        body_id = body['data'].get('id')
        if body_id is not None and str(body_id) != str(self.resource_id):
            raise self._id_conflict()

    def _check_loaded_id(self, data):
        # marshmallow-jsonapi lets an "id" attribute overwrite data.id in the loaded payload.
        if 'id' in data and str(data['id']) != str(self.resource_id):
            raise self._id_conflict()

    @staticmethod
    def _id_conflict():
        return exceptions.Conflict(
            source={'pointer': '/data/id'},
            detail='Resource id in the request body does not match the URL.',
        )

    @property
    def resource_id(self):
        return self.kwargs[self.id_kwarg]

    def read(self, id):
        raise NotImplementedError

    def update(self, id, data, **kwargs):
        raise NotImplementedError

    def destroy(self, id):
        raise NotImplementedError


class ListResourceBase(ResourceBase):
    methods = ['GET', 'POST']
    filter_schema = filters_schema.FilterSchema()
    pagination = query_string.SizeNumberPagination()

    def __init__(self, *, filter_schema=None, **kwargs):
        super().__init__(**kwargs)
        if filter_schema:
            self.filter_schema = filter_schema

    def _parse_list_query(self):
        return {
            'filters': self.filter_schema.parse(),
            'sorting': self.sort_parser.parse(),
            'pagination': self.pagination.parse(),
        }

    def _dump_list(self, objects_list):
        include_fields = self.include_parser.parse()
        sparse_fields = self.sparse_fields_parser.parse()
        try:
            return self.schema(many=True, include_data=include_fields, only=sparse_fields).dump(objects_list)
        except marshmallow.ValidationError as e:
            raise exceptions.JsonApiException(detail='marshmallow.ValidationError', source=e.messages)

    def post(self, *args, **kwargs):
        try:
            data = self.schema().load(request.get_json())
        except marshmallow_jsonapi_exceptions.IncorrectTypeError as e:
            return response.JsonApiErrorResponse.from_marshmallow_errors(e.messages)
        except marshmallow.ValidationError as e:
            return response.JsonApiErrorResponse.from_marshmallow_errors(e.messages)
        else:
            return self.prepare_response(data)

    def prepare_response(self, data):
        object = self.create(data=data)
        return response.JsonApiResponse(
            self.schema().dump(object),
            status=http.HTTPStatus.CREATED,
        )

    def create(self, data, **kwargs):
        raise NotImplementedError


class ResourceList(ListResourceBase):
    def get(self, *args, **kwargs):
        query = self._parse_list_query()
        objects_list = self.read_many(**query)
        objects = self._dump_list(objects_list)
        pagination_links = self.get_pagination_links(query['pagination'], query['filters'])
        return response.JsonApiListResponse(
            response_data=objects,
            links=pagination_links,
        )

    def get_pagination_links(self, parsed_pagination, parsed_filters):
        if parsed_pagination:
            page_size = parsed_pagination['size']
            current_page = parsed_pagination['number']
            total_count = self.get_count(filters=parsed_filters)
            pagination_links = self.pagination.get_links(page_size, current_page, total_count)
        else:
            pagination_links = {}
        return pagination_links

    def read_many(self, filters, sorting, pagination):
        raise NotImplementedError

    def get_count(self, filters):
        raise NotImplementedError


class Actions:
    create = 'create'
    read = 'fetch'
    list = 'fetch list'
    read_many = list
    update = 'update'
    destroy = 'delete'


def check_allowed_action(action: str):
    """Deprecated since 1.5.0, use the allowed_actions of flask_jsonapi.ViewSet."""

    def decorate(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if action not in self.allowed_actions:
                raise exceptions.MethodNotAllowed('{} is not allowed for this resource'.format(action.capitalize()))
            return func(self, *args, **kwargs)
        return wrapper
    return decorate


class AllowedActionsResourceMixin:
    """Deprecated since 1.5.0, use the allowed_actions of flask_jsonapi.ViewSet."""

    allowed_actions = ()

    def __init__(self, *, allowed_actions=None,  **kwargs):
        super().__init__(**kwargs)
        if allowed_actions:
            self.allowed_actions = allowed_actions


class AllowedActionsResourceDetailMixin(AllowedActionsResourceMixin):
    """Deprecated since 1.5.0, use flask_jsonapi.DetailView."""

    @check_allowed_action(Actions.read)
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    @check_allowed_action(Actions.update)
    def patch(self, *args, **kwargs):
        return super().patch(*args, **kwargs)

    @check_allowed_action(Actions.destroy)
    def delete(self, *args, **kwargs):
        return super().delete(*args, **kwargs)


class AllowedActionsResourceListMixin(AllowedActionsResourceMixin):
    """Deprecated since 1.5.0, use flask_jsonapi.ListView."""

    @check_allowed_action(Actions.create)
    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)

    @check_allowed_action(Actions.read_many)
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class AllowedActionsResourceViewSetMixin:
    """Deprecated since 1.5.0, use flask_jsonapi.ViewSet."""

    detail_view_cls: AllowedActionsResourceMixin
    list_view_cls: AllowedActionsResourceMixin
    allowed_actions = ()

    def get_views_kwargs(self):
        kwargs = super().get_views_kwargs()
        kwargs['allowed_actions'] = self.allowed_actions
        return kwargs

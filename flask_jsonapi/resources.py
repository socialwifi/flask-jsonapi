import functools
import http
import logging

import marshmallow

from flask import helpers
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
        handler = getattr(self, request.method.lower(), self._http_method_not_allowed)
        try:
            response_object = handler(request, *args, **kwargs)
        except exceptions.JsonApiException as e:
            return response.JsonApiErrorResponse(
                e.to_dict(),
                status=e.status
            ).make_response()
        else:
            return response_object.make_response()

    def _http_method_not_allowed(self, request, *args, **kwargs):
        logger.error(
            'Method Not Allowed (%s): %s', request.method, request.path,
            extra={'status_code': http.HTTPStatus.METHOD_NOT_ALLOWED, 'request': request}
        )
        return helpers.make_response('Method Not Allowed.', http.HTTPStatus.METHOD_NOT_ALLOWED)


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
        except (AttributeError, KeyError, ValueError) as e:
            logger.error(
                'Error Processing Request',
                extra={'status_code': http.HTTPStatus.BAD_REQUEST, 'request': request, 'exception': e}
            )
            raise exceptions.JsonApiException(detail=str(e), source={'component': 'schema'})
        else:
            return response.JsonApiResponse(data)

    def delete(self, *args, **kwargs):
        self.destroy(self.resource_id)
        return response.EmptyResponse()

    def patch(self, *args, **kwargs):
        computed_schema = self.schema(partial=True)
        try:
            data = computed_schema.load(request.get_json())
        except marshmallow.ValidationError as e:
            return response.JsonApiErrorResponse.from_marshmallow_errors(e.messages)
        else:
            resource = self.update(self.resource_id, data)
            if resource:
                return response.JsonApiResponse(computed_schema.dump(resource))
            else:
                return response.EmptyResponse()

    @property
    def resource_id(self):
        return self.kwargs[self.id_kwarg]

    def read(self, id):
        raise NotImplementedError

    def update(self, id, data, **kwargs):
        raise NotImplementedError

    def destroy(self, id):
        raise NotImplementedError


class ResourceList(ResourceBase):
    methods = ['GET', 'POST']
    filter_schema = filters_schema.FilterSchema()
    pagination = query_string.SizeNumberPagination()

    def __init__(self, *, filter_schema=None, **kwargs):
        super().__init__(**kwargs)
        if filter_schema:
            self.filter_schema = filter_schema

    def get(self, *args, **kwargs):
        parsed_filters = self.filter_schema.parse()
        parsed_sorting = self.sort_parser.parse()
        parsed_pagination = self.pagination.parse()
        objects_list = self.read_many(filters=parsed_filters,
                                      sorting=parsed_sorting,
                                      pagination=parsed_pagination)
        include_fields = self.include_parser.parse()
        sparse_fields = self.sparse_fields_parser.parse()
        try:
            objects = self.schema(
                many=True, include_data=include_fields, only=sparse_fields).dump(objects_list)
        except marshmallow.ValidationError as e:
            raise exceptions.JsonApiException(detail='marshmallow.ValidationError', source=e.messages)
        except (AttributeError, KeyError, ValueError) as e:
            logger.error(
                'Error Processing Request',
                extra={'status_code': http.HTTPStatus.BAD_REQUEST, 'request': request, 'exception': e}
            )
            raise exceptions.JsonApiException(detail=str(e), source={'component': 'schema'})
        else:
            pagination_links = self.get_pagination_links(parsed_pagination, parsed_filters)
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

    def read_many(self, filters, sorting, pagination):
        raise NotImplementedError

    def get_count(self, filters):
        raise NotImplementedError

    def create(self, data, **kwargs):
        raise NotImplementedError


class Actions:
    create = 'create'
    read = 'fetch'
    read_many = 'fetch list'
    update = 'update'
    destroy = 'delete'


def check_allowed_action(action: str):
    def decorate(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if action not in self.allowed_actions:
                raise exceptions.MethodNotAllowed('{} is not allowed for this resource'.format(action.capitalize()))
            return func(self, *args, **kwargs)
        return wrapper
    return decorate


class AllowedActionsResourceMixin:
    allowed_actions = ()

    def __init__(self, *, allowed_actions=None,  **kwargs):
        super().__init__(**kwargs)
        if allowed_actions:
            self.allowed_actions = allowed_actions


class AllowedActionsResourceDetailMixin(AllowedActionsResourceMixin):
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
    @check_allowed_action(Actions.create)
    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)

    @check_allowed_action(Actions.read_many)
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class AllowedActionsResourceViewSetMixin:
    detail_view_cls: AllowedActionsResourceMixin
    list_view_cls: AllowedActionsResourceMixin
    allowed_actions = ()

    def get_views_kwargs(self):
        kwargs = super().get_views_kwargs()
        kwargs['allowed_actions'] = self.allowed_actions
        return kwargs

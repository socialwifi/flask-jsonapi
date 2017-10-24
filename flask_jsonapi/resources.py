import http

import flask
import marshmallow
from flask import helpers
from flask import logging
from flask import request
from flask import views
from marshmallow_jsonapi import exceptions as marshmallow_jsonapi_exceptions

from flask_jsonapi import decorators
from flask_jsonapi import descriptors
from flask_jsonapi import exceptions
from flask_jsonapi import filters_schema
from flask_jsonapi import response

logger = logging.getLogger(__name__)


class ResourceBase(views.View):
    schema = descriptors.NotImplementedProperty('schema')
    args = None
    kwargs = None

    def __init__(self, *, schema=None):
        if schema:
            self.schema = schema

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

    def _check_include_fields(self):
        include_parameter = flask.request.args.get('include')
        if include_parameter:
            include_fields = tuple(include_parameter.split(','))
            try:
                self.schema().check_relations(include_fields)
            except ValueError as exc:
                raise exceptions.InvalidInclude(detail=str(exc))
            return include_fields
        else:
            return tuple()


class ResourceDetail(ResourceBase):
    methods = ['GET', 'DELETE', 'PATCH']
    id_kwarg = 'id'

    def get(self, *args, **kwargs):
        resource = self.read(self.resource_id)
        include_fields = self._check_include_fields()
        try:
            data, errors = self.schema(include_data=include_fields).dump(resource)
        except marshmallow.ValidationError as e:
            return response.JsonApiErrorResponse.from_marshmallow_errors(e.messages)
        else:
            if errors:
                return response.JsonApiErrorResponse.from_marshmallow_errors(errors)
            else:
                return response.JsonApiResponse(data)

    def delete(self, *args, **kwargs):
        self.destroy(self.resource_id)
        return response.EmptyResponse()

    def patch(self, *args, **kwargs):
        computed_schema = self.schema(partial=True)
        try:
            data, errors = computed_schema.load(request.get_json())
        except marshmallow.ValidationError as e:
            return response.JsonApiErrorResponse.from_marshmallow_errors(e.messages)
        else:
            if errors:
                return response.JsonApiErrorResponse.from_marshmallow_errors(errors)
            else:
                resource = self.update(self.resource_id, data)
                if resource:
                    return response.JsonApiResponse(computed_schema.dump(resource).data)
                else:
                    return response.EmptyResponse()

    @property
    def resource_id(self):
        return self.kwargs[self.id_kwarg]

    def read(self, id):
        raise NotImplementedError

    def update(self, id, data):
        raise NotImplementedError

    def destroy(self, id):
        raise NotImplementedError


class ResourceList(ResourceBase):
    methods = ['GET', 'POST']
    filter_schema = filters_schema.FilterSchema({})

    def __init__(self, *, filter_schema=None, **kwargs):
        super().__init__(**kwargs)
        if filter_schema:
            self.filter_schema = filter_schema

    def get(self, *args, **kwargs):
        objects_list = self.read_many(filters=self.filter_schema.parse())
        include_fields = self._check_include_fields()
        try:
            objects, errors = self.schema(many=True, include_data=include_fields).dump(objects_list)
        except marshmallow.ValidationError as e:
            return response.JsonApiErrorResponse.from_marshmallow_errors(e.messages)
        else:
            if errors:
                return response.JsonApiErrorResponse.from_marshmallow_errors(errors)
            else:
                return response.JsonApiListResponse(
                    response_data=objects,
                )

    def post(self, *args, **kwargs):
        try:
            data, errors = self.schema().load(request.get_json())
        except marshmallow_jsonapi_exceptions.IncorrectTypeError as e:
            return response.JsonApiErrorResponse.from_marshmallow_errors(e.messages)
        except marshmallow.ValidationError as e:
            return response.JsonApiErrorResponse.from_marshmallow_errors(e.messages)
        else:
            if errors:
                response.JsonApiErrorResponse.from_marshmallow_errors(errors)
            else:
                return self.prepare_response(data)

    def prepare_response(self, data):
        object = self.create(data=data)
        return response.JsonApiResponse(
            self.schema().dump(object).data,
            status=http.HTTPStatus.CREATED,
        )

    def read_many(self, filters):
        raise NotImplementedError

    def create(self, data, **kwargs):
        raise NotImplementedError

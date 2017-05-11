import http

import marshmallow
from flask import logging
from flask import request
from flask import views, helpers
from marshmallow_jsonapi import exceptions as marshmallow_jsonapi_exceptions

from flask_jsonapi import decorators
from flask_jsonapi import exceptions
from flask_jsonapi import response


logger = logging.getLogger(__name__)


class Resource(views.MethodView):
    @classmethod
    def as_view(cls, name, *class_args, **class_kwargs):
        view = super().as_view(name, *class_args, **class_kwargs)
        return decorators.check_headers(view)

    def dispatch_request(self, *args, **kwargs):
        handler = getattr(self, request.method.lower(), self._http_method_not_allowed)
        try:
            response_object = handler(request, *args, **kwargs)
        except exceptions.JsonApiException as e:
            return response.JsonApiErrorResponse(
                e.to_dict(),
                status=e.status
            ).make_error_response()
        except Exception as e:
            error = exceptions.JsonApiException(source='', detail=str(e), title='Unknown error.')
            return response.JsonApiErrorResponse(error.to_dict()).make_error_response()
        else:
            return response_object.make_response()

    def _http_method_not_allowed(self, request, *args, **kwargs):
        logger.error(
            'Method Not Allowed (%s): %s', request.method, request.path,
            extra={'status_code': http.HTTPStatus.METHOD_NOT_ALLOWED, 'request': request}
        )
        return helpers.make_response('Method Not Allowed.', http.HTTPStatus.METHOD_NOT_ALLOWED)


class ResourceList(Resource):
    methods = ['GET', 'POST']

    @property
    def schema(self):
        raise NotImplementedError

    def get_list(self):
        raise NotImplementedError

    def create(self, *args, **kwargs):
        raise NotImplementedError

    def get(self, *args, **kwargs):
        try:
            objects_list = self.get_list()
        except DataLayerObjectNotFound as e:
            raise exceptions.ObjectNotFound(source='', detail=str(e))
        except DataLayerError as e:
            raise exceptions.JsonApiException(source='', detail=str(e))
        else:
            try:
                objects, errors = self.schema(many=True).dump(objects_list)
            except marshmallow.ValidationError as e:
                raise exceptions.JsonApiException(
                    source='',
                    detail=str(e),
                    title='Validation Error.',
                    status=http.HTTPStatus.UNPROCESSABLE_ENTITY
                )
            else:
                if errors:
                    error = errors['errors'].pop()
                    raise exceptions.JsonApiException(
                        source=error.source,
                        detail=error.detail,
                        title=error.title,
                        status=error.status
                    )
                else:
                    return response.JsonApiListResponse(
                        response_data=objects,
                        status=http.HTTPStatus.CREATED,
                    )

    def post(self, *args, **kwargs):
        try:
            data, errors = self.schema().load(request.get_json())
        except marshmallow_jsonapi_exceptions.IncorrectTypeError as e:
            exceptions.get_error_and_raise_exception(errors_dict=e.messages, title='Incorrect type error.')
        except marshmallow.ValidationError as e:
            exceptions.get_error_and_raise_exception(errors_dict=e.messages)
        else:
            if errors:
                exceptions.get_error_and_raise_exception(errors_dict=errors)
            else:
                try:
                    object = self.create(data=data)
                except DataLayerError as e:
                    raise exceptions.JsonApiException(
                        source='',
                        detail=str(e)
                    )
                else:
                    return response.JsonApiResponse(
                        self.schema().dump(object).data,
                        status=http.HTTPStatus.CREATED,
                    )


class DataLayerError(Exception):
    pass


class DataLayerObjectNotFound(DataLayerError):
    pass

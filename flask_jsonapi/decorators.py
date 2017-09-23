import functools

import flask

from flask_jsonapi import response


def check_headers(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if flask.request.method in ('POST', 'PATCH'):
            if flask.request.headers.get('Content-Type') != 'application/vnd.api+json':
                return response.JsonApiErrorResponse({
                    'source': '',
                    'detail': 'Content-Type header must be application/vnd.api+json',
                    'title': 'InvalidRequestHeader',
                    'status': 415
                }, status=415).make_response()
        if flask.request.headers.get('Accept', 'application/vnd.api+json') != 'application/vnd.api+json':
            return response.JsonApiErrorResponse({
                'source': '',
                'detail': 'Accept header must be application/vnd.api+json',
                'title': 'InvalidRequestHeader',
                'status': 406
            }, status=406).make_response()
        return func(*args, **kwargs)
    return wrapped


def selective_decorator(decorator, methods):
    def wrap(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            if flask.request.method in methods:
                return decorator(func)(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapped
    return wrap


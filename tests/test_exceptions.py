import warnings

import pytest

from flask_jsonapi import exceptions
from flask_jsonapi.permissions import checkers
from flask_jsonapi.resource_repositories import repositories


def test_base_accepts_legacy_positional_source_and_detail():
    error = exceptions.JsonApiException({'pointer': '/data'}, 'boom')
    assert error.to_dict() == {
        'status': 500, 'title': 'Unknown error', 'source': {'pointer': '/data'}, 'detail': 'boom',
    }


@pytest.mark.parametrize('exception_class', [
    exceptions.ForbiddenError, exceptions.MethodNotAllowed, exceptions.NotImplementedMethod,
    exceptions.InvalidFilters, exceptions.InvalidSort, exceptions.InvalidPage,
    exceptions.InvalidField, exceptions.InvalidInclude,
])
def test_subclasses_accept_positional_detail(exception_class):
    assert exception_class('boom').detail == 'boom'


def test_extra_positional_arguments_reach_exception_args():
    error = exceptions.JsonApiException({'pointer': '/data'}, 'boom', 'extra', 2)
    assert (error.source, error.detail) == ({'pointer': '/data'}, 'boom')
    assert error.args[-2:] == ('extra', 2)
    assert str(error) == 'boom'


def test_message_survives_in_str_and_args():
    assert str(exceptions.ForbiddenError('boom')) == 'boom'
    assert exceptions.ForbiddenError('boom').args == ('boom',)
    assert str(exceptions.JsonApiException(detail='boom')) == 'boom'
    assert str(exceptions.JsonApiException(status=400)) == ''


def test_permission_exception_accepts_positional_source_and_detail():
    error = checkers.PermissionException({'pointer': '/data'}, 'no')
    assert (error.source, error.detail, error.status) == ({'pointer': '/data'}, 'no', 403)


def test_legacy_resource_repository_still_raises_not_implemented():
    with pytest.raises(exceptions.NotImplementedMethod):
        repositories.ResourceRepository().create({})


def test_legacy_signatures_do_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        exceptions.ForbiddenError('x')
        exceptions.JsonApiException({}, 'x')


def test_to_dict_omits_empty_members():
    assert exceptions.JsonApiException(status=400, title='Bad').to_dict() == {'status': 400, 'title': 'Bad'}


@pytest.mark.parametrize('exception_class, status, title', [
    (exceptions.Unauthorized, 401, 'Unauthorized'),
    (exceptions.Conflict, 409, 'Conflict'),
    (exceptions.UnprocessableEntity, 422, 'Unprocessable entity'),
    (exceptions.ServiceUnavailable, 503, 'Service unavailable'),
])
def test_http_exceptions(exception_class, status, title):
    assert exception_class().to_dict() == {'status': status, 'title': title}

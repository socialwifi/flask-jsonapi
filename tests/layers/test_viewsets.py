import subprocess
import sys

import pytest

import flask_jsonapi

from flask_jsonapi import exceptions
from flask_jsonapi import filters_schema
from flask_jsonapi import guards
from flask_jsonapi import viewsets
from flask_jsonapi.resources import Actions
from tests.layers.conftest import ArticleSchema
from tests.layers.conftest import RecordingGuard
from tests.layers.conftest import RecordingObjectPermissions


class DenyAll(guards.Guard):
    def check(self, action):
        raise exceptions.Unauthorized(detail='denied')


def make_viewset(articles, **attributes):
    attributes.update(schema_class=ArticleSchema, data_service=articles)
    return type('ArticleViewSet', (viewsets.ViewSet,), attributes)()


def test_viewset_serves_list_and_detail(api, jsonapi_client, articles):
    api.repository(make_viewset(articles, allowed_actions={Actions.read, Actions.list}), 'articles', '/articles/')
    assert jsonapi_client.get('/articles/').status_code == 200
    assert jsonapi_client.get('/articles/1/').status_code == 200


def test_filter_schema_reaches_the_list_view(api, jsonapi_client, articles):
    class OwnerFilters(filters_schema.FilterSchema):
        owner = filters_schema.FilterField()

    viewset = make_viewset(articles, allowed_actions={Actions.list}, filter_schema=OwnerFilters())
    api.repository(viewset, 'articles', '/articles/')
    assert jsonapi_client.get('/articles/?filter[owner]=me').status_code == 200
    assert [kwargs['filters'] for name, kwargs in articles.calls if name == 'list'] == [{'owner': 'me'}]


def test_viewset_without_allowed_actions_serves_nothing(api, jsonapi_client, articles):
    api.repository(make_viewset(articles), 'articles', '/articles/')
    assert jsonapi_client.get('/articles/').status_code == 405
    assert jsonapi_client.get('/articles/1/').status_code == 405


def test_subclass_replaces_guards(api, jsonapi_client, articles):
    class Public(viewsets.ViewSet):
        schema_class = ArticleSchema
        data_service = articles
        allowed_actions = {Actions.list}
        guards = [DenyAll()]

    class Internal(Public):
        guards = []

    api.repository(Public(), 'public', '/public/')
    api.repository(Internal(), 'internal', '/internal/')
    public_status = jsonapi_client.get('/public/').status_code
    internal_status = jsonapi_client.get('/internal/').status_code
    assert (public_status, internal_status) == (401, 200)


def test_subclass_switches_off_guards_and_object_permissions(api, jsonapi_client, articles):
    log = []

    class Public(viewsets.ViewSet):
        schema_class = ArticleSchema
        data_service = articles
        allowed_actions = {Actions.read, Actions.list}
        guards = [RecordingGuard(log)]
        object_permissions = RecordingObjectPermissions(log)

    class Internal(Public):
        guards = []
        object_permissions = None

    api.repository(Public(), 'public', '/public/')
    api.repository(Internal(), 'internal', '/internal/')
    public_statuses = [jsonapi_client.get(url).status_code for url in ['/public/', '/public/1/']]
    assert (public_statuses, log) == ([200, 200], ['guard', 'object permissions'] * 2)
    log.clear()
    internal_statuses = [jsonapi_client.get(url).status_code for url in ['/internal/', '/internal/1/']]
    assert (internal_statuses, log) == ([200, 200], [])


def test_view_decorators_wrap_both_views(api, jsonapi_client, articles):
    wrapped = []

    def record_endpoint(view):
        wrapped.append(view.__name__)
        return view

    viewset = make_viewset(articles, view_decorators=[record_endpoint])
    api.repository(viewset, 'articles', '/articles/')
    assert sorted(wrapped) == ['articles_detail', 'articles_list']


def test_missing_data_service_is_reported(api):
    class NoDataServiceViewSet(viewsets.ViewSet):
        schema_class = ArticleSchema

    with pytest.raises(NotImplementedError):
        api.repository(NoDataServiceViewSet(), 'broken', '/broken/')


def test_public_api_exports_layered_classes():
    assert flask_jsonapi.ViewSet is viewsets.ViewSet
    assert flask_jsonapi.Actions is Actions
    assert all(isinstance(name, str) for name in flask_jsonapi.__all__)


def test_new_api_imports_without_sqlalchemy():
    code = ("import sys; sys.modules['sqlalchemy'] = None; "
            "import flask_jsonapi, flask_jsonapi.viewsets, flask_jsonapi.views, flask_jsonapi.guards, "
            "flask_jsonapi.middlewares, flask_jsonapi.permissions, flask_jsonapi.data_services")
    subprocess.run([sys.executable, '-c', code], check=True)

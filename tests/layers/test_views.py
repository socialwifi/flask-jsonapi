import types

import flask
import pytest

from flask_jsonapi import data_services
from flask_jsonapi import exceptions
from flask_jsonapi import guards
from flask_jsonapi import middlewares
from flask_jsonapi import views
from flask_jsonapi.data_services import exceptions as ds_exceptions
from flask_jsonapi.resources import Actions
from tests.layers.conftest import ArticleSchema
from tests.layers.conftest import RecordingGuard
from tests.layers.conftest import RecordingMiddleware
from tests.layers.conftest import RecordingObjectPermissions

ALL = {Actions.create, Actions.read, Actions.list, Actions.update, Actions.destroy}
NEW_ARTICLE_BODY = {'data': {'type': 'articles', 'attributes': {'title': 'brand new', 'owner': 'me'}}}


def patch_body(id, **attributes):
    return {'data': {'type': 'articles', 'id': str(id), 'attributes': attributes}}


@pytest.fixture
def register(api, articles):
    def register_views(**view_kwargs):
        view_kwargs.setdefault('allowed_actions', ALL)
        view_kwargs.update(data_service=articles, schema=ArticleSchema)
        api.route(views.DetailView, 'articles_detail', '/articles/<id>/', view_kwargs=view_kwargs)
        api.route(views.ListView, 'articles_list', '/articles/', view_kwargs=view_kwargs)
    return register_views


def error_document(response):
    return response.get_json(force=True)['errors']


def test_crud_round_trip(register, jsonapi_client):
    register()
    assert jsonapi_client.get('/articles/1/').status_code == 200
    assert len(jsonapi_client.get('/articles/').get_json(force=True)['data']) == 2
    assert jsonapi_client.post('/articles/', json=NEW_ARTICLE_BODY).status_code == 201
    patched = jsonapi_client.patch('/articles/1/', json=patch_body(1, title='new'))
    assert (patched.status_code, patched.get_json(force=True)['data']['attributes']['title']) == (200, 'new')
    assert jsonapi_client.delete('/articles/1/').status_code == 204


@pytest.mark.parametrize('hook', ['read_many', 'get_count', 'get_pagination_links'])
def test_list_view_has_no_legacy_list_hooks(hook):
    assert not hasattr(views.ListView, hook)


def test_read_many_is_an_alias_of_list():
    assert Actions.read_many == Actions.list


def test_read_many_in_allowed_actions_serves_lists(register, jsonapi_client):
    register(allowed_actions={Actions.read_many})
    assert jsonapi_client.get('/articles/').status_code == 200


def test_not_allowed_action_is_rejected_before_body_parsing(register, jsonapi_client):
    register(allowed_actions={Actions.read})
    response = jsonapi_client.patch('/articles/1/', json=patch_body(1, title=5))
    assert response.status_code == 405
    assert error_document(response)[0]['detail'] == 'Update is not allowed for this resource'


def test_empty_allowed_actions_serves_nothing(api, jsonapi_client, articles):
    view_kwargs = {'data_service': articles, 'schema': ArticleSchema}
    api.route(views.DetailView, 'articles_detail', '/articles/<id>/', view_kwargs=view_kwargs)
    api.route(views.ListView, 'articles_list', '/articles/', view_kwargs=view_kwargs)
    assert jsonapi_client.get('/articles/').status_code == 405
    assert jsonapi_client.get('/articles/1/').status_code == 405


def test_guards_run_before_body_parsing(register, jsonapi_client):
    class Deny(guards.Guard):
        def check(self, action):
            raise exceptions.Unauthorized()

    register(guards=[Deny()])
    response = jsonapi_client.patch('/articles/1/', json=patch_body(1, title=5))
    assert response.status_code == 401


def test_guards_run_in_order_with_the_action(register, jsonapi_client):
    seen = []

    class Recording(guards.Guard):
        def __init__(self, name):
            self.name = name

        def check(self, action):
            seen.append((self.name, action))

    register(guards=[Recording('first'), Recording('second')])
    assert jsonapi_client.patch('/articles/1/', json=patch_body(1, title='new')).status_code == 200
    assert seen == [('first', Actions.update), ('second', Actions.update)]


def test_guard_flask_abort_is_jsonapi(register, jsonapi_client):
    class Abort(guards.Guard):
        def check(self, action):
            flask.abort(400)

    register(guards=[Abort()])
    response = jsonapi_client.get('/articles/')
    assert response.status_code == 400
    assert response.headers['Content-Type'] == 'application/vnd.api+json'


def test_guard_base_class_is_abstract():
    with pytest.raises(NotImplementedError):
        guards.Guard().check(Actions.read)


def test_patch_loads_once_and_hands_the_resource_down(register, jsonapi_client, articles):
    register()
    jsonapi_client.patch('/articles/1/', json=patch_body(1, title='new'))
    assert [name for name, kwargs in articles.calls] == ['read', 'update']
    assert articles.calls[1][1]['resource'] is articles.rows[1]
    assert 'id' not in articles.calls[1][1]['data']


def test_delete_loads_once_and_hands_the_resource_down(register, jsonapi_client, articles):
    register()
    jsonapi_client.delete('/articles/1/')
    assert [name for name, kwargs in articles.calls] == ['read', 'destroy']


@pytest.mark.parametrize('error, status, expected_error', [
    (ds_exceptions.ResourceNotFound('Missing.'), 404,
     {'status': 404, 'title': 'Object not found', 'detail': 'Missing.'}),
    (ds_exceptions.PermissionDenied('No.'), 403,
     {'status': 403, 'title': 'Operation forbidden.', 'detail': 'No.'}),
    (ds_exceptions.InvalidData('Bad.', field='title'), 422,
     {'status': 422, 'title': 'Attribute error', 'detail': 'Bad.', 'source': {'pointer': '/data/attributes/title'}}),
    (ds_exceptions.InvalidData('Bad.'), 422,
     {'status': 422, 'title': 'Unprocessable entity', 'detail': 'Bad.'}),
    (ds_exceptions.Conflict('Taken.'), 409,
     {'status': 409, 'title': 'Conflict', 'detail': 'Taken.'}),
    (ds_exceptions.Unavailable('Later.'), 503,
     {'status': 503, 'title': 'Service unavailable', 'detail': 'Later.'}),
    (ds_exceptions.DataServiceException('SELECT secret'), 500,
     {'status': 500, 'title': 'Internal server error'}),
])
def test_data_service_errors_are_translated(
        register, jsonapi_client, articles, monkeypatch, error, status, expected_error):
    register()

    def fail(**kwargs):
        raise error
    monkeypatch.setattr(articles, 'read', fail)
    response = jsonapi_client.get('/articles/1/')
    assert response.status_code == status
    assert error_document(response) == [expected_error]


def test_unexpected_data_service_error_is_logged(register, jsonapi_client, articles, monkeypatch, caplog):
    register()

    def fail(**kwargs):
        raise ds_exceptions.DataServiceException('SELECT secret')
    monkeypatch.setattr(articles, 'read', fail)
    jsonapi_client.get('/articles/1/')
    assert any(record.name == 'flask_jsonapi.views' and record.exc_info for record in caplog.records)


@pytest.mark.parametrize('error, parameter', [
    (ds_exceptions.InvalidSortParameter('Bad sort.'), 'sort'),
    (ds_exceptions.InvalidFilterParameter('Bad filter.'), 'filters'),
])
def test_sort_and_filter_errors_are_400(register, jsonapi_client, articles, monkeypatch, error, parameter):
    register()

    def fail(**kwargs):
        raise error
    monkeypatch.setattr(articles, 'list', fail)
    response = jsonapi_client.get('/articles/')
    assert response.status_code == 400
    assert error_document(response)[0]['source'] == {'parameter': parameter}


def test_patch_and_delete_of_missing_object_are_404(register, jsonapi_client):
    register()
    assert jsonapi_client.patch('/articles/999/', json=patch_body(999, title='x')).status_code == 404
    assert jsonapi_client.delete('/articles/999/').status_code == 404


def test_paginated_list_makes_one_pipeline_call(register, jsonapi_client, articles):
    recorded = []

    class RecordList(middlewares.Middleware):
        def list(self, *, filters, inner, **kwargs):
            recorded.append(filters)
            return inner.list(filters=filters, **kwargs)

    register(middlewares=[RecordList()])
    assert jsonapi_client.get('/articles/?page[size]=1&page[number]=1').status_code == 200
    assert recorded == [{}]
    assert [name for name, kwargs in articles.calls] == ['list']


def links_of(jsonapi_client, query):
    response = jsonapi_client.get('/articles/?' + query)
    assert response.status_code == 200
    return response.get_json(force=True)['links']


def page_link(number, size):
    return 'http://localhost/articles/?page[size]={}&page[number]={}'.format(size, number)


def test_links_come_from_the_list_total(register, jsonapi_client):
    register()
    assert links_of(jsonapi_client, 'page[size]=1&page[number]=1') == {
        'self': page_link(1, size=1),
        'first': page_link(1, size=1),
        'previous': None,
        'next': page_link(2, size=1),
        'last': page_link(2, size=1),
    }


def test_unpaginated_list_has_no_links(register, jsonapi_client):
    register()
    assert 'links' not in jsonapi_client.get('/articles/').get_json(force=True)


@pytest.mark.parametrize('size, number, expected_previous, expected_next', [
    (2, 1, None, 2),
    (4, 1, None, None),
    (1, 2, 1, 3),
    (2, 2, 1, None),
])
def test_links_without_total_have_no_last_and_next_only_for_a_full_page(
        register, jsonapi_client, articles, monkeypatch, size, number, expected_previous, expected_next):
    register()
    paginated_list = articles.list
    monkeypatch.setattr(articles, 'list', lambda **kwargs: data_services.ListResult(
        paginated_list(**kwargs).items, total=None))
    articles.rows[3] = types.SimpleNamespace(id=3, title='third', owner='me')

    links = links_of(jsonapi_client, 'page[size]={}&page[number]={}'.format(size, number))

    assert links == {
        'self': page_link(number, size),
        'first': page_link(1, size),
        'previous': page_link(expected_previous, size) if expected_previous else None,
        'next': page_link(expected_next, size) if expected_next else None,
        'last': None,
    }


@pytest.mark.parametrize('method', ['get', 'patch', 'delete'])
def test_missing_resource_from_data_service_is_404(register, jsonapi_client, articles, monkeypatch, method):
    register()
    monkeypatch.setattr(articles, 'read', lambda **kwargs: None)
    response = getattr(jsonapi_client, method)('/articles/1/', json=patch_body(1, title='x'))
    assert response.status_code == 404
    assert error_document(response)[0]['status'] == 404
    assert [name for name, kwargs in articles.calls] == []


@pytest.mark.parametrize('url, data_service_call', [('/articles/', 'list'), ('/articles/1/', 'read')])
def test_object_permissions_run_after_guards_and_before_every_middleware(
        register, jsonapi_client, articles, url, data_service_call):
    log = []
    register(
        guards=[RecordingGuard(log)],
        object_permissions=RecordingObjectPermissions(log),
        middlewares=[RecordingMiddleware(log, 'first middleware'), RecordingMiddleware(log, 'second middleware')],
    )
    assert jsonapi_client.get(url).status_code == 200
    assert log == ['guard', 'object permissions', 'first middleware', 'second middleware']
    assert [name for name, kwargs in articles.calls] == [data_service_call]


@pytest.mark.parametrize('view_kwargs', [{}, {'object_permissions': None}])
@pytest.mark.parametrize('view_class', [views.DetailView, views.ListView])
def test_without_object_permissions_the_pipeline_has_no_extra_layer(articles, view_class, view_kwargs):
    middleware = middlewares.Middleware()
    view = view_class(schema=ArticleSchema, data_service=articles, middlewares=[middleware], **view_kwargs)
    assert (view.pipeline.middleware, view.pipeline.inner) == (middleware, articles)

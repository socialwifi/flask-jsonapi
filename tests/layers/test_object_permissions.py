import logging

import pytest

from flask_jsonapi import filters_schema
from flask_jsonapi import middlewares
from flask_jsonapi import permissions
from flask_jsonapi import views
from flask_jsonapi.resources import Actions
from tests.layers.conftest import ArticleSchema


class OwnerChecker(permissions.PermissionChecker):
    def check_read_permission(self, *, resource):
        if resource.owner != 'me':
            raise permissions.PermissionException
        return resource

    def check_destroy_permission(self, *, resource):
        return self.check_read_permission(resource=resource)

    def check_update_permission(self, *, resource, data):
        self.check_read_permission(resource=resource)
        return resource, {**data, 'title': 'checked'}

    def check_create_permission(self, *, data):
        return {'title': 'checked'}


class OwnerOnly(permissions.CheckObjectPermission):
    def apply_permission_filter(self, filters):
        return {**filters, 'owner': 'me'}


SAFETY_NET = 'Object permission check dropped listed objects; the total is hidden.'


@pytest.fixture
def pipeline(articles):
    return middlewares.build_pipeline([OwnerOnly(OwnerChecker())], articles)


ACTIONS = ['create', 'read', 'list', 'update', 'destroy']


@pytest.mark.parametrize('missing', ACTIONS)
def test_object_permissions_must_implement_every_action(missing):
    methods = {name: lambda self, **kwargs: None for name in ACTIONS if name != missing}
    incomplete = type('Incomplete', (permissions.ObjectPermissions,), methods)

    with pytest.raises(TypeError):
        incomplete()


def test_object_permissions_with_every_action_can_be_instantiated():
    methods = {name: lambda self, **kwargs: None for name in ACTIONS}
    type('Complete', (permissions.ObjectPermissions,), methods)()


def test_permission_classes_live_in_permissions_only():
    assert permissions.CheckObjectPermission.__module__ == 'flask_jsonapi.permissions.object_permissions'
    assert {'ObjectPermissions', 'CheckObjectPermission'} <= set(permissions.__all__)
    assert all(isinstance(name, str) for name in permissions.__all__)
    assert sorted(middlewares.__all__) == ['CheckRequiredListFilters', 'Middleware', 'build_pipeline']
    assert not hasattr(middlewares, 'PermissionMiddleware')
    assert not hasattr(middlewares, 'CheckObjectPermission')


def test_check_object_permission_must_implement_permission_filter():
    with pytest.raises(TypeError):
        permissions.CheckObjectPermission(OwnerChecker())


def test_permission_checker_must_be_provided():
    with pytest.raises(NotImplementedError):
        OwnerOnly().permission_checker


def test_read_checks_read_permission(pipeline):
    assert pipeline.read(id=1).id == 1

    with pytest.raises(permissions.PermissionException):
        pipeline.read(id=2)


def test_create_passes_on_data_returned_by_checker(pipeline, articles):
    pipeline.create(data={'title': 'raw'})

    assert articles.calls[-1] == ('create', {'data': {'title': 'checked'}})


def test_update_passes_on_data_returned_by_checker(pipeline, articles):
    resource = articles.rows[1]

    pipeline.update(resource=resource, data={'title': 'raw'})

    assert articles.calls[-1] == ('update', {'resource': resource, 'data': {'title': 'checked'}})


def test_update_and_destroy_check_their_permission(pipeline, articles):
    other = articles.rows[2]

    with pytest.raises(permissions.PermissionException):
        pipeline.update(resource=other, data={'title': 'raw'})
    with pytest.raises(permissions.PermissionException):
        pipeline.destroy(resource=other)

    assert articles.calls == []
    assert 2 in articles.rows


def test_destroy_own_resource(pipeline, articles):
    pipeline.destroy(resource=articles.rows[1])

    assert articles.calls[-1][0] == 'destroy'
    assert 1 not in articles.rows


def test_object_permissions_have_no_count():
    assert not hasattr(permissions.ObjectPermissions, 'count')
    assert not hasattr(permissions.CheckObjectPermission, 'count')


def test_list_applies_filter_and_list_check(pipeline, articles):
    filters = {}

    result = pipeline.list(filters=filters, sorting=[], pagination={})

    assert [row.id for row in result.items] == [1]
    assert articles.calls[-1] == ('list', {'filters': {'owner': 'me'}, 'sorting': [], 'pagination': {}})
    assert filters == {}


def test_safety_net_hides_the_total_and_logs_without_data(pipeline, caplog):
    with caplog.at_level(logging.DEBUG):
        result = pipeline.list(filters={}, sorting=[], pagination={'size': 10, 'number': 1})

    assert ([row.id for row in result.items], result.total) == ([1], None)
    assert [(record.levelno, record.getMessage()) for record in caplog.records] == [(logging.WARNING, SAFETY_NET)]
    assert not hasattr(caplog.records[0], 'filters')
    assert caplog.records[0].args == ()


def test_list_keeps_the_total_when_nothing_was_dropped(articles, caplog):
    del articles.rows[2]
    pipeline = middlewares.build_pipeline([OwnerOnly(OwnerChecker())], articles)

    with caplog.at_level(logging.WARNING):
        result = pipeline.list(filters={}, sorting=[], pagination={'size': 10, 'number': 1})

    assert ([row.id for row in result.items], result.total) == ([1], 1)
    assert caplog.records == []


def test_permission_filter_refusing_the_scope_is_403_before_listing(api, jsonapi_client, articles):
    class RefuseForeignOwner(permissions.CheckObjectPermission):
        def apply_permission_filter(self, filters):
            if filters.get('owner') not in (None, 'me'):
                raise permissions.PermissionException(detail='You may not list this scope.')
            return {**filters, 'owner': 'me'}

    class OwnerFilters(filters_schema.FilterSchema):
        owner = filters_schema.FilterField()

    api.route(views.ListView, 'articles_list', '/articles/', view_kwargs={
        'schema': ArticleSchema, 'data_service': articles, 'allowed_actions': {Actions.list},
        'filter_schema': OwnerFilters(),
        'object_permissions': RefuseForeignOwner(OwnerChecker()),
    })

    response = jsonapi_client.get('/articles/?filter[owner]=other')

    assert response.status_code == 403
    assert response.get_json(force=True)['errors'][0]['detail'] == 'You may not list this scope.'
    assert articles.calls == []

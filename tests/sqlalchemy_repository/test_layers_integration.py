import contextlib
import json
import logging

import marshmallow_jsonapi
import pytest
import sqlalchemy
import sqlalchemy.orm

from marshmallow_jsonapi import fields

import flask_jsonapi

from flask_jsonapi import data_services
from flask_jsonapi import permissions
from flask_jsonapi.data_services import sqlalchemy_repositories
from flask_jsonapi.resource_repositories import sqlalchemy_repositories as legacy_sqlalchemy_repositories

Base = sqlalchemy.orm.declarative_base()

OWNER = 'me'
OTHER = 'someone else'


class Article(Base):
    __tablename__ = 'articles'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    title = sqlalchemy.Column(sqlalchemy.String, unique=True)
    owner = sqlalchemy.Column(sqlalchemy.String)


class ArticleSchema(marshmallow_jsonapi.Schema):
    id = fields.Int()
    title = fields.Str()
    owner = fields.Str()

    class Meta:
        type_ = 'articles'


class OwnerChecker(permissions.PermissionChecker):
    def check_read_permission(self, *, resource):
        return self._check(resource)

    def check_destroy_permission(self, *, resource):
        return self._check(resource)

    def check_update_permission(self, *, resource, data):
        return self._check(resource), data

    def check_create_permission(self, *, data):
        return data

    @staticmethod
    def _check(resource):
        if resource.owner != OWNER:
            raise permissions.PermissionException
        return resource


class OwnerOnly(permissions.CheckObjectPermission):
    permission_checker = OwnerChecker()

    def apply_permission_filter(self, filters):
        return {**filters, 'owner': OWNER}


@contextlib.contextmanager
def recorded_statements(engine):
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    sqlalchemy.event.listen(engine, 'before_cursor_execute', record)
    try:
        yield statements
    finally:
        sqlalchemy.event.remove(engine, 'before_cursor_execute', record)


def make_viewset(data_service):
    class ArticleViewSet(flask_jsonapi.ViewSet):
        schema_class = ArticleSchema
        allowed_actions = {
            flask_jsonapi.Actions.create,
            flask_jsonapi.Actions.read,
            flask_jsonapi.Actions.list,
            flask_jsonapi.Actions.update,
            flask_jsonapi.Actions.destroy,
        }
        object_permissions = OwnerOnly()

    ArticleViewSet.data_service = data_service
    return ArticleViewSet()


def article_body(**attributes):
    return json.dumps({'data': {'type': 'articles', **attributes}})


@pytest.fixture
def articles(db_session):
    class ArticleRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = Article
        session = db_session

    return ArticleRepository()


@pytest.fixture
def seed(db_session):
    def add(*rows):
        for id, title, owner in rows:
            db_session.add(Article(id=id, title=title, owner=owner))
        db_session.commit()

    return add


@pytest.fixture
def served(app, articles):
    flask_jsonapi.Api(app).repository(make_viewset(articles), 'articles', '/articles/')


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema', 'served')
class TestSqlAlchemyDataService:
    def test_own_object_is_readable_and_others_are_forbidden(self, jsonapi_client, seed):
        seed((1, 'mine', OWNER), (2, 'theirs', OTHER))
        assert jsonapi_client.get('/articles/1/').status_code == 200
        assert jsonapi_client.get('/articles/2/').status_code == 403

    def test_patch_selects_the_object_once(self, jsonapi_client, seed, db_engine):
        seed((1, 'mine', OWNER))
        with recorded_statements(db_engine) as statements:
            response = jsonapi_client.patch('/articles/1/', data=article_body(id='1', attributes={'title': 'new'}))
        assert response.status_code == 200
        before_update = statements[:next(i for i, s in enumerate(statements) if s.startswith('UPDATE'))]
        selects_before_update = [statement for statement in before_update if statement.startswith('SELECT')]
        assert len(selects_before_update) == 1

    def test_pagination_total_respects_permissions(self, jsonapi_client, seed):
        seed((1, 'a', OWNER), (2, 'b', OWNER), (3, 'c', OTHER), (4, 'd', OTHER))
        response = jsonapi_client.get('/articles/?page[size]=1&page[number]=1')
        assert response.status_code == 200
        assert response.get_json(force=True)['links']['last'].endswith('page[number]=2')

    def test_paginated_list_runs_one_count_and_one_select(self, jsonapi_client, seed, db_engine):
        seed((1, 'a', OWNER), (2, 'b', OWNER))
        with recorded_statements(db_engine) as statements:
            response = jsonapi_client.get('/articles/?page[size]=1&page[number]=1')
        assert response.status_code == 200
        assert len(statements) == 2
        assert len([statement for statement in statements if 'count(' in statement.lower()]) == 1

    def test_duplicate_create_is_a_jsonapi_409(self, jsonapi_client, seed):
        seed((1, 'taken', OWNER))
        response = jsonapi_client.post('/articles/', data=article_body(attributes={'title': 'taken', 'owner': OWNER}))
        assert response.status_code == 409
        assert response.get_json(force=True)['errors'][0]['status'] == 409

    def test_mismatched_patch_id_is_409(self, jsonapi_client, seed):
        seed((1, 'mine', OWNER))
        response = jsonapi_client.patch('/articles/1/', data=article_body(id='2', attributes={'title': 'new'}))
        assert response.status_code == 409
        assert response.get_json(force=True)['errors'][0]['status'] == 409


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
def test_legacy_repository_through_adapter(app, jsonapi_client, db_session, seed):
    class LegacyArticleRepository(legacy_sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = Article
        session = db_session
        instance_name = 'article'

    viewset = make_viewset(data_services.LegacyRepositoryAdapter(LegacyArticleRepository()))
    flask_jsonapi.Api(app).repository(viewset, 'articles', '/articles/')
    seed((1, 'mine', OWNER))

    patched = jsonapi_client.patch('/articles/1/', data=article_body(id='1', attributes={'title': 'new'}))
    deleted = jsonapi_client.delete('/articles/1/')
    missing = jsonapi_client.get('/articles/1/')

    assert (patched.status_code, deleted.status_code, missing.status_code) == (200, 204, 404)
    assert missing.get_json(force=True)['errors'][0]['status'] == 404


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
def test_safety_net_hides_the_total_when_the_filter_lets_foreign_rows_through(
        app, jsonapi_client, articles, seed, caplog):
    class LeakyFilter(OwnerOnly):
        def apply_permission_filter(self, filters):
            return dict(filters)

    viewset = make_viewset(articles)
    viewset.object_permissions = LeakyFilter()
    flask_jsonapi.Api(app).repository(viewset, 'articles', '/articles/')
    seed((1, 'a', OWNER), (2, 'b', OTHER), (3, 'c', OWNER))

    response = jsonapi_client.get('/articles/?page[size]=2&page[number]=1')

    document = response.get_json(force=True)
    assert [item['id'] for item in document['data']] == [1]
    assert (document['links']['last'], document['links']['next']) == (None, None)
    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert OTHER not in warnings[0].getMessage()

import flask
import pytest

from flask import testing


@pytest.fixture
def app():
    application = flask.Flask(__name__)
    return application


@pytest.fixture
def api(app):
    from flask_jsonapi import api
    application_api = api.Api(app)
    return application_api


@pytest.fixture
def test_client(app):
    with app.test_client() as client:
        yield client


class JSONAPIClient(testing.FlaskClient):
    def open(self, *args, **kwargs):
        headers = kwargs.setdefault('headers', {})
        headers.setdefault('Content-Type', 'application/vnd.api+json')
        headers.setdefault('Accept', 'application/vnd.api+json')
        return super().open(*args, **kwargs)


@pytest.fixture
def jsonapi_client(app):
    app.test_client_class = JSONAPIClient
    return app.test_client()
